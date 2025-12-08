"""Integration test for the high-level research workflow.

This script starts a `FinanceMcpApp` instance and runs the `ConductResearchOp`
pipeline using a Dashscope-backed search operator and a thinking tool. It is
primarily intended as an end-to-end sanity check rather than a unit test.
"""

import asyncio

from finance_mcp import FinanceMcpApp
from finance_mcp.core.agent import ConductResearchOp, ThinkToolOp
from finance_mcp.core.search import DashscopeSearchOp
from finance_mcp.core.utils import run_stream_op


async def main() -> None:
    """Run the conduct-research operation with a predefined research topic.

    The function wires up the research operator with concrete search and
    thinking implementations, then streams results to stdout for manual
    inspection.
    """

    async with FinanceMcpApp():
        # Build the research operation with explicit search and thinking ops.
        op = ConductResearchOp()
        op.ops.search_op = DashscopeSearchOp()
        op.ops.think_op = ThinkToolOp()

        research_topic = "茅台公司未来业绩"
        async for _ in run_stream_op(
            op,
            enable_print=True,
            research_topic=research_topic,
        ):
            # The streaming helper prints intermediate results; we only
            # exhaust the async generator here.
            pass


if __name__ == "__main__":
    asyncio.run(main())
