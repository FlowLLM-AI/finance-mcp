import os

os.environ["FLOW_APP_NAME"] = "FinanceMCP"

from . import core
from . import config

from .main import FinanceMcpApp

__all__ = [
    "core",
    "config",
    "FinanceMcpApp",
]

__version__ = "0.1.1"
