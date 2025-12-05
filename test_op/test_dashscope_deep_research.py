import asyncio

from finmcp.core.agent.dashscope_deep_research_op import DashscopeDeepResearchOp
from finmcp.core.utils.common_utils import run_stream_op


async def main():
    query = "茅台公司未来业绩"
    op = DashscopeDeepResearchOp()
    async for _ in run_stream_op(op, enable_print=True, query=query):
        pass



if __name__ == "__main__":
    asyncio.run(main())
