"""Integration test for the LangChain-based deep research pipeline.

This script composes several research-related operators into a LangChain-style
workflow and runs them inside a `FinanceMcpApp` context. Output is streamed to
stdout for quick manual inspection.
"""

import asyncio

from finance_mcp import FinanceMcpApp
from finance_mcp.core.agent import (
    ConductResearchOp,
    LangchainDeepResearchOp,
    ResearchCompleteOp,
    ThinkToolOp,
)
from finance_mcp.core.search import DashscopeSearchOp
from finance_mcp.core.utils import run_stream_op


async def main() -> None:
    """Run the LangChain-style deep research flow for a sample query."""

    async with FinanceMcpApp():
        # First build the basic conduct-research op with search and thinking.
        cr_op = ConductResearchOp() << {
            "search_op": DashscopeSearchOp(),
            "think_op": ThinkToolOp(),
        }

        # Then compose a deeper research pipeline on top of the base operator.
        dr_op = LangchainDeepResearchOp() << [
            cr_op,
            ThinkToolOp(),
            ResearchCompleteOp(),
        ]

        query = "茅台公司未来业绩"
        async for _ in run_stream_op(
            dr_op,
            enable_print=True,
            query=query,
        ):
            # Streaming helper handles printing; we only exhaust the iterator.
            pass


if __name__ == "__main__":
    asyncio.run(main())
