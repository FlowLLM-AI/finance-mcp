import asyncio

from finance_mcp import FinanceMcpApp
from finance_mcp.core.akshare import AkshareCalculateOp


async def async_main():
    async with FinanceMcpApp():
        op = AkshareCalculateOp()
        await op.async_call(code="601899", query="最近五日成交量有放量吗？最近五日macd有金叉吗？RSI指标怎么样，有没有顶背离？")
        print(op.output)


if __name__ == "__main__":
    asyncio.run(async_main())
