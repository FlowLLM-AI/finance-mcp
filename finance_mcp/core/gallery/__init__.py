"""Gallery of built-in tool operations.

This subpackage exposes ready-to-use tool operations such as code execution
and shell command execution, which can be plugged into FlowLLM agents.
Only the high-level operation classes are exported in ``__all__`` so that
consumers can import them directly from :mod:`finance_mcp.core.gallery`.
"""

from .execute_code_op import ExecuteCodeOp
from .execute_shell_op import ExecuteShellOp

__all__ = [
    "ExecuteCodeOp",
    "ExecuteShellOp",
]
