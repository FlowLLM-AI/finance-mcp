"""Ops for extracting entities and resolving their security codes.

This module defines an async tool op that:

* Uses an LLM to extract financial entities (e.g. stocks, ETFs, funds)
  from a natural language query.
* For supported entities, calls a downstream search op to resolve the
  corresponding security codes and attaches them back to the entities.
"""

import json
from typing import List

from flowllm.core.context import C
from flowllm.core.enumeration import Role
from flowllm.core.op import BaseAsyncToolOp
from flowllm.core.schema import ToolCall, Message
from flowllm.core.utils import extract_content
from loguru import logger


@C.register_op()
class ExtractEntitiesCodeOp(BaseAsyncToolOp):
    """Async op that extracts entities from a query and fetches their codes.

    The op expects a single input field ``query`` containing a natural
    language question or statement about financial instruments. The LLM is
    first prompted to return a JSON list describing all mentioned entities.
    For entities representing stocks or funds, an additional async tool is
    called to resolve the corresponding security codes.
    """

    file_path: str = __file__

    def build_tool_call(self) -> ToolCall:
        """Build the tool-call schema exposed to the outer tool framework.

        Returns:
            ``ToolCall`` describing the op metadata, including the
            description prompt and required input schema.
        """

        return ToolCall(
            **{
                "description": self.get_prompt("tool_description"),
                "input_schema": {
                    "query": {
                        "type": "string",
                        "description": "Natural language query about financial entities.",
                        "required": True,
                    },
                },
            },
        )

    async def get_entity_code(self, entity: str, entity_type: str):
        """Resolve security codes for a single entity using a search op.

        This helper method delegates to the first configured sub-op (usually
        a search op) to obtain raw search results, then prompts the LLM to
        extract one or more security codes from that text.

        Args:
            entity: Entity name, such as a company or fund name.
            entity_type: Entity type returned by the LLM, e.g. ``"stock"``
                or ``"fund"``.

        Returns:
            A mapping with the original ``entity`` and a list of resolved
            ``codes``.
        """

        # Currently we only expect a single configured downstream op.
        search_op = list(self.ops.values())[0]
        assert isinstance(search_op, BaseAsyncToolOp)
        await search_op.async_call(query=f"the {entity_type} code of {entity}")

        extract_code_prompt: str = self.prompt_format(
            prompt_name="extract_code_prompt",
            entity=entity,
            text=search_op.output,
        )

        def callback_fn(message: Message):
            """Return plain text content from the assistant message."""

            return extract_content(message.content)

        assistant_result = await self.llm.achat(
            messages=[Message(role=Role.USER, content=extract_code_prompt)],
            callback_fn=callback_fn,
        )
        logger.info(
            "entity=%s response=%s %s",
            entity,
            search_op.output,
            json.dumps(assistant_result, ensure_ascii=False),
        )
        return {"entity": entity, "codes": assistant_result}

    async def async_execute(self):
        """Run the main pipeline: extract entities then enrich them with codes.

        The method first prompts the LLM to return a JSON list of entities
        mentioned in the user ``query``. For supported financial types, it
        schedules parallel async tasks to fetch their security codes and
        merges the results back into the original entity list.
        """

        query = self.input_dict["query"]
        extract_entities_prompt: str = self.prompt_format(
            prompt_name="extract_entities_prompt",
            example=self.get_prompt(prompt_name="extract_entities_example"),
            query=query,
        )

        def callback_fn(message: Message):
            """Parse the assistant response as JSON content."""

            return extract_content(message.content, language_tag="json")

        assistant_result: List[dict] = await self.llm.achat(
            messages=[Message(role=Role.USER, content=extract_entities_prompt)],
            callback_fn=callback_fn,
        )
        logger.info(json.dumps(assistant_result, ensure_ascii=False))

        entity_list = []  # Track entities that will have codes resolved.
        for entity_info in assistant_result:
            # Only resolve codes for stock- or fund-like entities.
            if entity_info["type"] in ["stock", "股票", "etf", "fund"]:
                entity_list.append(entity_info["entity"])
                self.submit_async_task(
                    self.get_entity_code,
                    entity=entity_info["entity"],
                    entity_type=entity_info["type"],
                )

        # Wait for all async code-resolution tasks and merge results.
        for t_result in await self.join_async_task():
            entity = t_result["entity"]
            codes = t_result["codes"]
            for entity_info in assistant_result:
                if entity_info["entity"] == entity:
                    entity_info["codes"] = codes

        # Store JSON string as final op output.
        self.set_output(json.dumps(assistant_result, ensure_ascii=False))
