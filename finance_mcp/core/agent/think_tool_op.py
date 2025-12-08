"""Lightweight tool op used to elicit intermediate thinking from the LLM."""

from flowllm.core.context import C
from flowllm.core.op import BaseAsyncToolOp
from flowllm.core.schema import ToolCall


@C.register_op()
class ThinkToolOp(BaseAsyncToolOp):
    """Utility operation that prompts the model for explicit reflection text."""

    file_path = __file__

    def __init__(self, add_output_reflection: bool = False, **kwargs):
        """Create a think tool helper.

        Args:
            add_output_reflection: If ``True``, the caller-provided
                reflection text is returned as the tool output.
                Otherwise a generic reflection string from the prompt
                configuration is used.
            **kwargs: Additional keyword arguments forwarded to
                :class:`BaseAsyncToolOp`.
        """

        super().__init__(**kwargs)
        self.add_output_reflection: bool = add_output_reflection

    def build_tool_call(self) -> ToolCall:
        """Describe the think tool and its single text field input."""

        return ToolCall(
            **{
                "name": "think_tool",
                "description": self.get_prompt("tool_desc"),
                "input_schema": {
                    "reflection": {
                        "type": "string",
                        "description": self.get_prompt("reflection"),
                        "required": True,
                    },
                },
            },
        )

    async def async_execute(self):
        """Populate the output with either user or template reflection."""

        if self.add_output_reflection:
            self.set_output(self.input_dict["reflection"])
        else:
            self.set_output(self.get_prompt("reflection_output"))
