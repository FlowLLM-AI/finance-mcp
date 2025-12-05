async def main():
    from flowllm.app import FlowLLMApp

    async with FlowLLMApp(load_default_config=True):

        context = FlowContext(research_topic="茅台公司未来业绩", stream_queue=asyncio.Queue())
        op = ConductResearchOp() << DashscopeSearchOp() << ThinkToolOp() << ResearchCompleteOp()

        async def async_call():
            await op.async_call(context=context)
            await context.add_stream_done()

        task = asyncio.create_task(async_call())

        while True:
            stream_chunk = await context.stream_queue.get()
            if stream_chunk.done:
                print("\nend")
                await task
                break

            else:
                print(stream_chunk.chunk, end="")

        await task


if __name__ == "__main__":
    asyncio.run(main())
