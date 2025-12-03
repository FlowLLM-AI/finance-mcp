from crawl4ai import BrowserConfig, CrawlerRunConfig, CacheMode, AsyncWebCrawler
from flowllm.core.context import C
from flowllm.core.op import BaseAsyncToolOp
from flowllm.core.schema import ToolCall

from finmcp.utils import get_random_user_agent


@C.register_op()
class Crawl4aiOp(BaseAsyncToolOp):

    def __init__(self,
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

        self.max_content_char_length: int = max_content_char_length
        self.browser_config = None
        self.crawler_config = None

    def build_tool_call(self) -> ToolCall:
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
        url: str = self.input_dict["url"]

        if self.enable_cache:
            cached_result = self.cache.load(hash(url))
            if cached_result:
                self.set_output(cached_result["response_content"])
                return

        # Initialize configs lazily
        self.browser_config = BrowserConfig(
            headless=True,
            java_script_enabled=True,
            user_agent=get_random_user_agent(),
            viewport={"width": 1280, "height": 800},
            verbose=True,
        )

        self.crawler_config = CrawlerRunConfig(cache_mode=CacheMode.BYPASS, verbose=True)

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
