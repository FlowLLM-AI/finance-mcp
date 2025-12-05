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
    file_path: str = __file__

    def build_tool_call(self) -> ToolCall:
        return ToolCall(
            **{
                "description": self.get_prompt("tool_description"),
                "input_schema": {
                    "query": {
                        "type": "string",
                        "description": "query",
                        "required": True,
                    },
                },
            },
        )

    async def get_entity_code(self, entity: str, entity_type: str):
        search_op = list(self.ops.values())[0]
        assert isinstance(search_op, BaseAsyncToolOp)
        await search_op.async_call(query=f"the {entity_type} code of {entity}")

        extract_code_prompt: str = self.prompt_format(
            prompt_name="extract_code_prompt",
            entity=entity,
            text=search_op.output,
        )

        def callback_fn(message: Message):
            return extract_content(message.content)

        assistant_result = await self.llm.achat(
            messages=[Message(role=Role.USER, content=extract_code_prompt)],
            callback_fn=callback_fn,
        )
        logger.info(f"entity={entity} response={search_op.output} {json.dumps(assistant_result, ensure_ascii=False)}")
        return {"entity": entity, "codes": assistant_result}

    async def async_execute(self):
        query = self.input_dict["query"]
        extract_entities_prompt: str = self.prompt_format(
            prompt_name="extract_entities_prompt",
            example=self.get_prompt(prompt_name="extract_entities_example"),
            query=query,
        )

        def callback_fn(message: Message):
            return extract_content(message.content, language_tag="json")

        assistant_result: List[dict] = await self.llm.achat(
            messages=[Message(role=Role.USER, content=extract_entities_prompt)],
            callback_fn=callback_fn,
        )
        logger.info(json.dumps(assistant_result, ensure_ascii=False))

        entity_list = []
        for entity_info in assistant_result:
            if entity_info["type"] in ["stock", "股票", "etf", "fund"]:
                entity_list.append(entity_info["entity"])
                self.submit_async_task(
                    self.get_entity_code,
                    entity=entity_info["entity"],
                    entity_type=entity_info["type"],
                )

        for t_result in await self.join_async_task():
            entity = t_result["entity"]
            codes = t_result["codes"]
            for entity_info in assistant_result:
                if entity_info["entity"] == entity:
                    entity_info["codes"] = codes

        self.set_output(json.dumps(assistant_result, ensure_ascii=False))
