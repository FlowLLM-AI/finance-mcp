# flake8: noqa: E402
# pylint: disable=wrong-import-position

"""Async web crawling operations based on the crawl4ai library.

This module provides FlowLLM-compatible operations that wrap the `crawl4ai`
asynchronous web crawler.  The main entry point is :class:`Crawl4aiOp`, which
fetches the content of a single URL and returns a Markdown representation of
the page.  :class:`Crawl4aiLongTextOp` is a thin specialization intended for
long-text outputs.

The implementation also handles Playwright browser installation on demand and
adds a small caching layer based on the parent :class:`BaseAsyncToolOp`.
"""
import asyncio
import warnings

from loguru import logger
from pydantic.warnings import PydanticDeprecatedSince20

warnings.filterwarnings("ignore", category=PydanticDeprecatedSince20)

from crawl4ai import BrowserConfig, CrawlerRunConfig, CacheMode, AsyncWebCrawler
from flowllm.core.context import C
from flowllm.core.op import BaseAsyncToolOp
from flowllm.core.schema import ToolCall

from ..utils import get_random_user_agent


@C.register_op()
class Crawl4aiOp(BaseAsyncToolOp):
    """Crawl a single URL and return its content as Markdown.

    The operation relies on the `crawl4ai` asynchronous crawler and integrates
    with FlowLLM as a tool operation.  It supports:

    - Optional caching of responses via the base ``BaseAsyncToolOp`` cache.
    - Configurable maximum length of the returned Markdown string.
    - Lazy initialization of Playwright and automatic browser installation if
      the required runtime is missing.

    Parameters
    ----------
    max_content_char_length:
        Maximum number of characters from the crawled Markdown content to
        include in the final result.
    enable_cache:
        Whether to enable caching of results based on the URL hash.
    cache_expire_hours:
        Cache expiration time in hours when caching is enabled.
    **kwargs:
        Additional keyword arguments forwarded to :class:`BaseAsyncToolOp`.
    """

    # Class variable to track if playwright has been installed
    _playwright_installed = False

    def __init__(
        self,
        max_content_char_length: int = 50000,
        enable_cache: bool = True,
        cache_expire_hours: float = 1,
        **kwargs,
    ):

        super().__init__(
            enable_cache=enable_cache,
            cache_expire_hours=cache_expire_hours,
            **kwargs,
        )

        # Maximal length safeguard to avoid over-long responses in downstream LLMs.
        self.max_content_char_length: int = max_content_char_length
        # These configs are initialized lazily in ``async_execute``.
        self.browser_config = None
        self.crawler_config = None

    def build_tool_call(self) -> ToolCall:
        """Build the :class:`ToolCall` schema used to describe this operation.

        The returned object defines how the tool is exposed to agents,
        including the expected input fields and a human-readable description.
        """

        return ToolCall(
            **{
                "description": "Crawl the content from the specified URL using crawl4ai.",
                "input_schema": {
                    "url": {
                        "type": "string",
                        "description": "url to be crawled",
                        "required": True,
                    },
                },
            },
        )

    async def async_execute(self):
        """Execute the crawl operation asynchronously.

        Steps
        -----
        1. Read the target URL from ``self.input_dict``.
        2. If caching is enabled, try to load a cached response.
        3. Initialize crawler configuration and ensure Playwright is available.
        4. Use :class:`AsyncWebCrawler` to fetch the page and extract Markdown.
        5. Truncate the content to ``max_content_char_length`` and save it as
           both tool output and (optionally) a cached entry.
        """
        url: str = self.input_dict["url"]

        if self.enable_cache:
            cached_result = self.cache.load(hash(url))
            if cached_result:
                self.set_output(cached_result["response_content"])
                return

        # Initialize configs lazily to avoid unnecessary browser startup
        self.browser_config = BrowserConfig(
            headless=True,
            java_script_enabled=True,
            user_agent=get_random_user_agent(),
            viewport={"width": 1280, "height": 800},
            verbose=True,
        )

        self.crawler_config = CrawlerRunConfig(cache_mode=CacheMode.BYPASS, verbose=True)

        # Install playwright only once using class variable
        if not Crawl4aiOp._playwright_installed:
            process = await asyncio.create_subprocess_exec(
                "playwright",
                "install",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await process.communicate()
            logger.info(f"Playwright installation completed with exit stdout={stdout} stderr={stderr}")
            Crawl4aiOp._playwright_installed = True

        # Run the asynchronous crawl and capture the Markdown content.
        async with AsyncWebCrawler(config=self.browser_config) as crawler:
            result = await crawler.arun(url=url, config=self.crawler_config)
            response_content = result.markdown[: self.max_content_char_length]

            final_result = {
                "url": url,
                "response_content": response_content,
            }

            if self.enable_cache:
                self.cache.save(hash(url), final_result, expire_hours=self.cache_expire_hours)

            self.set_output(response_content)


@C.register_op()
class Crawl4aiLongTextOp(Crawl4aiOp):
    """Specialized crawl operation for long-text responses.

    This subclass of :class:`Crawl4aiOp` only adjusts the
    ``output_schema_mapping`` so that downstream components can recognize the
    result as ``long_text``.  All crawling behavior is inherited from the
    parent class.
    """

    def __init__(self, **kwargs):
        """Initialize the long-text crawl operation.

        Parameters
        ----------
        **kwargs:
            Additional keyword arguments passed through to
            :class:`Crawl4aiOp`.  The ``output_schema_mapping`` field is
            defaulted to ``{"crawl4ai_long_text_result": "long_text"}`` if
            not provided.
        """

        kwargs.setdefault("output_schema_mapping", {"crawl4ai_long_text_result": "long_text"})
        super().__init__(**kwargs)
