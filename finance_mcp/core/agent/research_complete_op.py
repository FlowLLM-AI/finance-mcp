"""Sentinel operator used to mark the end of a research workflow."""

from flowllm.core.context import C
from flowllm.core.op import BaseAsyncToolOp
from flowllm.core.schema import ToolCall


@C.register_op()
class ResearchCompleteOp(BaseAsyncToolOp):
    """Tool op that signals the completion of a research process.

    This operator does not perform any heavy computation. It is used by
    higher-level agents (for example :class:`ConductResearchOp` and
    :class:`LangchainDeepResearchOp`) as a terminal tool call that
    indicates the research loop can stop.
    """

    def build_tool_call(self) -> ToolCall:
        """Return the minimal tool metadata for this sentinel op."""

        return ToolCall(
            **{
                "name": "research_complete",
                "description": "Call this tool to indicate that the research is complete.",
            },
        )

    async def async_execute(self):
        """Set a human-readable completion message as the tool output."""

        self.set_output("The research is complete.")
