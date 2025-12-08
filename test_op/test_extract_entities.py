"""End-to-end test for entity extraction based on search results.

The script wires `ExtractEntitiesCodeOp` with `DashscopeSearchOp` and runs the
pipeline on a multi-question natural-language query. The resulting structured
entities are printed for manual review.
"""

import asyncio

from finance_mcp import FinanceMcpApp
from finance_mcp.core.extract import ExtractEntitiesCodeOp
from finance_mcp.core.search import DashscopeSearchOp


async def main() -> None:
    """Run the entity-extraction pipeline for a sample user query."""

    async with FinanceMcpApp():
        # The query mixes stock and crypto questions to test extraction quality.
        query = "茅台和五粮液哪个好？现在适合买入以太坊吗？"
        # query = "中概etf？"

        op = ExtractEntitiesCodeOp() << DashscopeSearchOp()
        await op.async_call(query=query)
        print(op.output)


if __name__ == "__main__":
    asyncio.run(main())
