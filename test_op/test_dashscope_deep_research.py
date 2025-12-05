import asyncio

from finmcp import FinMcpApp
from finmcp.core.agent.dashscope_deep_research_op import DashscopeDeepResearchOp


async def main():
    async with FinMcpApp():
        query = "茅台公司未来业绩"

        op = DashscopeDeepResearchOp()
        stream_queue = asyncio.Queue()

        async def execute_task():
            await op.async_call(query=query, stream_queue=stream_queue)
            await op.context.add_stream_done()
            return

        task = asyncio.create_task(execute_task())

        while True:
            stream_chunk = await stream_queue.get()
            if stream_chunk.done:
                print("\nend")
                break

            else:
                print(stream_chunk.chunk, end="")

        await task


if __name__ == "__main__":
    asyncio.run(main())
