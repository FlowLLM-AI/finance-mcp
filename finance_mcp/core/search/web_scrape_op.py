"""Web scraping operation using Jina AI and fallback strategies.

This module provides functionality to scrape web pages and extract
their content in a readable format using multiple scraping strategies.
"""

import asyncio
import io
import os
from flowllm.core.context import C
from flowllm.core.op import BaseAsyncToolOp
from flowllm.core.schema import ToolCall
from loguru import logger


@C.register_op()
class WebScrapeOp(BaseAsyncToolOp):
    """Scrape a website for its content using smart request strategy.
    
    This operation retrieves web page content using multiple methods:
    1. Jina AI Reader API (primary, best for dynamic content)
    2. requests + MarkItDown (fallback, good for static content)
    
    Supports automatic protocol detection, retries, and special URL handling.
    """

    file_path: str = __file__

    def __init__(
        self,
        jina_api_key: str = None,
        jina_base_url: str = None,
        max_retries: int = 3,
        **kwargs
    ):
        """Create a new web scrape operation.

        Args:
            jina_api_key: Jina AI API key (default: read from JINA_API_KEY env).
            jina_base_url: Jina base URL (default: read from JINA_BASE_URL env or https://r.jina.ai).
            max_retries: Maximum retry attempts (default: 3).
            **kwargs: Extra keyword arguments forwarded to BaseAsyncToolOp.
        """
        super().__init__(**kwargs)
        self.jina_api_key = jina_api_key or os.getenv("JINA_API_KEY", "")
        self.jina_base_url = jina_base_url or os.getenv("JINA_BASE_URL", "https://r.jina.ai")
        self.max_retries = max_retries

    def build_tool_call(self) -> ToolCall:
        """Build the tool call schema for web scraping."""
        return ToolCall(
            **{
                "description": self.get_prompt("tool_description"),
                "input_schema": {
                    "url": {
                        "type": "string",
                        "description": "The URL of the website to scrape",
                        "required": True,
                    },
                },
            },
        )

    async def _scrape_jina(self, url: str) -> tuple[str, str]:
        """Scrape using Jina AI Reader API.
        
        Args:
            url: The URL to scrape.
            
        Returns:
            Tuple of (content, error_message). If successful, error_message is None.
        """
        if not self.jina_api_key:
            return None, "JINA_API_KEY is not set, JINA scraping is not available."

        import httpx

        jina_headers = {
            "Authorization": f"Bearer {self.jina_api_key}",
            "X-Base": "final",
            "X-Engine": "browser",
            "X-With-Generated-Alt": "true",
            "X-With-Iframe": "true",
            "X-With-Shadow-Dom": "true",
        }

        jina_url = f"{self.jina_base_url}/{url}"
        
        try:
            async with httpx.AsyncClient(timeout=120) as client:
                response = await client.get(jina_url, headers=jina_headers)
                
                if response.status_code == 422:
                    return (
                        None,
                        "Tool execution failed with Jina 422 error, which may indicate the URL is a file. "
                        "This tool does not support files. If you believe the URL might point to a file, "
                        "you should try using other applicable tools."
                    )
                
                response.raise_for_status()
                content = response.text
                
                # Check if page is not fully loaded and retry with longer timeout
                if "Warning: This page maybe not yet fully loaded" in content:
                    logger.info("Page not fully loaded, retrying with longer timeout...")
                    async with httpx.AsyncClient(timeout=300) as client_long:
                        response = await client_long.get(jina_url, headers=jina_headers)
                        
                        if response.status_code == 422:
                            return (
                                None,
                                "Tool execution failed with Jina 422 error after retry."
                            )
                        
                        response.raise_for_status()
                        content = response.text
                
                # Extract markdown content if present
                if isinstance(content, str) and "Markdown Content:\n" in content:
                    content = content.split("Markdown Content:\n")[1]
                
                return content, None
                
        except Exception as e:
            logger.warning(f"Jina scraping failed: {e}")
            return None, f"Failed to get content from Jina.ai: {str(e)}"

    def _scrape_requests(self, url: str) -> tuple[str, str]:
        """Scrape using requests and MarkItDown.
        
        Args:
            url: The URL to scrape.
            
        Returns:
            Tuple of (content, error_message). If successful, error_message is None.
        """
        try:
            import requests
            from markitdown import MarkItDown

            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                              "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            }
            
            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()

            try:
                stream = io.BytesIO(response.content)
                md = MarkItDown()
                content = md.convert_stream(stream).text_content
                return content, None
            except Exception as e:
                logger.warning(f"MarkItDown conversion failed: {e}, returning raw text")
                return response.text, None

        except Exception as e:
            logger.warning(f"Requests scraping failed: {e}")
            return None, f"Failed to get content from requests: {str(e)}"

    async def async_execute(self):
        """Execute the web scraping with smart request strategy."""
        url: str = self.input_dict["url"]
        logger.info(f"web_scrape.url: {url}")

        # Validate URL
        if not url:
            self.set_output("[ERROR]: Invalid URL: ''. URL cannot be empty.")
            return

        # Auto-add https:// if no protocol is specified
        protocol_hint = ""
        if not url.startswith(("http://", "https://")):
            original_url = url
            url = f"https://{url}"
            protocol_hint = f"[NOTE]: Automatically added 'https://' to URL '{original_url}' -> '{url}'\n\n"
            logger.info(f"Auto-added protocol: {url}")

        # Check for restricted domains
        if "huggingface.co/datasets" in url or "huggingface.co/spaces" in url:
            self.set_output(
                "You are trying to scrape a Hugging Face dataset for answers, "
                "please do not use the scrape tool for this purpose."
            )
            return

        # Check cache
        if self.enable_cache:
            cached_result = self.cache.load(url)
            if cached_result:
                logger.info("Cache hit")
                self.set_output(cached_result)
                return

        # Add special hints for specific URL types
        youtube_hint = ""
        if any(pattern in url for pattern in ["youtube.com/watch", "youtube.com/shorts", "youtube.com/live"]):
            youtube_hint = (
                "[NOTE]: If you need to get information about its visual or audio content, "
                "please use an appropriate video analysis tool instead. "
                "This tool may not be able to provide visual and audio content of a YouTube Video.\n\n"
            )

        # Retry loop
        retry_count = 0
        while retry_count < self.max_retries:
            try:
                error_msg = "[NOTE]: If the link is a file / image / video / audio, please use other applicable tools.\n"

                # Strategy 1: Try Jina AI (primary)
                content, jina_err = await self._scrape_jina(url)
                if jina_err:
                    error_msg += f"Failed to get content from Jina.ai: {jina_err}\n"
                    logger.warning(f"Jina failed: {jina_err}")
                elif content and content.strip():
                    result = protocol_hint + youtube_hint + content
                    
                    # Save to cache
                    if self.enable_cache:
                        self.cache.save(url, result, expire_hours=self.cache_expire_hours)
                    
                    self.set_output(result)
                    return
                else:
                    error_msg += "No content got from Jina.ai.\n"
                    logger.warning("Jina returned empty content")

                # Strategy 2: Try requests + MarkItDown (fallback)
                content, request_err = self._scrape_requests(url)
                if request_err:
                    error_msg += f"Failed to get content from requests: {request_err}\n"
                    logger.warning(f"Requests failed: {request_err}")
                elif content and content.strip():
                    result = protocol_hint + youtube_hint + content
                    
                    # Save to cache
                    if self.enable_cache:
                        self.cache.save(url, result, expire_hours=self.cache_expire_hours)
                    
                    self.set_output(result)
                    return
                else:
                    error_msg += "No content got from requests.\n"
                    logger.warning("Requests returned empty content")

                # If we reach here, all strategies failed
                raise Exception(error_msg)

            except Exception as e:
                retry_count += 1
                if retry_count >= self.max_retries:
                    error_result = f"[ERROR]: {str(e)}"
                    logger.error(f"All scraping attempts failed: {error_result}")
                    self.set_output(error_result)
                    return
                else:
                    wait_time = 4 ** retry_count
                    logger.info(f"Retry {retry_count}/{self.max_retries} after {wait_time}s")
                    await asyncio.sleep(wait_time)

    async def async_default_execute(self, e: Exception = None, **_kwargs):
        """Fill outputs with a default failure message when execution fails."""
        error_msg = "[ERROR]: Failed to scrape website"
        if e:
            error_msg += f": {str(e)}"
        self.set_output(error_msg)
