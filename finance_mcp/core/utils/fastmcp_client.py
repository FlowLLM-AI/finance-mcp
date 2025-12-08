import asyncio
import os
import shutil
from typing import List, Optional, Union

import mcp.types
from fastmcp import Client
from fastmcp.client.client import CallToolResult
from fastmcp.client.transports import StdioTransport, SSETransport, StreamableHttpTransport
from flowllm.core.schema.tool_call import ToolCall
from loguru import logger


class FastMcpClient:
    def __init__(
            self,
            name: str,
            config: dict,
            append_env: bool = False,
            max_retries: int = 3,
            timeout: Optional[float] = None,
    ):
        self.name: str = name
        self.config: dict = config
        self.append_env: bool = append_env
        self.max_retries: int = max_retries
        self.timeout: Optional[float] = timeout

        self.client: Optional[Client] = None
        self._transport = self._create_transport()

    def _create_transport(self):
        """Create the appropriate transport based on config."""
        command = self.config.get("command")

        if command:
            # Stdio transport
            if command == "npx":
                command = shutil.which("npx") or command

            env_params: dict = {}
            if self.append_env:
                env_params.update(os.environ)
            if self.config.get("env"):
                env_params.update(self.config["env"])

            return StdioTransport(
                command=command,
                args=self.config.get("args", []),
                env=env_params if env_params else None,
                cwd=self.config.get("cwd"),
            )
        else:
            # HTTP transport (SSE or Streamable HTTP)
            url = self.config["url"]
            transport_type = self.config.get("type", "").lower()
            kwargs: dict = {"url": url}

            # Handle headers with environment variable substitution
            if self.config.get("headers"):
                headers = self.config.get("headers").copy()
                if headers.get("Authorization"):
                    assert isinstance(headers["Authorization"], str)
                    headers["Authorization"] = headers["Authorization"].format(**os.environ)
                kwargs["headers"] = headers

            # Handle timeout
            if "timeout" in self.config:
                kwargs["sse_read_timeout"] = self.config["timeout"]

            # Default to SSE for /sse endpoints, otherwise StreamableHttp
            if url.endswith("/sse"):
                return SSETransport(**kwargs)
            else:
                # For URLs without /sse, use StreamableHttpTransport
                return StreamableHttpTransport(**kwargs)

    async def __aenter__(self) -> "FastMcpClient":
        """Async context manager entry."""
        for i in range(self.max_retries):
            try:
                self.client = Client(
                    transport=self._transport,
                    name=self.name,
                    timeout=self.timeout,
                )

                # Use FastMCP Client as async context manager
                if self.timeout is not None:
                    await asyncio.wait_for(
                        self.client.__aenter__(),
                        timeout=self.timeout,
                    )
                else:
                    await self.client.__aenter__()

                break

            except asyncio.TimeoutError as exc:
                logger.exception(f"{self.name} start timeout after {self.timeout}s")

                # Clean up before retrying
                await self._cleanup_client()

                if i == self.max_retries - 1:
                    raise TimeoutError(f"{self.name} start timeout after {self.timeout}s") from exc

                await asyncio.sleep(1 + i)

            except Exception as e:
                logger.exception(
                    f"{self.name} start failed with {e}. " f"Retry {i + 1}/{self.max_retries} in {1 + i}s...",
                )

                # Clean up before retrying
                await self._cleanup_client()

                await asyncio.sleep(1 + i)

                if i == self.max_retries - 1:
                    raise e

        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        for i in range(self.max_retries):
            try:
                await self._cleanup_client()
                break

            except Exception as e:
                logger.exception(
                    f"{self.name} close failed with {e}. " f"Retry {i + 1}/{self.max_retries} in {1 + i}s...",
                )
                await asyncio.sleep(1 + i)

                if i == self.max_retries - 1:
                    break

        self.client = None

    async def _cleanup_client(self):
        """Clean up the client connection."""
        if self.client:
            try:
                await self.client.__aexit__(None, None, None)
            except Exception:
                pass
            try:
                await self.client.close()
            except Exception:
                pass
            self.client = None

    async def list_tools(self) -> List[mcp.types.Tool]:
        if not self.client:
            raise RuntimeError(f"Server {self.name} not initialized")

        tools = []
        for i in range(self.max_retries):
            try:
                if self.timeout is not None:
                    tools = await asyncio.wait_for(
                        self.client.list_tools(),
                        timeout=self.timeout,
                    )
                else:
                    tools = await self.client.list_tools()
                break

            except asyncio.TimeoutError as exc:
                logger.exception(f"{self.name} list tools timeout after {self.timeout}s")

                if i == self.max_retries - 1:
                    raise TimeoutError(f"{self.name} list tools timeout after {self.timeout}s") from exc

                await asyncio.sleep(1 + i)

            except Exception as e:
                logger.exception(
                    f"{self.name} list tools failed with {e}. " f"Retry {i + 1}/{self.max_retries} in {1 + i}s...",
                )
                await asyncio.sleep(1 + i)

                if i == self.max_retries - 1:
                    raise e

        return tools

    async def list_tool_calls(self) -> List[ToolCall]:
        if not self.client:
            raise RuntimeError(f"Server {self.name} not initialized")

        tools = await self.list_tools()
        return [ToolCall.from_mcp_tool(t) for t in tools]

    async def call_tool(
            self,
            tool_name: str,
            arguments: dict,
            parse_result: bool = False,
    ) -> Union[str, CallToolResult]:
        if not self.client:
            raise RuntimeError(f"Server {self.name} not initialized")

        result = None
        for i in range(self.max_retries):
            try:
                if self.timeout is not None:
                    result = await asyncio.wait_for(
                        self.client.call_tool(tool_name, arguments),
                        timeout=self.timeout,
                    )
                else:
                    result = await self.client.call_tool(tool_name, arguments)

                if parse_result:
                    if len(result.content) == 1:
                        return result.content[0].text

                    else:
                        text_content = []
                        for block in result.content:
                            if hasattr(block, "text"):
                                text_content.append(block.text)
                        return "\n".join(text_content) if text_content else result
                else:
                    return result

            except asyncio.TimeoutError as exc:
                logger.exception(f"{self.name}.{tool_name} call_tool timeout after {self.timeout}s")

                if i == self.max_retries - 1:
                    raise TimeoutError(f"{self.name}.{tool_name} call_tool timeout after {self.timeout}s") from exc

                await asyncio.sleep(1 + i)

            except Exception as e:
                logger.exception(
                    f"{self.name}.{tool_name} call_tool failed with {e}. "
                    f"Retry {i + 1}/{self.max_retries} in {1 + i}s...",
                )
                await asyncio.sleep(1 + i)

                if i == self.max_retries - 1:
                    raise e

        return result
