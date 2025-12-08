from flowllm.core.context import C
from flowllm.core.op import BaseAsyncToolOp
from flowllm.core.schema import ToolCall


@C.register_op()
class ResearchCompleteOp(BaseAsyncToolOp):

    def build_tool_call(self) -> ToolCall:
        return ToolCall(
            **{
                "name": "research_complete",
                "description": "Call this tool to indicate that the research is complete.",
            },
        )

    async def async_execute(self):
        self.set_output("The research is complete.")
