async def async_main():
    # op = AkshareTradeOp()
    # context = FlowContext(code="601899")
    # await op.async_call(context=context)
    # print(op.output)
    from flowllm.app import FlowLLMApp

    async with FlowLLMApp(load_default_config=True):
        op = AkshareCalculateOp()
        context = FlowContext(code="601899", query="最近五日成交量有放量吗？最近五日macd有金叉吗？")
        await op.async_call(context=context)
        print(op.output)


if __name__ == "__main__":
    asyncio.run(async_main())
