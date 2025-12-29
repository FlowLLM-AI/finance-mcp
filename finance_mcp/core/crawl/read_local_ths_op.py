import json
from pathlib import Path
from typing import Dict

from flowllm.core.context import C
from flowllm.core.op import BaseAsyncOp
from loguru import logger


@C.register_op()
class ReadLocalThsOp(BaseAsyncOp):
    # Class-level cache: {tag: {code: tool_result}}
    _cache: Dict[str, Dict[str, str]] = None

    def __init__(self, tag: str = "", **kwargs):
        super().__init__(**kwargs)
        self.tag: str = tag
        # Initialize class-level cache if not exists
        if ReadLocalThsOp._cache is None:
            ReadLocalThsOp._cache = {}

    def _load_cache(self) -> Dict[str, str]:
        """Load all crawl_ths_{tag}*.json files and build code->tool_result mapping."""
        tool_cache_dir = Path("tool_cache")
        pattern = f"crawl_ths_{self.tag}*.json"
        matching_files = list(tool_cache_dir.glob(pattern))

        total_files = len(matching_files)
        logger.info(f"Found {total_files} files matching pattern '{pattern}'")

        result_dict = {}
        for idx, file_path in enumerate(matching_files, 1):
            logger.info(f"Loading file [{idx}/{total_files}]: {file_path.name}")
            
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            file_records = 0
            for item in data:
                code = item['tool_args']['code']
                result_dict[code] = item['tool_result']
                file_records += 1
            
            logger.info(f"  → Processed {file_records} records from {file_path.name}")

        logger.info(f"✓ Successfully loaded {len(result_dict)} total records for tag={self.tag}")
        return result_dict

    async def async_execute(self):
        """Read tool_result for self.context.code from cached data."""
        # Load cache if not exists
        if self.tag not in ReadLocalThsOp._cache:
            ReadLocalThsOp._cache[self.tag] = self._load_cache()

        # Get code from context
        code = self.context.code
        if not code:
            self.context.response.answer = f"No code={code} found in context."
            logger.info(self.context.response.answer)
            return

        # Get tool_result from cache
        tool_result = ReadLocalThsOp._cache[self.tag].get(code)
        self.context.response.answer = tool_result
