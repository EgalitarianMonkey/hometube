"""
DEPRECATED: Utility functions - Please use dedicated *_utils modules instead.

This module is maintained for backward compatibility only.
New code should import from the following modules:

- file_system_utils: sanitize_filename, is_valid_cookie_file, is_valid_browser
- display_utils: fmt_hhmmss, parse_time_like
- medias_utils: sanitize_url, video_id_from_url
- cut_utils: invert_segments, invert_segments_tuples

This file will be removed in a future version.
"""

import warnings

# Re-export functions from their new locations for backward compatibility
from .file_system_utils import (
    sanitize_filename,
    is_valid_cookie_file,
    is_valid_browser,
)
from .display_utils import (
    fmt_hhmmss,
    parse_time_like,
)
from .medias_utils import (
    sanitize_url,
    video_id_from_url,
)
from .cut_utils import invert_segments, invert_segments_tuples


def __getattr__(name):
    """Warn users about deprecated imports."""
    warnings.warn(
        f"Importing '{name}' from utils.py is deprecated. "
        f"Please import from the appropriate *_utils module instead.",
        DeprecationWarning,
        stacklevel=2,
    )
    # Try to return the attribute from globals
    if name in globals():
        return globals()[name]
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")
