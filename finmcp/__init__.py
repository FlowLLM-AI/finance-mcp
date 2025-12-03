import os

os.environ["FLOW_APP_NAME"] = "FinMCP"

from . import crawl

from .main import FinMcpApp

__all__ = [
    "crawl",
]

__version__ = "0.1.0"
