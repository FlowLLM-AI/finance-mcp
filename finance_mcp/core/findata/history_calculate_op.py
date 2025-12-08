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
    file_path = __file__

    def build_tool_call(self) -> ToolCall:
        return ToolCall(
            **{
                "description": self.get_prompt("tool_description"),
                "input_schema": {
                    "code": {
                        "type": "string",
                        "description": "A股股票代码",
                        "required": True,
                    },
                    "query": {
                        "type": "string",
                        "description": "用户问题",
                        "required": True,
                    },
                },
            },
        )

    async def async_execute(self):
        code: str = self.input_dict["code"]
        # '00.SZ', '30.SZ', '60.SH', '68.SH', '92.BJ'
        if code[:2] in ["00", "30"]:
            code = f"{code}.SZ"
        elif code[:2] in ["60", "68"]:
            code = f"{code}.SH"
        elif code[:2] in ["92"]:
            code = f"{code}.BJ"

        query: str = self.input_dict["query"]

        import tushare as ts

        ts.pro_api(token=os.getenv("TUSHARE_API_TOKEN", ""))

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
            return extract_content(message.content, language_tag="python")

        result_code = await self.llm.achat(messages=messages, callback_fn=get_code)
        logger.info(f"result_code=\n{result_code}")

        self.set_output(exec_code(result_code))

    async def async_default_execute(self, e: Exception = None, **kwargs):
        """Fill outputs with a default failure message when execution fails."""
        code: str = self.input_dict["code"]
        query: str = self.input_dict["query"]
        error_msg = f"Failed to execute code={code} query={query}"
        if e:
            error_msg += f": {str(e)}"
        self.set_output(error_msg)
