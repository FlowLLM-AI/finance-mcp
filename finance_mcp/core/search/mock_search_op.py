"""Mock search operation that uses LLM to generate search results."""

import json
import random

from flowllm.core.context import C
from flowllm.core.enumeration import Role
from flowllm.core.op import BaseAsyncToolOp
from flowllm.core.schema import ToolCall, Message
from flowllm.core.utils import extract_content
from loguru import logger


@C.register_op()
class MockSearchOp(BaseAsyncToolOp):
    """Asynchronous mock search tool that generates LLM-based results."""

    file_path: str = __file__

    def build_tool_call(self) -> ToolCall:
        """Build the tool call schema describing the mock search tool.

        Returns:
            ToolCall: Definition containing description and input schema
            for the ``query`` parameter.
        """

        return ToolCall(
            **{
                "description": self.get_prompt("tool_description"),
                "input_schema": {
                    "query": {
                        "type": "string",
                        "description": "search keyword",
                        "required": True,
                    },
                },
            },
        )

    async def async_execute(self):
        """Generate mock search results using an LLM.

        The method builds a small conversation where the system message
        instructs the model to return JSON-formatted search results, and
        the user message contains the formatted query. The JSON
        structure is then extracted and pretty-printed.
        """

        query: str = self.input_dict["query"]
        if not query:
            answer = "query is empty, no results found."
            logger.warning(answer)
            self.set_output(answer)
            return

        messages = [
            Message(
                role=Role.SYSTEM,
                content="You are a helpful assistant that generates realistic search results in JSON format.",
            ),
            Message(
                role=Role.USER,
                content=self.prompt_format(
                    "mock_search_op_prompt",
                    query=query,
                    num_results=random.randint(0, 5),
                ),
            ),
        ]

        logger.info(f"messages={messages}")

        def callback_fn(message: Message):
            return extract_content(message.content, "json")

        search_results: str = await self.llm.achat(messages=messages, callback_fn=callback_fn)
        self.set_output(json.dumps(search_results, ensure_ascii=False, indent=2))
