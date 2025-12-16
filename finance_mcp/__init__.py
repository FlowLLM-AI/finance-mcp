# flake8: noqa: E402
# pylint: disable=wrong-import-position

"""Public package interface for the Finance MCP library.

This module exposes the high-level objects that users are expected to import
from :mod:`finance_mcp`. It also sets the :envvar:`FLOW_APP_NAME` environment
variable so that the underlying FlowLLM framework can correctly associate
configuration and logging with this application.
"""

import os

# Hint FlowLLM about the logical application name. This is used by the
# framework to locate configuration files and to tag logs/telemetry.
os.environ["FLOW_APP_NAME"] = "FinanceMCP"

from . import core
from . import config

from .main import FinanceMcpApp

__all__ = [
    "core",
    "config",
    "FinanceMcpApp",
]

# Library version. Keep in sync with the project metadata.
__version__ = "0.1.4"
