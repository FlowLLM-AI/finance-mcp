import asyncio

from finance_mcp import FinanceMcpApp
from finance_mcp.core.agent import LangchainDeepResearchOp, ConductResearchOp, ThinkToolOp, ResearchCompleteOp
from finance_mcp.core.search import DashscopeSearchOp
from finance_mcp.core.utils import run_stream_op


async def main():
    async with FinanceMcpApp():
        cr_op = ConductResearchOp() << {"search_op": DashscopeSearchOp(), "think_op": ThinkToolOp()}
        dr_op = LangchainDeepResearchOp() << [cr_op, ThinkToolOp(), ResearchCompleteOp()]
        query = "茅台公司未来业绩"
        async for _ in run_stream_op(dr_op, enable_print=True, query=query):
            pass


if __name__ == "__main__":
    asyncio.run(main())
