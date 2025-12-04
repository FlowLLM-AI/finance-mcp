import os

os.environ["FLOW_APP_NAME"] = "FinMCP"

from . import core
from . import config

from .main import FinMcpApp

__all__ = [
    "core",
    "config",
    "FinMcpApp",
]

__version__ = "0.1.0"
