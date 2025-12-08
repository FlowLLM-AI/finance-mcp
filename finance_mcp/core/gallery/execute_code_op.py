"""Asynchronous tool operation for executing arbitrary Python code.

This operation is mainly intended for controlled environments such as
debugging, experimentation, or automation within the agent workflow.
It wraps :func:`finance_mcp.core.utils.common_utils.exec_code` and
exposes it as a FlowLLM ``ToolOp`` so that LLM agents can call it
through a structured tool interface.
"""

from flowllm.core.context import C
from flowllm.core.op import BaseAsyncToolOp
from flowllm.core.schema import ToolCall

from finance_mcp.core.utils.common_utils import exec_code


@C.register_op()
class ExecuteCodeOp(BaseAsyncToolOp):
    """Execute raw Python code and return the textual result.

    The input expects a single "code" field containing the Python
    source to run. The underlying execution helper is responsible for
    sandboxing and security controls.
    """

    file_path = __file__

    def build_tool_call(self) -> ToolCall:
        """Build the tool call schema used by FlowLLM.

        Returns:
            ToolCall: The tool call definition including description and
            input schema.
        """
        return ToolCall(
            **{
                "description": self.get_prompt("tool_description"),
                "input_schema": {
                    "code": {
                        "type": "string",
                        "description": "code to be executed",
                        "required": True,
                    },
                },
            },
        )

    async def async_execute(self):
        """Execute the provided Python code asynchronously.

        The method reads the ``code`` field from ``input_dict``,
        delegates execution to :func:`exec_code`, and stores the
        textual result in the operation output.
        """

        self.set_output(exec_code(self.input_dict["code"]))

    async def async_default_execute(self, e: Exception = None, **_kwargs):
        """Fill outputs with a default failure message when execution fails."""
        error_msg = "Failed to execute code "
        if e:
            error_msg += f": {str(e)}"
        self.set_output(error_msg)
