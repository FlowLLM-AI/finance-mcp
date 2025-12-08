"""Datetime helper utilities for finance-mcp.

This module currently exposes a single helper, :func:`get_datetime`, which
returns the current time formatted as a string.
"""

from datetime import datetime


def get_datetime(time_ft: str = "%Y-%m-%d %H:%M:%S") -> str:
    """Return the current datetime formatted as a string.

    Args:
        time_ft: Format string compatible with :meth:`datetime.strftime`.

    Returns:
        The current local datetime formatted according to ``time_ft``.
    """

    now = datetime.now()
    formatted_time = now.strftime(time_ft)
    return formatted_time
