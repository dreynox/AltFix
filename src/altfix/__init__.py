"""AltFix: generate alt text for documentation images with a local vision model.

Everything runs locally: the model is served by an OpenAI-compatible server
(LM Studio by default) on your own machine, and no repository content ever
leaves it.
"""

from .config import Config, load_config
from .classify import ImageClass, classify
from .quality import MAX_ALT_LENGTH, NEEDS_REVIEW, check
from .scan import ImageOccurrence, ScanResult, scan_file, scan_path, scan_text

__version__ = "0.2.0"

__all__ = [
    "Config",
    "ImageClass",
    "ImageOccurrence",
    "MAX_ALT_LENGTH",
    "NEEDS_REVIEW",
    "ScanResult",
    "__version__",
    "check",
    "classify",
    "load_config",
    "scan_file",
    "scan_path",
    "scan_text",
]
