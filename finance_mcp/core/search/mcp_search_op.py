from flowllm.core.context import C
from flowllm.core.op import BaseMcpOp


@C.register_op()
class TongyiMcpSearchOp(BaseMcpOp):

    def __init__(self, **kwargs):
        kwargs.update(
            {
                "mcp_name": "tongyi_search",
                "tool_name": "bailian_web_search",
                "save_answer": True,
                "input_schema_optional": ["count"],
                "input_schema_deleted": ["ctx"],
            },
        )
        super().__init__(**kwargs)


@C.register_op()
class BochaMcpSearchOp(BaseMcpOp):
    def __init__(self, **kwargs):
        kwargs.update(
            {
                "mcp_name": "bochaai_search",
                "tool_name": "bocha_web_search",
                "save_answer": True,
                "input_schema_optional": ["freshness", "count"],
                "input_schema_deleted": ["ctx"],
            },
        )
        super().__init__(**kwargs)
