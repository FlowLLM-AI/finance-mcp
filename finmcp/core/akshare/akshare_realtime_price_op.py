import asyncio
import json
from typing import Optional

import pandas as pd
from flowllm.core.context import C
from flowllm.core.op import BaseAsyncToolOp
from flowllm.core.schema import ToolCall


@C.register_op()
class AkshareRealtimePriceOp(BaseAsyncToolOp):

    def __init__(
        self,
        enable_cache: bool = True,
        cache_expire_hours: float = 0.1,
        **kwargs,
    ):
        super().__init__(enable_cache=enable_cache, cache_expire_hours=cache_expire_hours, **kwargs)

    def build_tool_call(self) -> ToolCall:
        return ToolCall(
            **{
                "description": "查询A股股票实时股价",
                "input_schema": {
                    "code": {
                        "type": "string",
                        "description": "A股股票代码",
                        "required": True,
                    },
                },
            },
        )

    @staticmethod
    def download_a_stock_df():
        import akshare as ak

        stock_sh_a_spot_em_df = ak.stock_sh_a_spot_em()
        stock_sz_a_spot_em_df = ak.stock_sz_a_spot_em()
        stock_bj_a_spot_em_df = ak.stock_bj_a_spot_em()

        df: pd.DataFrame = pd.concat(
            [stock_sh_a_spot_em_df, stock_sz_a_spot_em_df, stock_bj_a_spot_em_df],
            axis=0,
        )
        df = df.drop(columns=["序号"])
        df = df.reset_index(drop=True)
        df = df.sort_values(by="代码")
        return df

    async def async_execute(self):
        code: str = self.input_dict["code"]

        df: Optional[pd.DataFrame] = None
        if self.enable_cache:
            df = self.cache.load(code, dtype={"代码": str})

        if df is None:
            loop = asyncio.get_event_loop()
            df = await loop.run_in_executor(C.thread_pool, self.download_a_stock_df)  ## noqa

        if self.enable_cache:
            self.cache.save(code, df, expire_hours=self.cache_expire_hours)

        result = df.loc[df["代码"] == code, :].to_dict(orient="records")[-1]
        response: str = f"{code}的实时行情: {json.dumps(result, ensure_ascii=False)}"
        self.set_output(response)
