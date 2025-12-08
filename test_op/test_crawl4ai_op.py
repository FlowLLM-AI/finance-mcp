import asyncio

from finance_mcp import FinanceMcpApp
from finance_mcp.core.crawl import Crawl4aiOp


async def main():
    async with FinanceMcpApp():
        op = Crawl4aiOp()
        await op.async_call(url="https://stockpage.10jqka.com.cn/601899/")
        print(op.output)


if __name__ == "__main__":
    asyncio.run(main())
