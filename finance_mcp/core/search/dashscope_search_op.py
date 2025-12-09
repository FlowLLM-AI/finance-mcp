"""Dashscope web search operation module.

This module provides a tool operation for performing web searches using the Dashscope API.
It enables LLM models to retrieve relevant information from the internet by executing
search queries and returning formatted results.
"""

import os

from flowllm.core.context import C
from flowllm.core.op import BaseAsyncToolOp
from flowllm.core.schema import ToolCall
from loguru import logger


@C.register_op()
class DashscopeSearchOp(BaseAsyncToolOp):
    """A tool operation for performing web searches using Dashscope API.

    This operation enables LLM models to search the internet for information by
    providing search keywords. It supports various search strategies and can
    optionally use role prompts to enhance search queries.
    """

    file_path: str = __file__

    def __init__(
        self,
        model: str = "qwen-flash",
        search_strategy: str = "max",
        enable_role_prompt: bool = True,
        **kwargs,
    ):
        """Initialize the Dashscope search operation.

        Args:
            model: Name of the Dashscope model to use.
            search_strategy: Web search strategy, such as ``"max"``.
            enable_role_prompt: Whether to wrap the user query with an
                additional role prompt from the prompt template.
            **kwargs: Extra keyword arguments forwarded to
                :class:`BaseAsyncToolOp`.
        """

        super().__init__(**kwargs)

        self.model: str = model
        self.search_strategy: str = search_strategy
        self.enable_role_prompt: bool = enable_role_prompt

        self.api_key = os.getenv("DASHSCOPE_API_KEY", "")
        # https://help.aliyun.com/zh/model-studio/web-search

    def build_tool_call(self) -> ToolCall:
        """Build the tool call schema for the Dashscope search op."""

        return ToolCall(
            **{
                "description": self.get_prompt("tool_description"),
                "input_schema": {
                    "query": {
                        "type": "string",
                        "description": "search keyword",
                        "required": True,
                    },
                },
            },
        )

    async def async_execute(self):
        """Execute a Dashscope web search for the given query.

        The method prepares the user query (optionally using a role
        prompt), calls the Dashscope generation API with search enabled,
        and returns the natural-language answer produced by the model.
        """

        query: str = self.input_dict["query"]

        if self.enable_cache:
            cached_result = self.cache.load(query)
            if cached_result:
                self.set_output(cached_result["response_content"])
                return

        if self.enable_role_prompt:
            user_query = self.prompt_format(prompt_name="role_prompt", query=query)
        else:
            user_query = query
        logger.info(f"user_query={user_query}")
        messages: list = [{"role": "user", "content": user_query}]

        import dashscope

        response = await dashscope.AioGeneration.call(
            api_key=self.api_key,
            model=self.model,
            messages=messages,
            enable_search=True,  # Enable web search
            search_options={
                "forced_search": True,  # Force web search
                "enable_source": True,  # Include search source information
                "enable_citation": False,  # Enable citation markers
                "search_strategy": self.search_strategy,  # Search strategy
            },
            result_format="message",
        )

        search_results = []
        response_content = ""

        if hasattr(response, "output") and response.output:
            if hasattr(response.output, "search_info") and response.output.search_info:
                search_results = response.output.search_info.get("search_results", [])

            if hasattr(response.output, "choices") and response.output.choices and len(response.output.choices) > 0:
                response_content = response.output.choices[0].message.content

        final_result = {
            "query": query,
            "search_results": search_results,
            "response_content": response_content,
            "model": self.model,
            "search_strategy": self.search_strategy,
        }

        if self.enable_cache:
            self.cache.save(query, final_result, expire_hours=self.cache_expire_hours)

        self.set_output(final_result["response_content"])
