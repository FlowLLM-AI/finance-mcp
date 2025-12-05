from flowllm.core.context import C
from flowllm.core.op import BaseAsyncOp
from loguru import logger


@C.register_op()
class ThsUrlOp(BaseAsyncOp):

    def __init__(self, tag: str = "", **kwargs):
        super().__init__(**kwargs)
        self.tag: str = tag

    async def async_execute(self):
        self.context.url = f"https://basic.10jqka.com.cn/{self.context.code}/{self.tag}.html#stockpage"
        logger.info(f"{self.name} url={self.context.url}")
