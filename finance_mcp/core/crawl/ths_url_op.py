"""Operations for constructing URLs to the THS (10jqka) stock pages.

This module defines a simple FlowLLM operation that populates a formatted
URL for the THS basic stock information site based on the current
``context.code`` and a configurable ``tag``.
"""

from flowllm.core.context import C
from flowllm.core.op import BaseAsyncOp
from loguru import logger


@C.register_op()
class ThsUrlOp(BaseAsyncOp):
    """Build a THS (10jqka) stock information URL.

    The operation reads the stock code from ``self.context.code`` and combines
    it with an optional ``tag`` segment to form a URL pointing to the THS
    basic information page.  The resulting URL is stored on
    ``self.context.url`` for later consumption by downstream operations.

    Parameters
    ----------
    tag:
        Optional path segment appended before the ``.html`` suffix.  This can
        be used to navigate to different subpages for the same stock.
    **kwargs:
        Additional keyword arguments forwarded to :class:`BaseAsyncOp`.
    """

    def __init__(self, tag: str = "", **kwargs):
        super().__init__(**kwargs)
        # Extra path segment that customizes the THS page being addressed.
        self.tag: str = tag

    async def async_execute(self):
        """Populate ``context.url`` with the computed THS stock page URL.

        The method does not perform any network requests.  It only constructs
        the URL and logs it for traceability.
        """

        self.context.url = f"https://basic.10jqka.com.cn/{self.context.code}/{self.tag}.html#stockpage"
        logger.info(f"{self.name} url={self.context.url}")
