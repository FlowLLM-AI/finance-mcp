"""LangChain-style multi-agent deep research operator.

The :class:`LangchainDeepResearchOp` coordinates multiple tool calls
and research workers to progressively collect findings and finally
produce a consolidated report.
"""

import json
from typing import List, Dict

from flowllm.core.context import C
from flowllm.core.enumeration import ChunkEnum, Role
from flowllm.core.op import BaseAsyncToolOp
from flowllm.core.schema import ToolCall, Message, FlowStreamChunk
from flowllm.core.utils import extract_content
from loguru import logger

from finance_mcp.core.utils import get_datetime


@C.register_op()
class LangchainDeepResearchOp(BaseAsyncToolOp):
    """Agent-style operator that runs a LangChain-like research flow.

    It first builds a concise research brief from the user's query and
    message history, then iteratively asks the LLM to orchestrate
    downstream tools such as :class:`ConductResearchOp`. The collected
    findings are later merged into a final report.
    """

    file_path: str = __file__

    def __init__(
        self,
        enable_research_brief: bool = True,
        max_concurrent_research_units: int = 3,
        max_researcher_iterations: int = 5,
        **kwargs,
    ):
        """Configure research orchestration parameters.

        Args:
            enable_research_brief: Whether to summarize user messages
                into a dedicated research brief before starting the
                multi-tool research loop.
            max_concurrent_research_units: Maximum number of parallel
                ``conduct_research`` tool calls allowed per iteration.
            max_researcher_iterations: Maximum number of orchestration
                iterations before stopping.
            **kwargs: Additional keyword arguments forwarded to
                :class:`BaseAsyncToolOp`.
        """

        super().__init__(**kwargs)
        self.enable_research_brief: bool = enable_research_brief
        self.max_concurrent_research_units: int = max_concurrent_research_units
        self.max_researcher_iterations: int = max_researcher_iterations

    def build_tool_call(self) -> ToolCall:
        """Describe how external callers should invoke this operator."""

        return ToolCall(
            **{
                "description": "Conduct in-depth research on user query",
                "input_schema": {
                    "query": {
                        "type": "string",
                        "description": "user query",
                        "required": False,
                    },
                    "messages": {
                        "type": "array",
                        "description": "messages",
                        "required": False,
                    },
                },
            },
        )

    async def async_execute(self):
        """Run the multi-iteration LangChain-style research process."""

        await self.context.add_stream_string_and_type("开始深度研究", ChunkEnum.THINK)

        # Normalize input into a list of :class:`Message` objects.
        if self.input_dict.get("query"):
            query: str = self.input_dict.get("query")
            messages: List[Message] = [Message(role=Role.USER, content=query)]
        elif self.input_dict.get("messages"):
            raw_messages = self.input_dict.get("messages")
            messages = [Message(**x) for x in raw_messages]
        else:
            raise RuntimeError("query or messages is required")

        logger.info(f"messages={messages}")
        messages_merge = "\n".join([x.string_buffer for x in messages])

        # Optionally create a structured research brief that the
        # orchestrator will use as the main input.
        if self.enable_research_brief:
            transform_research_topic_prompt = self.prompt_format(
                "transform_research_topic_prompt",
                messages=messages_merge,
                date=get_datetime(),
            )

            def parse_research_brief(message: Message):
                """Extract the ``research_brief`` field from the model output."""

                return extract_content(message.content)["research_brief"]

            research_brief = await self.llm.achat(
                messages=[Message(role=Role.USER, content=transform_research_topic_prompt)],
                callback_fn=parse_research_brief,
            )
        else:
            research_brief = "\n".join([x.string_buffer for x in messages])
        logger.info(f"research_brief={research_brief}")

        # Build a mapping from tool name to operator instance used by
        # the orchestrating LLM.
        tool_dict: Dict[str, BaseAsyncToolOp] = {}
        for _, op in self.ops.items():
            assert isinstance(op, BaseAsyncToolOp)
            assert op.tool_call.name not in tool_dict, f"Duplicate tool name={op.tool_call.name}"
            tool_dict[op.tool_call.name] = op
            logger.info(f"add tool call={op.tool_call.simple_input_dump()}")

        # Build the lead system prompt that governs the whole research
        # process and its constraints.
        lead_system_prompt = self.prompt_format(
            "lead_system_prompt",
            date=get_datetime(),
            max_researcher_iterations=self.max_researcher_iterations,
            max_concurrent_research_units=self.max_concurrent_research_units,
        )
        messages = [
            Message(role=Role.SYSTEM, content=lead_system_prompt),
            Message(role=Role.USER, content=research_brief),
        ]

        findings: List[str] = []
        for i in range(self.max_researcher_iterations):
            # Ask the LLM to decide what tools to call next.
            assistant_message = await self.llm.achat(
                messages=messages,
                tools=[x.tool_call for x in tool_dict.values()],
            )
            messages.append(assistant_message)

            assistant_content = f"[{self.name}.{i}]"
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

            # If no tools are requested, the orchestration loop stops.
            if not assistant_message.tool_calls:
                break

            # Limit how many ``conduct_research`` calls can be issued in
            # a single iteration.
            tool_calls_others = [x for x in assistant_message.tool_calls if x.name != "conduct_research"]
            tool_calls_conduct = [x for x in assistant_message.tool_calls if x.name == "conduct_research"]
            tool_calls_conduct = tool_calls_conduct[: self.max_concurrent_research_units]
            assistant_message.tool_calls = tool_calls_others + tool_calls_conduct

            ops: List[BaseAsyncToolOp] = []
            for j, tool in enumerate(assistant_message.tool_calls):
                op = tool_dict[tool.name].copy()
                op.tool_call.id = tool.id
                ops.append(op)
                logger.info(f"{self.name} submit op{j}={op.name} argument={tool.argument_dict}")
                self.submit_async_task(op.async_call, **tool.argument_dict, stream_queue=self.context.stream_queue)

            await self.join_async_task()

            done: bool = False
            for op in ops:
                messages.append(
                    Message(
                        role=Role.TOOL,
                        content=op.output,
                        tool_call_id=op.tool_call.id,
                    ),
                )
                tool_content = f"[{self.name}.{i}.{op.name}] {op.output[:200]}...\n\n"
                logger.info(tool_content)
                await self.context.add_stream_string_and_type(tool_content, ChunkEnum.TOOL)

                # Collect intermediate findings from conduct_research
                # calls so they can be summarized later.
                if op.tool_call.name == "conduct_research":
                    findings.append(op.output)

                if op.tool_call.name == "research_complete":
                    done = True

            if done:
                break

        logger.info(f"findings.size={len(findings)}")

        # Build a final report generation prompt that summarizes all
        # findings and user context into a single answer.
        final_report_generation_prompt: str = self.prompt_format(
            "final_report_generation_prompt",
            research_brief=research_brief,
            messages=messages_merge,
            date=get_datetime(),
            findings="\n\n".join(findings),
        )
        report_generation_messages = [Message(role=Role.USER, content=final_report_generation_prompt)]

        async for stream_chunk in self.llm.astream_chat(report_generation_messages):  # noqa
            assert isinstance(stream_chunk, FlowStreamChunk)
            if stream_chunk.chunk_type in [ChunkEnum.ANSWER, ChunkEnum.THINK, ChunkEnum.ERROR, ChunkEnum.TOOL]:
                await self.context.add_stream_chunk(stream_chunk)
