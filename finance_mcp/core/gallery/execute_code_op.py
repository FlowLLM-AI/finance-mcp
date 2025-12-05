import asyncio
import sys
from io import StringIO

from flowllm.core.context import C
from flowllm.core.op import BaseAsyncToolOp
from flowllm.core.schema import ToolCall
from loguru import logger


@C.register_op()
class ExecuteCodeOp(BaseAsyncToolOp):

    def build_tool_call(self) -> ToolCall:
        return ToolCall(
            **{
                "description": self.get_prompt("tool_description"),
                "input_schema": {
                    "code": {
                        "type": "string",
                        "description": "code to be executed",
                        "required": True,
                    },
                },
            },
        )

    def execute(self):
        old_stdout = sys.stdout
        redirected_output = sys.stdout = StringIO()

        try:
            code: str = self.input_dict["code"]
            exec(code)
            code_result = redirected_output.getvalue()

        except Exception as e:
            logger.info(f"{self.name} encounter exception! error={e.args}")
            code_result = str(e)

        sys.stdout = old_stdout
        self.set_output(code_result)

    async def async_execute(self):
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(C.thread_pool, self.execute)  # noqa
