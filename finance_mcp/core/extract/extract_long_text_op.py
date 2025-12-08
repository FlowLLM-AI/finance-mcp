"""Ops for extracting query-relevant content from long text.

The main operator defined here takes a long text and a query, then asks
an LLM to return only the portions of the text that are relevant to the
user query. Inputs and outputs are designed to be compatible with the
FlowLLM operator framework.
"""

from flowllm.core.context import C
from flowllm.core.enumeration import Role
from flowllm.core.op import BaseAsyncToolOp
from flowllm.core.schema import ToolCall, Message

from ..utils import get_datetime


@C.register_op()
class ExtractLongTextOp(BaseAsyncToolOp):
    """Async op that extracts relevant snippets from a long text.

    The op expects a ``long_text`` field containing the full context and a
    ``query`` describing what information the user is looking for. The
    long text can be truncated with ``max_content_char_length`` to control
    token cost and latency.
    """

    file_path: str = __file__

    def __init__(self, max_content_char_length: int = 50000, **kwargs):
        """Initialize the op.

        Args:
            max_content_char_length: Maximum number of characters from
                ``long_text`` that will be sent to the LLM. Longer content
                is safely truncated from the tail.
            **kwargs: Additional keyword arguments passed to ``BaseAsyncToolOp``.
        """

        super().__init__(**kwargs)
        self.max_content_char_length = max_content_char_length

    def build_tool_call(self) -> ToolCall:
        """Describe the tool-call schema for this operator.

        Returns:
            ``ToolCall`` instance with description and input schema.
        """

        return ToolCall(
            **{
                "description": "Utilize the capabilities of LLM to parse content relevant to the query from long_text.",
                "input_schema": {
                    "long_text": {
                        "type": "string",
                        "description": "Long unstructured text that contains potential answers.",
                        "required": True,
                    },
                    "query": {
                        "type": "string",
                        "description": "User query describing what information to extract.",
                        "required": True,
                    },
                },
            },
        )

    async def async_execute(self):
        """Execute the extraction by prompting the LLM.

        The long text is truncated if it exceeds ``max_content_char_length``.
        The prompt includes the current datetime so that the LLM can reason
        about time-sensitive content when necessary.
        """

        long_text: str = self.input_dict["long_text"]
        # Avoid sending extremely long content to the LLM to save tokens.
        long_text = long_text[: self.max_content_char_length]
        query: str = self.input_dict["query"]

        extract_content_prompt = self.prompt_format(
            prompt_name="extract_content_prompt",
            long_text=long_text,
            datetime=get_datetime(),
            query=query,
        )
        assistant_message = await self.llm.achat(
            messages=[Message(role=Role.USER, content=extract_content_prompt)],
        )
        # The raw assistant content is used as the op output.
        self.set_output(assistant_message.content)
