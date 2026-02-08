"""Google search operation via Serper API.

This module provides Google search functionality through the Serper API,
supporting rich search results including organic results, knowledge graphs,
people also ask, and related searches.
"""

import asyncio
import json
import os

from flowllm.core.context import C
from flowllm.core.op import BaseAsyncToolOp
from flowllm.core.schema import ToolCall
from loguru import logger


@C.register_op()
class GoogleSearchOp(BaseAsyncToolOp):
    """Perform Google searches via Serper API and retrieve rich results.
    
    This operation provides access to Google search results through the Serper API,
    returning organic search results, people also ask, related searches, and knowledge graph.
    Supports filtering options and retry logic for robust operation.
    """

    file_path: str = __file__

    def __init__(
        self,
        num_results: int = 10,
        max_retries: int = 5,
        remove_snippets: bool = None,
        remove_knowledge_graph: bool = None,
        remove_answer_box: bool = None,
        **kwargs,
    ):
        """Create a new Google search operation.

        Args:
            num_results: Maximum number of search results to return (default: 10).
            max_retries: Maximum number of retry attempts (default: 5).
            remove_snippets: Whether to remove snippets from results. If None, reads from env.
            remove_knowledge_graph: Whether to remove knowledge graph. If None, reads from env.
            remove_answer_box: Whether to remove answer box. If None, reads from env.
            **kwargs: Extra keyword arguments forwarded to BaseAsyncToolOp.
        """
        super().__init__(**kwargs)
        self.num_results: int = num_results
        self.max_retries: int = max_retries
        
        # Read filter settings from environment or use provided values
        self.remove_snippets = (
            remove_snippets
            if remove_snippets is not None
            else os.environ.get("REMOVE_SNIPPETS", "").lower() in ("true", "1", "yes")
        )
        self.remove_knowledge_graph = (
            remove_knowledge_graph
            if remove_knowledge_graph is not None
            else os.environ.get("REMOVE_KNOWLEDGE_GRAPH", "").lower() in ("true", "1", "yes")
        )
        self.remove_answer_box = (
            remove_answer_box
            if remove_answer_box is not None
            else os.environ.get("REMOVE_ANSWER_BOX", "").lower() in ("true", "1", "yes")
        )

        self._client = None
        self.api_key = os.environ.get("SERPER_API_KEY", "")

    def build_tool_call(self) -> ToolCall:
        """Build the tool call schema for Google search."""
        return ToolCall(
            **{
                "description": self.get_prompt("tool_description"),
                "input_schema": {
                    "q": {
                        "type": "string",
                        "description": "Search query string",
                        "required": True,
                    },
                    "gl": {
                        "type": "string",
                        "description": "Country context for search (e.g., 'us', 'cn', 'uk'). Default: 'us'",
                        "required": False,
                    },
                    "hl": {
                        "type": "string",
                        "description": "Google interface language (e.g., 'en', 'zh', 'es'). Default: 'en'",
                        "required": False,
                    },
                    "location": {
                        "type": "string",
                        "description": "City-level location (e.g., 'California, United States')",
                        "required": False,
                    },
                    "num": {
                        "type": "integer",
                        "description": "Number of results to return. Default: 10",
                        "required": False,
                    },
                    "tbs": {
                        "type": "string",
                        "description": "Time-based filter ('qdr:h'=hour, 'qdr:d'=day, 'qdr:w'=week, 'qdr:m'=month, 'qdr:y'=year)",
                        "required": False,
                    },
                    "page": {
                        "type": "integer",
                        "description": "Page number of results. Default: 1",
                        "required": False,
                    },
                },
            },
        )

    @property
    def client(self):
        """Get or create the httpx async client instance."""
        if self._client is None:
            import httpx

            self._client = httpx.AsyncClient(
                base_url="https://google.serper.dev",
                headers={
                    "X-API-KEY": self.api_key,
                    "Content-Type": "application/json",
                },
                timeout=30.0,
            )
        return self._client

    def _filter_search_result(self, result_content: str) -> str:
        """Filter Google search result content based on configuration.

        Args:
            result_content: The JSON string result from Google search.

        Returns:
            Filtered JSON string result.
        """
        try:
            # Parse JSON
            data = json.loads(result_content)

            # Remove knowledgeGraph if requested
            if self.remove_knowledge_graph and "knowledgeGraph" in data:
                del data["knowledgeGraph"]

            # Remove answerBox if requested
            if self.remove_answer_box and "answerBox" in data:
                del data["answerBox"]

            # Remove snippets if requested
            if self.remove_snippets:
                # Remove snippets from organic results
                if "organic" in data:
                    for item in data["organic"]:
                        if "snippet" in item:
                            del item["snippet"]

                # Remove snippets from peopleAlsoAsk
                if "peopleAlsoAsk" in data:
                    for item in data["peopleAlsoAsk"]:
                        if "snippet" in item:
                            del item["snippet"]

            # Return filtered JSON
            return json.dumps(data, ensure_ascii=False, indent=2)

        except (json.JSONDecodeError, Exception) as e:
            logger.warning(f"Failed to filter search results: {e}")
            # If filtering fails, return original content
            return result_content

    async def async_execute(self):
        """Execute the Google search for the given query.

        The query is read from input_dict and the result is returned as a
        JSON-formatted string containing organic results, knowledge graphs,
        answer boxes, people also ask, and related searches.
        """
        if not self.api_key:
            self.set_output(
                "Error: SERPER_API_KEY is not set. Google search tool is not available."
            )
            return

        # Get search parameters
        q: str = self.input_dict["q"]
        gl: str = self.input_dict.get("gl", "us")
        hl: str = self.input_dict.get("hl", "en")
        location: str = self.input_dict.get("location")
        num: int = self.input_dict.get("num", self.num_results)
        tbs: str = self.input_dict.get("tbs")
        page: int = self.input_dict.get("page", 1)

        logger.info(f"google_search.query: {q}, gl: {gl}, hl: {hl}, num: {num}, page: {page}")

        # Check cache
        if self.enable_cache:
            cache_key = f"{q}_{gl}_{hl}_{location}_{num}_{tbs}_{page}"
            cached_result = self.cache.load(cache_key)
            if cached_result:
                self.set_output(cached_result)
                return

        # Prepare request payload
        payload = {
            "q": q,
            "gl": gl,
            "hl": hl,
            "num": num,
            "page": page,
            "autocorrect": False,
        }

        if location:
            payload["location"] = location
        if tbs:
            payload["tbs"] = tbs

        # Execute search with retry logic
        retry_count = 0
        result_content = None

        while retry_count < self.max_retries:
            try:
                response = await self.client.post("/search", json=payload)
                response.raise_for_status()

                data = response.json()
                result_content = json.dumps(data, ensure_ascii=False, indent=2)

                # Validate result
                if not result_content or result_content.strip() == "":
                    raise RuntimeError("Empty result from Google search")

                # Apply filtering based on configuration
                filtered_result = self._filter_search_result(result_content)

                # Cache the result
                if self.enable_cache:
                    cache_key = f"{q}_{gl}_{hl}_{location}_{num}_{tbs}_{page}"
                    self.cache.save(cache_key, filtered_result, expire_hours=self.cache_expire_hours)

                self.set_output(filtered_result)
                return

            except Exception as error:
                retry_count += 1
                logger.warning(
                    f"Google search attempt {retry_count}/{self.max_retries} failed: {error}"
                )

                if retry_count >= self.max_retries:
                    error_msg = (
                        f"Error: Google search tool execution failed after {self.max_retries} attempts: {str(error)}"
                    )
                    self.set_output(error_msg)
                    return

                # Wait before retrying (exponential backoff, max 60s)
                await asyncio.sleep(min(2**retry_count, 60))

        # Fallback error message
        self.set_output(
            "Error: Unknown error occurred in Google search tool, please try again."
        )

    async def async_default_execute(self, e: Exception = None, **_kwargs):
        """Fill outputs with a default failure message when execution fails."""
        error_msg = "Failed to execute Google search"
        if e:
            error_msg += f": {str(e)}"
        self.set_output(error_msg)

    async def __aenter__(self):
        """Enter async context and return self."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Clean up resources when exiting async context."""
        if self._client is not None:
            await self._client.aclose()
            self._client = None
