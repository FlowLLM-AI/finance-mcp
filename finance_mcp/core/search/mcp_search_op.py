"""MCP-based web search operations.

This module provides thin wrappers around generic :class:`BaseMcpOp`
operations to expose concrete MCP tools (e.g. Tongyi, Bocha) as
FlowLLM search operations.
"""

from flowllm.core.context import C
from flowllm.core.op import BaseMcpOp


@C.register_op()
class TongyiMcpSearchOp(BaseMcpOp):
    """Search operation that calls the Tongyi MCP web search tool."""

    def __init__(self, **kwargs):
        """Initialize the Tongyi MCP search operation.

        Args:
            **kwargs: Extra keyword arguments forwarded to ``BaseMcpOp``.
        """
        kwargs.update(
            {
                "mcp_name": "tongyi_search",
                "tool_name": "bailian_web_search",
                "save_answer": True,
                "input_schema_optional": ["count"],
                "input_schema_deleted": ["ctx"],
            },
        )
        super().__init__(**kwargs)


@C.register_op()
class BochaMcpSearchOp(BaseMcpOp):
    """Search operation that calls the Bocha MCP web search tool."""

    def __init__(self, **kwargs):
        """Initialize the Bocha MCP search operation.

        Args:
            **kwargs: Extra keyword arguments forwarded to ``BaseMcpOp``.
        """
        kwargs.update(
            {
                "mcp_name": "bochaai_search",
                "tool_name": "bocha_web_search",
                "save_answer": True,
                "input_schema_optional": ["freshness", "count"],
                "input_schema_deleted": ["ctx"],
            },
        )
        super().__init__(**kwargs)
