"""Async operator for LLM-driven historical data calculations.

The operator defined in this module works together with Tushare to
generate Python analysis code via an LLM and then execute that code on
historical market data.
"""

import os

from flowllm.core.context import C
from flowllm.core.enumeration import Role
from flowllm.core.op import BaseAsyncToolOp
from flowllm.core.schema import ToolCall, Message
from flowllm.core.utils import extract_content
from loguru import logger

from ..utils import get_datetime
from ..utils.common_utils import exec_code


@C.register_op()
class HistoryCalculateOp(BaseAsyncToolOp):
    """Async op that lets an LLM write code for historical stock analysis.

    The op takes a stock code and a natural language question, then
    delegates to the LLM to produce executable Python code that fetches
    and analyses historical data obtained from Tushare.
    """

    file_path = __file__

    def build_tool_call(self) -> ToolCall:
        """Describe the tool-call interface for this operator.

        Returns:
            ``ToolCall`` instance specifying required inputs and metadata.
        """

        return ToolCall(
            **{
                "description": self.get_prompt("tool_description"),
                "input_schema": {
                    "code": {
                        "type": "string",
                        "description": "A-share stock code (e.g. '600000' or '000001').",
                        "required": True,
                    },
                    "query": {
                        "type": "string",
                        "description": "User question about the stock's historical performance.",
                        "required": True,
                    },
                },
            },
        )

    async def async_execute(self):
        """Generate and execute analysis code for the given stock code.

        The method normalizes the stock code to the Tushare format, calls
        the LLM to generate Python analysis code, and finally executes that
        code using ``exec_code``.
        """

        code: str = self.input_dict["code"]
        # Normalize plain numeric codes into exchange-qualified codes.
        # Examples: '00'/'30' → 'SZ', '60'/'68' → 'SH', '92' → 'BJ'.
        if code[:2] in ["00", "30"]:
            code = f"{code}.SZ"
        elif code[:2] in ["60", "68"]:
            code = f"{code}.SH"
        elif code[:2] in ["92"]:
            code = f"{code}.BJ"

        query: str = self.input_dict["query"]

        import tushare as ts

        # Initialize the Tushare pro API using the token from environment.
        ts.set_token(token=os.getenv("TUSHARE_API_TOKEN", ""))

        code_prompt: str = self.prompt_format(
            prompt_name="code_prompt",
            code=code,
            query=query,
            current_date=get_datetime(),
            example=self.get_prompt("code_example"),
        )
        logger.info(f"code_prompt=\n{code_prompt}")

        messages = [Message(role=Role.USER, content=code_prompt)]

        def get_code(message: Message):
            """Extract Python code from the assistant response."""

            return extract_content(message.content, language_tag="python")

        result_code = await self.llm.achat(messages=messages, callback_fn=get_code)
        logger.info(f"result_code=\n{result_code}")

        # Execute the generated Python code and set the execution result.
        self.set_output(exec_code(result_code))

    async def async_default_execute(self, e: Exception = None, **_kwargs):
        """Fill outputs with a default failure message when execution fails."""

        code: str = self.input_dict["code"]
        query: str = self.input_dict["query"]
        error_msg = f"Failed to execute code={code} query={query}"
        if e:
            error_msg += f": {str(e)}"
        self.set_output(error_msg)
