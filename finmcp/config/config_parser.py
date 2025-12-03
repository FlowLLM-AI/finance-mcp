from flowllm.core.utils import PydanticConfigParser


class ConfigParser(PydanticConfigParser):
    current_file: str = __file__
