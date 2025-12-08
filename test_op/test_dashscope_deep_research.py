"""Integration test for the Dashscope-powered deep research operator.

This script runs `DashscopeDeepResearchOp` with a fixed query and streams the
intermediate research output to stdout, allowing manual inspection of the
end-to-end research flow.
"""

import asyncio

from finance_mcp.core.agent import DashscopeDeepResearchOp
from finance_mcp.core.utils import run_stream_op


async def main() -> None:
    """Execute the deep-research pipeline for a single example query."""

    query = "茅台公司未来业绩"
    op = DashscopeDeepResearchOp()

    async for _ in run_stream_op(
        op,
        enable_print=True,
        query=query,
    ):
        # The helper prints streaming content; we just consume the iterator.
        pass


if __name__ == "__main__":
    asyncio.run(main())
