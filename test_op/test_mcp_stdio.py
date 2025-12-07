import asyncio
import contextlib
from io import StringIO

from fastmcp import Client
from fastmcp import FastMCP
from loguru import logger

mcp = FastMCP("Demo 🚀")


@mcp.tool
def add(a: int, b: int):
    """Add two numbers"""
    code = """
import numpy as np

def power_int(a: int, b: int) -> int:
    return int(np.power(a, b))

print(power_int(10, 2))
    """.strip()

    print(code)

    try:
        redirected_output = StringIO()
        with contextlib.redirect_stdout(redirected_output):
            exec(code, globals())
        result = redirected_output.getvalue().strip()

    except Exception as e:
        logger.exception(e)
        result = "error"

    return result


async def main():
    async with Client(mcp) as client:
        result = await client.call_tool(
            name="add",
            arguments={"a": 1, "b": 2}
        )
    print(result)


asyncio.run(main())
