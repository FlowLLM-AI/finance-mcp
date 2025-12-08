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
    file_path: str = __file__

    def build_tool_call(self) -> ToolCall:
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
