async def main():
    from flowllm.app import FlowLLMApp

    async with FlowLLMApp(load_default_config=True):
        # query = "茅台和五粮液哪个好？现在适合买入以太坊吗？"
        query = "中概etf？"
        context = FlowContext(query=query)
        op = ExtractEntitiesCodeOp() << DashscopeSearchOp()
        await op.async_call(context=context)
        logger.info(op.output)


if __name__ == "__main__":
    asyncio.run(main())
