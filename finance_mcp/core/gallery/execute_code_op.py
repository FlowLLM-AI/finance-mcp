from flowllm.core.context import C
from flowllm.core.op import BaseAsyncToolOp
from flowllm.core.schema import ToolCall

from finance_mcp.core.utils.common_utils import exec_code


@C.register_op()
class ExecuteCodeOp(BaseAsyncToolOp):
    file_path = __file__

    def build_tool_call(self) -> ToolCall:
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
        self.set_output(exec_code(self.input_dict["code"]))

    async def async_default_execute(self, e: Exception = None, **kwargs):
        """Fill outputs with a default failure message when execution fails."""
        error_msg = "Failed to execute code "
        if e:
            error_msg += f": {str(e)}"
        self.set_output(error_msg)
