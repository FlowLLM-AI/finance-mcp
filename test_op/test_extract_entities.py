import asyncio

from finance_mcp import FinMcpApp
from finance_mcp.core.extract import ExtractEntitiesCodeOp
from finance_mcp.core.search import DashscopeSearchOp


async def main():
    async with FinMcpApp():
        query = "茅台和五粮液哪个好？现在适合买入以太坊吗？"
        # query = "中概etf？"
        op = ExtractEntitiesCodeOp() << DashscopeSearchOp()
        await op.async_call(query=query)
        print(op.output)


if __name__ == "__main__":
    asyncio.run(main())
