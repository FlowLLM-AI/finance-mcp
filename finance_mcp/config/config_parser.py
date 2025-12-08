"""Configuration parser integration for Finance MCP.

This module provides a thin wrapper around FlowLLM's
``PydanticConfigParser`` so that the framework can automatically discover and
load configuration files that are colocated with this package.
"""

from flowllm.core.utils import PydanticConfigParser


class ConfigParser(PydanticConfigParser):
    """Specialized configuration parser for the Finance MCP package.

    The only customization over :class:`PydanticConfigParser` is the
    ``current_file`` attribute, which anchors the configuration discovery
    logic to the location of this module.
    """

    # Absolute path of this module; used by the base parser to resolve
    # configuration file locations relative to the package.
    current_file: str = __file__
