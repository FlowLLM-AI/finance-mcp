"""Search-related tool operations.

This subpackage collects different implementations of web search tools
backed by multiple providers (Dashscope, Tavily, Google/Serper, MCP-based search,
and an LLM-powered mock search), as well as specialized search tools for
web scraping. The high-level operation classes
are exported so that they can be imported directly from
``finance_mcp.core.search``.
"""

from .dashscope_search_op import DashscopeSearchOp
from .google_search_op import GoogleSearchOp
from .mcp_search_op import TongyiMcpSearchOp, BochaMcpSearchOp
from .mock_search_op import MockSearchOp
from .tavily_search_op import TavilySearchOp
from .web_scrape_op import WebScrapeOp

__all__ = [
    "DashscopeSearchOp",
    "TavilySearchOp",
    "GoogleSearchOp",
    "TongyiMcpSearchOp",
    "BochaMcpSearchOp",
    "MockSearchOp",
    "WebScrapeOp",
]
