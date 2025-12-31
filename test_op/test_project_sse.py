"""Test module for the finance-mcp MCP service over HTTP.

This module exercises the finance-mcp MCP service by:

1. Starting the service with the given configuration using
   :class:`FinanceMcpServiceRunner`.
2. Connecting to the service via :class:`FastMcpClient`.
3. Listing available tools exposed by the MCP server.
4. Invoking a selection of tools and asserting that each call succeeds.

It is intended as an integration/diagnostic script rather than a unit test.
"""

import asyncio
import json
import time

from fastmcp.client.client import CallToolResult
from loguru import logger

from finance_mcp.core.utils.fastmcp_client import FastMcpClient
from finance_mcp.core.utils.service_runner import FinanceMcpServiceRunner

# Service configuration
service_args = [
    "finance-mcp",
    "config=default,ths_local",
    "mcp.transport=sse",
    "llm.default.model_name=qwen3-30b-a3b-thinking-2507",
]

# MCP client configuration
host = "0.0.0.0"
port = 8150
mcp_config = {
    "type": "sse",
    "url": f"http://{host}:{port}/sse",
}


async def test_mcp_service() -> None:
    """Connect to the MCP service, list tools, and run sample tool calls."""

    # Connect to the MCP service using FastMcpClient
    async with FastMcpClient(
        name="finance-mcp-test",
        config=mcp_config,
        max_retries=1,
    ) as client:
        # List available tools
        print("=" * 50)
        print("Getting available MCP tools...")
        tool_calls = await client.list_tool_calls()
        print(f"Found {len(tool_calls)} tools:")
        for tool_call in tool_calls:
            tool_info = tool_call.simple_input_dump()
            print(json.dumps(tool_info, ensure_ascii=False))

        for tool_name, test_arguments in [
            # ("history_calculate", {"code": "000001", "query": "最近5个、10个交易日的涨幅是多少？"}),
            # ("crawl_url", {"url": "https://stockpage.10jqka.com.cn/601899/", "query": "紫金矿业信息"}),
            # ("extract_entities_code", {"query": "查询紫金矿业和贵州茅台的股票代码"}),
            # ("execute_code", {"code": "print('Hello World')\nresult = 1 + 1\nprint(f'1 + 1 = {result}')"}),
            # ("execute_shell", {"command": "echo 'Hello from shell' && date"}),
            ("dashscope_search", {"query": "什么是人工智能？"}),
            # ("tavily_search", {"query": "Python programming best practices"}),
            # ("mock_search", {"query": "最新的AI技术发展"}),
            # ("react_agent", {"query": "分析一下宁德时代"}),
            # ("crawl_ths_company", {"code": "300750"}),
            # ("crawl_ths_holder", {"code": "300750"}),
            # ("crawl_ths_operate", {"code": "300750"}),
            # ("crawl_ths_equity", {"code": "300750"}),
            # ("crawl_ths_capital", {"code": "300750"}),
            # ("crawl_ths_worth", {"code": "300750"}),
            # ("crawl_ths_news", {"code": "300750"}),
            # ("crawl_ths_concept", {"code": "300750"}),
            # ("crawl_ths_position", {"code": "300750"}),
            # ("crawl_ths_finance", {"code": "300750"}),
            # ("crawl_ths_bonus", {"code": "300750"}),
            # ("crawl_ths_event", {"code": "300750"}),
            # ("crawl_ths_field", {"code": "300750"}),
        ]:
            result: CallToolResult = await client.call_tool(tool_name, test_arguments)
            result_content = result.content[0].text if result.content else "(empty)"
            success = not result.is_error
            print(f"Tool call result: {tool_name}, success: {success}, content: {result_content}")
            assert success


def main() -> None:
    """Run the MCP service in-process and execute the async test routine."""

    with FinanceMcpServiceRunner(
        service_args,
        host=host,
        port=port,
    ) as service:
        logger.info(f"Service is running on port {service.port}")
        logger.info("Waiting a moment for service to fully initialize...")
        time.sleep(2)  # Give service a moment to fully initialize

        asyncio.run(test_mcp_service())


if __name__ == "__main__":
    main()
