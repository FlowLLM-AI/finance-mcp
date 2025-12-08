"""Financial data utilities and ops.

This package contains helpers for working with historical market data,
including:

* ``TushareClient`` – a thin wrapper around the Tushare HTTP API that
  returns results as pandas ``DataFrame`` objects.
* ``HistoryCalculateOp`` – an async FlowLLM operator that generates and
  executes analysis code on top of historical data.

Only the main public classes are exported via ``__all__``.
"""

from .history_calculate_op import HistoryCalculateOp
from .tushare_client import TushareClient

__all__ = [
    "TushareClient",
    "HistoryCalculateOp",
]
