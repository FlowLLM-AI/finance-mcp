"""Entry point and application wrapper for the Finance MCP service.

This module exposes a thin wrapper around :class:`flowllm.core.application.Application`
that wires it to the finance-mcp configuration system. The :class:`FinanceMcpApp`
class is intended to be used as a context manager from the command line, where the
CLI arguments are forwarded directly to the underlying FlowLLM application.
"""

import sys

from flowllm.core.application import Application

from .config import ConfigParser


class FinanceMcpApp(Application):
    """Concrete FlowLLM application for the Finance MCP package.

    This subclass simply pre-configures the base :class:`Application` with the
    finance-mcp specific configuration parser and sensible defaults. All heavy
    lifting (service lifecycle, routing, etc.) is delegated to the parent class.
    """

    def __init__(
        self,
        *args,
        llm_api_key: str = None,
        llm_api_base: str = None,
        embedding_api_key: str = None,
        embedding_api_base: str = None,
        config_path: str = None,
        **kwargs,
    ):
        """Initialize the Finance MCP application.

        Parameters
        ----------
        *args:
            Positional arguments forwarded to :class:`Application`.
        llm_api_key:
            API key used by the underlying LLM provider. If omitted, the
            provider-specific default resolution (for example environment
            variables) is used.
        llm_api_base:
            Optional base URL for the LLM API endpoint.
        embedding_api_key:
            API key for the embedding model provider, if different from the
            main LLM provider.
        embedding_api_base:
            Optional base URL for the embedding API endpoint.
        config_path:
            Optional path to an explicit configuration file. When omitted, the
            default configuration discovery rules of :class:`PydanticConfigParser`
            are applied.
        **kwargs:
            Additional keyword arguments forwarded untouched to
            :class:`Application`.
        """

        # Delegate to the generic FlowLLM application, but force the parser
        # and configuration options that are specific to the Finance MCP
        # package. ``service_config`` is left as ``None`` so that it is fully
        # loaded from the configuration files.
        super().__init__(
            *args,
            llm_api_key=llm_api_key,
            llm_api_base=llm_api_base,
            embedding_api_key=embedding_api_key,
            embedding_api_base=embedding_api_base,
            service_config=None,
            parser=ConfigParser,
            config_path=config_path,
            load_default_config=True,
            **kwargs,
        )


def main() -> None:
    """Run the Finance MCP service as a command-line application.

    The function builds :class:`FinanceMcpApp` from the command-line arguments
    (excluding the script name) and starts the FlowLLM service loop. It is
    intentionally minimal so that the application lifecycle remains controlled
    by :class:`Application`.
    """

    # ``sys.argv[1:]`` contains user-provided CLI arguments that the
    # :class:`Application` implementation is responsible for interpreting.
    with FinanceMcpApp(*sys.argv[1:]) as app:
        app.run_service()


if __name__ == "__main__":
    # Allow the module to be executed directly via ``python -m finance_mcp``
    # or by invoking the script file. In both cases we delegate to ``main``.
    main()
