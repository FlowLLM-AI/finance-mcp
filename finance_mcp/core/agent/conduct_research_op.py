"""Research operator that orchestrates a ReAct-like research loop.

The :class:`ConductResearchOp` tool coordinates multiple tool calls to
progressively gather evidence for a single research topic, logs the
intermediate reasoning process, and finally compresses the conversation
into a concise answer.
"""

import json
from typing import Dict, List

from flowllm.core.context import C
from flowllm.core.enumeration import Role, ChunkEnum
from flowllm.core.op import BaseAsyncToolOp
from flowllm.core.schema import ToolCall, Message
from loguru import logger

from ..utils import get_datetime


@C.register_op()
class ConductResearchOp(BaseAsyncToolOp):
    """Tool op that conducts in-depth research on a single topic.

    The operator drives a ReAct-style loop: the LLM repeatedly reasons
    about the current context, invokes tools provided in ``self.ops``,
    and integrates their outputs until a terminating condition is met.
    """

    file_path: str = __file__

    def __init__(
        self,
        max_react_tool_calls: int = 20,
        max_content_len: int = 20000,
        language: str = "zh",
        **kwargs,
    ):
        """Configure research loop limits and language.

        Args:
            max_react_tool_calls: Maximum number of ReAct iterations
                (LLM tool-using turns) before the loop is forcibly
                terminated.
            max_content_len: Hard limit on the length of tool and
                answer content that is streamed back and stored.
            language: Output language passed to the base operator.
            **kwargs: Additional keyword arguments forwarded to
                :class:`BaseAsyncToolOp`.
        """

        super().__init__(language=language, **kwargs)
        self.max_react_tool_calls: int = max_react_tool_calls
        self.max_content_len: int = max_content_len

    def build_tool_call(self) -> ToolCall:
        """Describe how external callers should invoke this tool.

        Returns a :class:`ToolCall` instance describing the high-level
        purpose of the operation and the expected input schema.
        """

        return ToolCall(
            **{
                "description": "Conduct in-depth research on a single topic.",
                "input_schema": {
                    "research_topic": {
                        "type": "string",
                        "description": "The topic to research",
                        "required": True,
                    },
                },
            },
        )

    async def async_execute(self):
        """Run the multi-step research loop and produce a final answer.

        The method performs the following high-level steps:

        1. Build a system prompt that configures the research behavior.
        2. Normalize inputs into a ``messages`` history.
        3. Repeatedly call the LLM with available tools and log its
           reasoning and tool calls.
        4. Execute requested tools asynchronously and feed their
           outputs back as TOOL messages.
        5. Once the loop ends, compress the conversation into a
           summarized answer.
        """

        # Discover the search operation from the context; it is used
        # inside the research prompt as the default search tool.
        search_op = self.ops.search_op
        assert isinstance(search_op, BaseAsyncToolOp)
        research_system_prompt = self.prompt_format(
            prompt_name="research_system_prompt",
            date=get_datetime(),
            mcp_prompt="",
            search_tool=search_op.tool_call.name,
        )

        # Normalize input into a message list: either a plain
        # ``research_topic`` string or a pre-built message history.
        if self.input_dict.get("research_topic"):
            messages: List[Message] = [Message(role=Role.USER, content=self.input_dict.get("research_topic"))]
        elif self.input_dict.get("messages"):
            messages = [Message(**x) for x in self.input_dict.get("messages")]
        else:
            raise RuntimeError("research_topic or messages is required")

        logger.info(f"messages={messages}")

        # Prepend a system message that instructs the LLM how to
        # conduct the research process.
        messages = [Message(role=Role.SYSTEM, content=research_system_prompt)] + messages

        # Build a mapping from tool name to operator instance so the
        # LLM can address tools by name in its tool calls.
        tool_dict: Dict[str, BaseAsyncToolOp] = {}
        for _, op in self.ops.items():
            assert isinstance(op, BaseAsyncToolOp)
            tool_dict[op.tool_call.name] = op

        # Main ReAct-style loop: alternate between LLM reasoning and
        # invoking tools requested by the LLM.
        for i in range(self.max_react_tool_calls):
            assistant_message = await self.llm.achat(
                messages=messages,
                tools=[x.tool_call for x in tool_dict.values()],
            )
            messages.append(assistant_message)

            # Log reasoning, content and tool calls for observability
            # and stream them as THINK chunks.
            assistant_content = f"[{self.name}.{self.tool_index}.{i}]"
            if assistant_message.content:
                assistant_content += f" content={assistant_message.content}"
            if assistant_message.reasoning_content:
                assistant_content += f" reasoning={assistant_message.reasoning_content}"
            if assistant_message.tool_calls:
                tool_call_str = " | ".join(
                    [json.dumps(t.simple_output_dump(), ensure_ascii=False) for t in assistant_message.tool_calls],
                )
                assistant_content += f" tool_calls={tool_call_str}"
            assistant_content += "\n\n"
            logger.info(assistant_content)
            await self.context.add_stream_string_and_type(assistant_content, ChunkEnum.THINK)

            # If the model does not request any tools, we consider the
            # reasoning process finished.
            if not assistant_message.tool_calls:
                break

            # Execute all requested tools in parallel and collect their
            # outputs.
            ops: List[BaseAsyncToolOp] = []
            for tool in assistant_message.tool_calls:
                op = tool_dict[tool.name].copy()
                op.tool_call.id = tool.id
                ops.append(op)
                self.submit_async_task(op.async_call, **tool.argument_dict)

            await self.join_async_task()

            # Feed each tool output back into the conversation as a
            # TOOL message and stream a truncated preview.
            done: bool = False
            for op in ops:
                messages.append(
                    Message(
                        role=Role.TOOL,
                        content=op.output[: self.max_content_len],
                        tool_call_id=op.tool_call.id,
                    ),
                )
                tool_content = f"[{self.name}.{self.tool_index}.{i}.{op.name}] {op.output[:200]}...\n\n"
                logger.info(tool_content)
                await self.context.add_stream_string_and_type(tool_content, ChunkEnum.TOOL)
                if op.tool_call.name == "research_complete":
                    done = True

            if done:
                break

        # Drop system messages before running the final compression to
        # keep the user-visible transcript focused.
        messages = [x for x in messages if x.role != Role.SYSTEM]

        # Compress the full conversation into a concise report.
        compress_system_prompt: str = self.prompt_format("compress_system_prompt", date=get_datetime())
        merge_messages = [
            Message(role=Role.SYSTEM, content=compress_system_prompt),
            *messages,
            Message(role=Role.USER, content=self.get_prompt("compress_user_prompt")),
        ]

        logger.info(f"merge_messages={merge_messages}")
        assistant_message = await self.llm.achat(messages=merge_messages)
        assistant_message.content = assistant_message.content[: self.max_content_len]
        chunk_type: ChunkEnum = ChunkEnum.ANSWER if self.save_answer else ChunkEnum.THINK
        await self.context.add_stream_string_and_type(assistant_message.content, chunk_type)
        self.set_output(assistant_message.content)
