import sys

from finmcp.config import ConfigParser
from flowllm.core.application import Application


class FinMcpApp(Application):


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


def main():
    with FinMcpApp(*sys.argv[1:]) as app:
        app.run_service()


if __name__ == "__main__":
    main()


# pip install --upgrade build twine
# python -m build