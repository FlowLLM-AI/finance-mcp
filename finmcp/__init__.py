import os

os.environ["FLOW_APP_NAME"] = "FinMCP"

from . import core
from . import utils

from .main import FinMcpApp

__all__ = [
    "core",
    "utils",
    "FinMcpApp",
]

__version__ = "0.1.0"
