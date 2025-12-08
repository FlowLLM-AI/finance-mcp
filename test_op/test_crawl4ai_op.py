"""Simple integration test for the Crawl4ai-based crawler operator.

The script runs `Crawl4aiOp` inside a `FinanceMcpApp` context and prints the
scraped output for a fixed target URL. It is mainly intended for quick manual
verification of the crawling pipeline.
"""

import asyncio

from finance_mcp import FinanceMcpApp
from finance_mcp.core.crawl import Crawl4aiOp


async def main() -> None:
    """Execute the crawl operation for a sample stock information page."""

    async with FinanceMcpApp():
        # Instantiate and run the crawling operator against a THS stock page.
        op = Crawl4aiOp()
        await op.async_call(url="https://stockpage.10jqka.com.cn/601899/")
        print(op.output)


if __name__ == "__main__":
    asyncio.run(main())
