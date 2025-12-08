"""Demo script for testing FastMCP stdio-style tool invocation.

This module defines a minimal `FastMCP` instance with a single `add` tool,
then uses a `Client` to call that tool asynchronously. It is intended for
manual debugging of tool registration, execution, and streaming behavior.
"""

import asyncio
import contextlib
from io import StringIO

from fastmcp import Client
from fastmcp import FastMCP
from loguru import logger

mcp = FastMCP("Demo 🚀")


@mcp.tool
def add(a: int, b: int) -> str:
    """Add two numbers.

    The function demonstrates how a MCP tool can execute arbitrary Python
    code and capture its stdout. The `a` and `b` arguments are currently not
    used inside the dynamic code snippet; they are kept to illustrate typed
    tool parameters.
    """

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

    except Exception as e:  # pragma: no cover - defensive logging path
        logger.exception(e)
        result = "error"

    return result + str(a) + str(b)


async def main() -> None:
    """Invoke the `add` MCP tool and print its captured output."""

    async with Client(mcp) as client:
        result = await client.call_tool(
            name="add",
            arguments={"a": 1, "b": 2},
        )
    print(result)


asyncio.run(main())
