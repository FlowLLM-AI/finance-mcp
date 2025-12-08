import asyncio

from finance_mcp import FinanceMcpApp
from finance_mcp.core.agent import ConductResearchOp, ThinkToolOp
from finance_mcp.core.search import DashscopeSearchOp
from finance_mcp.core.utils import run_stream_op


async def main():
    async with FinanceMcpApp():
        op = ConductResearchOp()
        op.ops.search_op = DashscopeSearchOp()
        op.ops.think_op = ThinkToolOp()
        research_topic = "茅台公司未来业绩"
        async for _ in run_stream_op(op, enable_print=True, research_topic=research_topic):
            pass


if __name__ == "__main__":
    asyncio.run(main())
