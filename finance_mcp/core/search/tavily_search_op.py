"""Tavily-based web search operation.

This module defines :class:`TavilySearchOp`, an asynchronous tool
operation that uses the Tavily API to perform web search and optional
content extraction with character-length constraints.
"""

import json
import os

from flowllm.core.context import C
from flowllm.core.op import BaseAsyncToolOp
from flowllm.core.schema import ToolCall
from loguru import logger


@C.register_op()
class TavilySearchOp(BaseAsyncToolOp):
    """Asynchronous web search operation backed by the Tavily API."""

    file_path: str = __file__

    def __init__(
        self,
        enable_extract: bool = False,
        item_max_char_count: int = 20000,
        all_max_char_count: int = 50000,
        **kwargs,
    ):
        """Create a new Tavily search operation.

        Args:
            enable_extract: Whether to call the Tavily extract endpoint
                and return page content in addition to metadata.
            item_max_char_count: Maximum characters to keep per item
                when extraction is enabled.
            all_max_char_count: Global character budget across all
                extracted items.
            **kwargs: Extra keyword arguments forwarded to
                :class:`BaseAsyncToolOp`.
        """

        super().__init__(**kwargs)
        self.enable_extract: bool = enable_extract
        self.item_max_char_count: int = item_max_char_count
        self.all_max_char_count: int = all_max_char_count

        self._client = None

    def build_tool_call(self) -> ToolCall:
        """Build the tool call schema for the Tavily web search tool."""
        return ToolCall(
            **{
                "description": "Use search keywords to retrieve relevant information from the internet.",
                "input_schema": {
                    "query": {
                        "type": "string",
                        "description": "search keyword",
                        "required": True,
                    },
                },
            },
        )

    @property
    def client(self):
        """Get or create the Tavily async client instance.

        Returns:
            AsyncTavilyClient: The Tavily async client instance.
        """
        if self._client is None:
            from tavily import AsyncTavilyClient

            self._client = AsyncTavilyClient(api_key=os.environ.get("TAVILY_API_KEY", ""))
        return self._client

    async def async_execute(self):
        """Execute the Tavily web search for the given query.

        The query is read from ``input_dict['query']`` and the result is
        either the raw Tavily search output or a post-processed mapping
        with optional extracted content, depending on ``enable_extract``.
        """

        query: str = self.input_dict["query"]
        logger.info(f"tavily.query: {query}")

        if self.enable_cache:
            cached_result = self.cache.load(query)
            if cached_result:
                self.set_output(json.dumps(cached_result, ensure_ascii=False, indent=2))
                return

        response = await self.client.search(query=query)
        logger.info(f"tavily.response: {response}")

        if not self.enable_extract:
            # 如果不需要 extract，直接返回 search 的结果
            if not response.get("results"):
                raise RuntimeError("tavily return empty result")

            final_result = {item["url"]: item for item in response["results"]}

            if self.enable_cache and final_result:
                self.cache.save(query, final_result, expire_hours=self.cache_expire_hours)

            self.set_output(json.dumps(final_result, ensure_ascii=False, indent=2))
            return

        # enable_extract=True 时的原有逻辑
        url_info_dict = {item["url"]: item for item in response["results"]}
        response_extract = await self.client.extract(urls=[item["url"] for item in response["results"]])
        logger.info(f"tavily.response_extract: {response_extract}")

        final_result = {}
        all_char_count = 0
        for item in response_extract["results"]:
            url = item["url"]
            raw_content: str = item["raw_content"]
            if len(raw_content) > self.item_max_char_count:
                raw_content = raw_content[: self.item_max_char_count]
            if all_char_count + len(raw_content) > self.all_max_char_count:
                raw_content = raw_content[: self.all_max_char_count - all_char_count]

            if raw_content:
                final_result[url] = url_info_dict[url]
                final_result[url]["raw_content"] = raw_content
                all_char_count += len(raw_content)

        if not final_result:
            raise RuntimeError("tavily return empty result")

        if self.enable_cache and final_result:
            self.cache.save(query, final_result, expire_hours=self.cache_expire_hours)

        self.set_output(json.dumps(final_result, ensure_ascii=False, indent=2))
