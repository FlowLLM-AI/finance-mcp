"""Search-related tool operations.

This subpackage collects different implementations of web search tools
backed by multiple providers (Dashscope, Tavily, MCP-based search, and
an LLM-powered mock search). The high-level operation classes are
exported so that they can be imported directly from
``finance_mcp.core.search``.
"""

from .dashscope_search_op import DashscopeSearchOp
from .mcp_search_op import TongyiMcpSearchOp, BochaMcpSearchOp
from .mock_search_op import MockSearchOp
from .tavily_search_op import TavilySearchOp

__all__ = [
    "DashscopeSearchOp",
    "TavilySearchOp",
    "TongyiMcpSearchOp",
    "BochaMcpSearchOp",
    "MockSearchOp",
]
