"""Test cases for Google search operation."""

import asyncio
import os

from finance_mcp.core.search import GoogleSearchOp


async def test_google_search_basic():
    """Test basic Google search."""
    print("\n=== Testing GoogleSearchOp (basic) ===")
    
    if not os.environ.get("SERPER_API_KEY"):
        print("Warning: SERPER_API_KEY not set, skipping test")
        return
    
    async with GoogleSearchOp(enable_cache=False) as op:
        op.input_dict = {"q": "Python programming language"}
        await op.async_execute()
        result = op.output
        
        # Truncate for display
        if len(result) > 1000:
            print(f"Result (first 1000 chars):\n{result[:1000]}...")
        else:
            print(f"Result:\n{result}")


async def test_google_search_with_params():
    """Test Google search with various parameters."""
    print("\n=== Testing GoogleSearchOp (with parameters) ===")
    
    if not os.environ.get("SERPER_API_KEY"):
        print("Warning: SERPER_API_KEY not set, skipping test")
        return
    
    async with GoogleSearchOp(enable_cache=False) as op:
        op.input_dict = {
            "q": "artificial intelligence news",
            "gl": "us",
            "hl": "en",
            "num": 5,
            "tbs": "qdr:w",  # Past week
        }
        await op.async_execute()
        result = op.output
        
        # Truncate for display
        if len(result) > 1000:
            print(f"Result (first 1000 chars):\n{result[:1000]}...")
        else:
            print(f"Result:\n{result}")


async def test_google_search_chinese():
    """Test Google search with Chinese query."""
    print("\n=== Testing GoogleSearchOp (Chinese) ===")
    
    if not os.environ.get("SERPER_API_KEY"):
        print("Warning: SERPER_API_KEY not set, skipping test")
        return
    
    async with GoogleSearchOp(enable_cache=False) as op:
        op.input_dict = {
            "q": "人工智能",
            "gl": "cn",
            "hl": "zh",
            "num": 5,
        }
        await op.async_execute()
        result = op.output
        
        # Truncate for display
        if len(result) > 1000:
            print(f"Result (first 1000 chars):\n{result[:1000]}...")
        else:
            print(f"Result:\n{result}")


async def test_google_search_with_filters():
    """Test Google search with content filters."""
    print("\n=== Testing GoogleSearchOp (with filters) ===")
    
    if not os.environ.get("SERPER_API_KEY"):
        print("Warning: SERPER_API_KEY not set, skipping test")
        return
    
    async with GoogleSearchOp(
        enable_cache=False,
        remove_snippets=True,
        remove_knowledge_graph=True,
    ) as op:
        op.input_dict = {
            "q": "OpenAI GPT",
            "num": 3,
        }
        await op.async_execute()
        result = op.output
        
        # Truncate for display
        if len(result) > 1000:
            print(f"Result (first 1000 chars):\n{result[:1000]}...")
        else:
            print(f"Result:\n{result}")


async def main():
    """Run all tests."""
    try:
        await test_google_search_basic()
    except Exception as e:
        print(f"Error in test_google_search_basic: {e}")

    try:
        await test_google_search_with_params()
    except Exception as e:
        print(f"Error in test_google_search_with_params: {e}")

    try:
        await test_google_search_chinese()
    except Exception as e:
        print(f"Error in test_google_search_chinese: {e}")

    try:
        await test_google_search_with_filters()
    except Exception as e:
        print(f"Error in test_google_search_with_filters: {e}")


if __name__ == "__main__":
    asyncio.run(main())
