"""Reactive agent operator that orchestrates tool-augmented LLM reasoning."""

import datetime
import time
from typing import List, Dict

from flowllm.core.context import C, BaseContext
from flowllm.core.enumeration import Role
from flowllm.core.op import BaseAsyncToolOp
from flowllm.core.schema import Message, ToolCall
from loguru import logger


@C.register_op()
class ReactAgentOp(BaseAsyncToolOp):
    """React-style agent capable of iterative tool invocation."""

    file_path: str = __file__

    def __init__(
        self,
        max_steps: int = 50,
        tool_call_interval: float = 1.0,
        add_think_tool: bool = False,
        **kwargs,
    ):
        """Initialize the agent runtime configuration."""
        super().__init__(**kwargs)
        self.max_steps: int = max_steps
        self.tool_call_interval: float = tool_call_interval
        self.add_think_tool: bool = add_think_tool

    def build_tool_call(self) -> ToolCall:
        """Expose metadata describing how to invoke the agent."""
        return ToolCall(
            **{
                "description": "A React agent that answers user queries.",
                "input_schema": {
                    "query": {
                        "type": "string",
                        "description": "query",
                        "required": True,
                    },
                },
            },
        )

    async def build_tool_op_dict(self) -> dict:
        """Collect available tool operators from the execution context."""
        assert isinstance(self.ops, BaseContext), "self.ops must be BaseContext"
        tool_op_dict: Dict[str, BaseAsyncToolOp] = {
            op.tool_call.name: op for op in self.ops.values() if isinstance(op, BaseAsyncToolOp)
        }
        for op in tool_op_dict.values():
            op.language = self.language
        return tool_op_dict

    async def build_messages(self) -> List[Message]:
        """Build the initial message history for the LLM."""
        if "query" in self.input_dict and self.input_dict["query"]:
            query: str = self.input_dict["query"]
            now_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            messages = [
                Message(role=Role.SYSTEM, content=self.prompt_format(prompt_name="system_prompt", time=now_time)),
                Message(role=Role.USER, content=query),
            ]
            logger.info(f"round0.system={messages[0].model_dump_json()}")
            logger.info(f"round0.user={messages[1].model_dump_json()}")

        elif "messages" in self.input_dict:
            messages = self.input_dict["messages"]
            messages = [Message(**x) for x in messages]

            logger.info(f"round0.user={messages[-1].model_dump_json()}")
        else:
            raise ValueError("input_dict must contain either 'query' or 'messages'")

        return messages

    async def execute_tool(self, op: BaseAsyncToolOp, tool_call: ToolCall):
        """Execute a tool operation asynchronously using the provided tool call arguments."""
        self.submit_async_task(op.async_call, **tool_call.argument_dict)

    async def _reasoning_step(
        self,
        messages: List[Message],
        tool_op_dict: Dict[str, BaseAsyncToolOp],
        step: int,
    ) -> tuple[Message, bool]:
        """
        Perform the reasoning step: prepare messages and invoke LLM to generate response.

        This step represents the "think" phase of the ReAct loop, where the agent
        analyzes the current context and decides what actions to take.

        Args:
            messages: Current message history for the conversation.
            tool_op_dict: Dictionary mapping tool names to their operator instances.
            step: Current iteration step number (0-indexed).

        Returns:
            A tuple containing:
                - assistant_message: The LLM's response message, which may contain tool calls.
                - should_continue: Boolean indicating whether to continue the loop
                  (False if no tool calls are needed, meaning the agent has finished).
        """

        # Invoke LLM with current context and available tools
        assistant_message: Message = await self.llm.achat(
            messages=messages,
            tools=[op.tool_call for op in tool_op_dict.values()],
        )

        # Append the assistant's response to message history
        messages.append(assistant_message)
        logger.info(f"round{step + 1}.assistant={assistant_message.model_dump_json()}")

        # Check if the agent wants to use tools or has finished reasoning
        should_continue = bool(assistant_message.tool_calls)

        return assistant_message, should_continue

    async def _acting_step(
        self,
        assistant_message: Message,
        tool_op_dict: Dict[str, BaseAsyncToolOp],
        think_op: BaseAsyncToolOp,
        step: int,
    ) -> List[Message]:
        """
        Perform the acting step: execute tool calls and collect results.

        This step represents the "act" phase of the ReAct loop, where the agent
        executes the tools it decided to use in the reasoning step and incorporates
        their results back into the conversation context.

        Args:
            assistant_message: The LLM's response message containing tool calls.
            tool_op_dict: Dictionary mapping tool names to their operator instances.
            think_op: The think tool operator instance (for dynamic think tool management).
            step: Current iteration step number (0-indexed).

        Returns:
            A list of tool result messages to be appended to the conversation history.
        """
        if not assistant_message.tool_calls:
            return []

        op_list: List[BaseAsyncToolOp] = []
        has_think_tool_flag: bool = False
        tool_result_messages: List[Message] = []

        # Phase 1: Submit all tool calls for parallel execution
        for j, tool_call in enumerate(assistant_message.tool_calls):
            # Track if `think_tool` was used (for dynamic tool management)
            if tool_call.name == think_op.tool_call.name:
                has_think_tool_flag = True

            # Validate tool exists in available tools
            if tool_call.name not in tool_op_dict:
                logger.exception(f"unknown tool_call.name={tool_call.name}")
                continue

            logger.info(
                f"round{step + 1}.{j} submit tool_calls={tool_call.name} " f"argument={tool_call.argument_dict}",
            )

            # Create a copy of the tool operator for this specific invocation
            op_copy: BaseAsyncToolOp = tool_op_dict[tool_call.name].copy()
            op_copy.tool_call.id = tool_call.id
            op_list.append(op_copy)

            # Submit tool execution asynchronously
            await self.execute_tool(op_copy, tool_call)
            time.sleep(self.tool_call_interval)

        # Phase 2: Wait for all tool executions to complete
        await self.join_async_task()

        # Phase 3: Collect tool results and format as tool messages
        for j, op in enumerate(op_list):
            tool_result = str(op.output)
            tool_message = Message(
                role=Role.TOOL,
                content=tool_result,
                tool_call_id=op.tool_call.id,
            )
            tool_result_messages.append(tool_message)
            logger.info(
                f"round{step + 1}.{j} join tool_result={tool_result[:200]}...\n\n",
            )

        # Phase 4: Manage think_tool availability dynamically
        # If `think_tool` was used, remove it to prevent repeated use in next step
        # If it wasn't used, ensure it's available for the next step
        if self.add_think_tool:
            if not has_think_tool_flag:
                tool_op_dict["think_tool"] = think_op
            else:
                tool_op_dict.pop("think_tool", None)

        return tool_result_messages

    async def async_execute(self):
        """
        Main execution loop implementing the ReAct (Reasoning + Acting) pattern.

        The agent alternates between:
        1. Reasoning: Invoking the LLM to analyze the situation and decide on actions
        2. Acting: Executing the chosen tools and incorporating their results

        This loop continues until:
        - The agent decides no more tools are needed (final answer reached)
        - The maximum number of steps is reached
        """
        from .think_tool_op import ThinkToolOp

        # Initialize think tool operator if needed
        think_op = ThinkToolOp(language=self.language)

        # Build dictionary of available tool operators from context
        tool_op_dict = await self.build_tool_op_dict()

        # Optionally add think_tool to available tools
        if self.add_think_tool:
            tool_op_dict["think_tool"] = think_op

        # Initialize conversation message history
        messages = await self.build_messages()

        # Main ReAct loop: alternate between reasoning and acting
        for step in range(self.max_steps):
            # Reasoning step: LLM analyzes context and decides on actions
            assistant_message, should_continue = await self._reasoning_step(
                messages,
                tool_op_dict,
                step,
            )

            # If no tool calls, the agent has reached a final answer
            if not should_continue:
                break

            # Acting step: execute tools and collect results
            tool_result_messages = await self._acting_step(
                assistant_message,
                tool_op_dict,
                think_op,
                step,
            )

            # Append tool results to message history for next reasoning step
            messages.extend(tool_result_messages)

        # Set final output and store full conversation history in metadata
        self.set_output(messages[-1].content)
        self.context.response.metadata["messages"] = messages


@C.register_op()
class ReactSearchOp(ReactAgentOp):
    """Agent that guarantees a search tool fallback when none are configured."""

    async def build_tool_op_dict(self) -> dict:
        """Extend parent tools with a default search operator when needed."""
        tool_op_dict: Dict[str, BaseAsyncToolOp] = await super().build_tool_op_dict()
        if not tool_op_dict:
            from ..search.dashscope_search_op import DashscopeSearchOp

            search_op = DashscopeSearchOp()
            tool_op_dict[search_op.tool_call.name] = search_op

        return tool_op_dict
