"""Generic helper utilities used across finance-mcp.

This module currently provides:

* ``run_shell_command``: small wrapper around ``asyncio.create_subprocess_shell``
  that returns decoded stdout/stderr.
* ``run_stream_op``: helper to execute a ``BaseAsyncToolOp`` and yield streaming
  chunks while printing them to stdout.
* ``exec_code``: very small sandbox that executes arbitrary Python code and
  captures printed output for debugging or experimentation.
"""

import asyncio
import contextlib
from io import StringIO
from typing import Optional, Tuple

from flowllm.core.op import BaseAsyncToolOp


async def run_shell_command(cmd: str, timeout: Optional[float] = 30) -> Tuple[str, str, int]:
    """Run a shell command asynchronously and return its output.

    Args:
        cmd: Full command string to execute in a system shell.
        timeout: Maximum time in seconds to wait for completion. ``None``
            disables the timeout and waits indefinitely.

    Returns:
        A tuple ``(stdout, stderr, return_code)`` where both streams are
        UTF-8 decoded strings.

    Raises:
        asyncio.TimeoutError: If command execution exceeds ``timeout``.
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
    """Execute an async tool op and stream its output.

    The operation is executed inside a ``FinanceMcpApp`` context so that all
    required configuration and resources are available. Streaming chunks are
    read from an internal queue and optionally printed to stdout.

    Args:
        op: The asynchronous tool operation instance to execute.
        enable_print: If ``True``, print streamed chunks to the console while
            yielding them to the caller.
        **kwargs: Additional keyword arguments forwarded to ``op.async_call``.

    Yields:
        Stream chunk objects produced by ``op.async_call`` until a terminal
        ``done`` chunk is received.
    """

    from finance_mcp import FinanceMcpApp

    async with FinanceMcpApp():
        # Shared queue used by the op to push streaming chunks.
        stream_queue = asyncio.Queue()

        async def execute_task():
            await op.async_call(stream_queue=stream_queue, **kwargs)
            # Explicitly signal that no more chunks will be produced.
            await op.context.add_stream_done()
            return

        # Run the tool op in the background while we consume the queue.
        task = asyncio.create_task(execute_task())

        while True:
            stream_chunk = await stream_queue.get()
            if stream_chunk.done:
                if enable_print:
                    print("\nend")
                break

            if enable_print:
                print(stream_chunk.chunk, end="")
            yield stream_chunk

        # Ensure the worker task has finished before leaving the context.
        await task


import multiprocessing
def _exec_code_in_process(queue: multiprocessing.Queue, code: str) -> None:
    """Helper function to execute code in a subprocess.

    This function runs in a separate process and communicates results
    back via a multiprocessing Queue.

    Args:
        queue: Queue to put the execution result into.
        code: Python source code to execute.
    """
    try:
        redirected_output = StringIO()
        with contextlib.redirect_stdout(redirected_output):
            exec(code)  # noqa: S102
        queue.put(("success", redirected_output.getvalue()))
    except BaseException as e:  # noqa: BLE001
        queue.put(("error", str(e)))


async def exec_code(code: str, timeout: Optional[float] = 30) -> str:
    """Execute arbitrary Python code and capture its printed output.

    The code is executed in a separate process and any text written to
    ``stdout`` is captured and returned as a string. If an exception occurs,
    its string representation is returned instead. If execution exceeds the
    timeout, the process is terminated and an error message is returned.

    Args:
        code: Python source code to execute.
        timeout: Maximum time in seconds to wait for code execution. ``None``
            disables the timeout and waits indefinitely. Defaults to 30 seconds.

    Returns:
        Captured ``stdout`` output, the exception message if execution fails,
        or a timeout error message if execution exceeds the timeout.
    """

    def _run_in_process() -> str:
        """Run code execution in a subprocess with timeout handling."""
        queue: multiprocessing.Queue = multiprocessing.Queue()
        process = multiprocessing.Process(
            target=_exec_code_in_process,
            args=(queue, code),
        )
        process.start()
        process.join(timeout=timeout)

        if process.is_alive():
            # Process is still running, terminate it
            process.terminate()
            process.join(timeout=1)
            if process.is_alive():
                # Force kill if terminate didn't work
                process.kill()
                process.join(timeout=1)
            return f"Code execution timed out after {timeout} seconds"

        # Process finished, get the result
        if not queue.empty():
            status, result = queue.get_nowait()
            return result

        return "No output"

    # Run the blocking process operation in a thread to avoid blocking the event loop
    return await asyncio.to_thread(_run_in_process)