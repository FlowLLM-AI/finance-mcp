"""Configuration helpers for the Finance MCP package.

The configuration layer is built on top of FlowLLM's ``PydanticConfigParser``
and exposes a single public ``ConfigParser`` class that knows how to locate
and load finance-mcp specific settings.
"""

from .config_parser import ConfigParser

__all__ = [
    "ConfigParser",
]
