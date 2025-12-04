from flowllm.core.context import C
from flowllm.core.op import BaseAsyncOp
from loguru import logger


@C.register_op()
class ThsUrlOp(BaseAsyncOp):

    def __init__(self, url_template: str = "", **kwargs):
        super().__init__(**kwargs)
        self.url_template: str = url_template

    async def async_execute(self):
        code: str = self.context.code
        self.context.url = self.url_template.format(code=code)
        logger.info(f"{self.name} url={self.context.url}")

