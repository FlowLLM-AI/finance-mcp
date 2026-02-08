"""Test web scraping operation."""

import asyncio
import os
from finance_mcp import FinanceMcpApp
from finance_mcp.core.search.web_scrape_op import WebScrapeOp
from loguru import logger


async def test_web_scrape():
    """Test web scraping with various URLs."""
    
    # Test URLs
    test_cases = [
        {
            "name": "Simple webpage",
            "url": "https://example.com",
        },
        {
            "name": "News article",
            "url": "https://www.bbc.com/news",
        },
        {
            "name": "URL without protocol",
            "url": "example.com",
        },
    ]
    
    async with FinanceMcpApp():
        for test_case in test_cases:
            logger.info(f"\n{'='*60}")
            logger.info(f"Testing: {test_case['name']}")
            logger.info(f"URL: {test_case['url']}")
            logger.info(f"{'='*60}")
            
            try:
                # Create operation instance
                op = WebScrapeOp(enable_cache=False)
                
                # Execute using async_call
                await op.async_call(url=test_case["url"])
                
                # Get output
                result = op.output
                
                logger.info(f"Success! Content length: {len(result)}")
                logger.info(f"Preview:\n{result[:500]}...")
                
            except Exception as e:
                logger.error(f"Error: {e}")
                import traceback
                traceback.print_exc()
            
            # Add delay between requests
            await asyncio.sleep(2)


async def test_web_scrape_with_jina():
    """Test web scraping with Jina API explicitly."""
    
    jina_api_key = os.getenv("JINA_API_KEY")
    if not jina_api_key:
        logger.warning("JINA_API_KEY not set, skipping Jina-specific test")
        return
    
    logger.info(f"\n{'='*60}")
    logger.info("Testing with Jina API")
    logger.info(f"{'='*60}")
    
    async with FinanceMcpApp():
        try:
            op = WebScrapeOp(
                jina_api_key=jina_api_key,
                enable_cache=False,
            )
            
            # Execute using async_call
            await op.async_call(url="https://news.ycombinator.com")
            result = op.output
            
            logger.info(f"Success! Content length: {len(result)}")
            logger.info(f"Preview:\n{result[:500]}...")
            
        except Exception as e:
            logger.error(f"Error: {e}")
            import traceback
            traceback.print_exc()


async def test_error_cases():
    """Test error handling."""
    
    error_cases = [
        {
            "name": "Empty URL",
            "url": "",
        },
        {
            "name": "Hugging Face dataset",
            "url": "https://huggingface.co/datasets/some-dataset",
        },
    ]
    
    async with FinanceMcpApp():
        for test_case in error_cases:
            logger.info(f"\n{'='*60}")
            logger.info(f"Testing error case: {test_case['name']}")
            logger.info(f"{'='*60}")
            
            try:
                op = WebScrapeOp(enable_cache=False)
                await op.async_call(url=test_case["url"])
                result = op.output
                logger.info(f"Result: {result}")
                
            except Exception as e:
                logger.error(f"Error: {e}")
                import traceback
                traceback.print_exc()


async def main():
    """Run all tests."""
    logger.info("Starting web scrape tests...")
    
    # Test basic functionality
    await test_web_scrape()
    
    # Test with Jina API
    await test_web_scrape_with_jina()
    
    # Test error cases
    await test_error_cases()
    
    logger.info("\nAll tests completed!")


if __name__ == "__main__":
    asyncio.run(main())
