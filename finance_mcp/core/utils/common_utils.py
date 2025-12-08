import asyncio
import contextlib
from io import StringIO
from typing import Optional, Tuple

from flowllm.core.op import BaseAsyncToolOp


async def run_shell_command(cmd: str, timeout: Optional[float] = 30) -> Tuple[str, str, int]:
    """Run a shell command asynchronously.

    Args:
        cmd: Command string to execute.
        timeout: Timeout in seconds. None for no timeout.

    Returns:
        Tuple of (stdout, stderr, return_code).

    Raises:
        asyncio.TimeoutError: If command execution exceeds timeout.
    """
    process = await asyncio.create_subprocess_shell(
        cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )

    if timeout:
        stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=timeout)
    else:
        stdout, stderr = await process.communicate()

    return (
        stdout.decode("utf-8", errors="ignore"),
        stderr.decode("utf-8", errors="ignore"),
        process.returncode,
    )

async def run_stream_op(op: BaseAsyncToolOp, enable_print: bool = True, **kwargs):
    from finance_mcp import FinanceMcpApp

    async with FinanceMcpApp():
        stream_queue = asyncio.Queue()

        async def execute_task():
            await op.async_call(stream_queue=stream_queue, **kwargs)
            await op.context.add_stream_done()
            return

        task = asyncio.create_task(execute_task())

        while True:
            stream_chunk = await stream_queue.get()
            if stream_chunk.done:
                if enable_print:
                    print("\nend")
                break

            else:
                if enable_print:
                    print(stream_chunk.chunk, end="")
                    yield stream_chunk

        await task


def exec_code(code: str) -> str:
    try:
        redirected_output = StringIO()
        with contextlib.redirect_stdout(redirected_output):
            exec(code)

        return redirected_output.getvalue()

    except Exception as e:
        return str(e)