"""Debug utilities for the AIMUD project."""

import os
import sys
from typing import Any

# Check if debug mode is enabled from environment or command line
DEBUG = os.getenv("DEBUG", "").lower() in ("1", "true", "yes") or "--debug" in sys.argv

def debug_print(*args: Any, **kwargs: Any) -> None:
    """Print debug information if debug mode is enabled.
    
    Args:
        *args: Positional arguments to pass to print
        **kwargs: Keyword arguments to pass to print
    """
    if DEBUG:
        print("[DEBUG]", *args, **kwargs)