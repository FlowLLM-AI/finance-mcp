"""Asynchronous tool operation for executing shell commands.

This module exposes :class:`ExecuteShellOp`, which allows FlowLLM agents
to run shell commands in a controlled way and capture their output,
error stream, and exit code as structured text.
"""

from flowllm.core.context import C
from flowllm.core.op import BaseAsyncToolOp
from flowllm.core.schema import ToolCall

from ..utils import run_shell_command


@C.register_op()
class ExecuteShellOp(BaseAsyncToolOp):
    """Run a shell command asynchronously and return its result.

    The operation expects a single string argument named ``command``
    and returns a human-readable multi-line summary including the
    command, stdout, stderr, and exit code.
    """

    file_path = __file__

    def build_tool_call(self) -> ToolCall:
        """Build the tool call schema for executing shell commands."""
        return ToolCall(
            **{
                "name": "ExecuteShell",
                "description": self.get_prompt("tool_description"),
                "input_schema": {
                    "command": {
                        "type": "string",
                        "description": "command to be executed",
                        "required": True,
                    },
                },
            },
        )

    async def async_execute(self):
        """Execute the shell command operation."""
        command: str = self.input_dict.get("command", "").strip()
        assert command, "The 'command' parameter cannot be empty."

        # Execute using run_shell_command from common_utils
        stdout, stderr, return_code = await run_shell_command(command)

        # Build result message
        result_parts = [
            f"Command: {command}",
            f"Output: {stdout if stdout else '(empty)'}",
            f"Error: {stderr if stderr else '(none)'}",
            f"Exit Code: {return_code if return_code is not None else '(none)'}",
        ]

        self.set_output("\n".join(result_parts))

    async def async_default_execute(self, e: Exception = None, **_kwargs):
        """Fill outputs with a default failure message when execution fails."""
        command: str = self.input_dict.get("command", "").strip()
        error_msg = f'Failed to execute shell command "{command}"'
        if e:
            error_msg += f": {str(e)}"
        self.set_output(error_msg)
