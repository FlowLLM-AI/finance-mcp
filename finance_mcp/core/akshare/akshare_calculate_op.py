import sys
from io import StringIO

from flowllm.core.context import C
from flowllm.core.enumeration import Role
from flowllm.core.op import BaseAsyncToolOp
from flowllm.core.schema import ToolCall, Message
from flowllm.core.utils import extract_content
from loguru import logger

from ..utils import get_datetime


@C.register_op()
class AkshareCalculateOp(BaseAsyncToolOp):
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
        query: str = self.input_dict["query"]

        akshare_code_prompt: str = self.prompt_format(
            prompt_name="akshare_code_prompt",
            code=code,
            query=query,
            current_date=get_datetime(),
            example=self.get_prompt("akshare_code_example"),
        )

        messages = [Message(role=Role.USER, content=akshare_code_prompt)]
        old_stdout = sys.stdout
        redirected_output = sys.stdout = StringIO()

        for i in range(3):

            def get_code(message: Message):
                return extract_content(message.content, language_tag="python")

            result_code = await self.llm.achat(messages=messages, callback_fn=get_code)
            logger.info(f"i={i} result_code=\n{result_code}")
            messages.append(Message(role=Role.ASSISTANT, content=result_code))

            try:
                exec(result_code)
                code_result = redirected_output.getvalue()
                messages.append(Message(role=Role.USER, content=code_result))
                break

            except Exception as e:
                logger.info(f"{self.name} encounter exception! error={e.args}")
                messages.append(Message(role=Role.USER, content=str(e)))

        sys.stdout = old_stdout
        self.set_output(messages[-1].content)
