"""Rule-based classification of documentation images.

The classifier never calls a model. It decides, from the alt text and the
image source alone, whether an image needs work:

``MISSING``      no alt text at all, or an empty alt attribute
``LOW_QUALITY``  alt text exists but says nothing useful
``OK``           alt text is descriptive
``DECORATIVE``   badge / spacer / tracking pixel that should not be described
"""

from __future__ import annotations

import re
from enum import Enum
from typing import Optional


class ImageClass(str, Enum):
    """Classification of a single image. Subclasses ``str`` for easy output."""

    MISSING = "missing"
    LOW_QUALITY = "low_quality"
    OK = "ok"
    DECORATIVE = "decorative"

    def __str__(self) -> str:  # pragma: no cover - cosmetic
        return self.value


# Alt text that is technically present but says nothing.
GENERIC_ALT_TEXTS = {
    "image",
    "img",
    "picture",
    "photo",
    "photograph",
    "screenshot",
    "screen shot",
    "screen-shot",
    "graphic",
    "diagram",
    "graph",
    "chart",
    "logo",
    "icon",
    "banner",
    "thumbnail",
    "untitled",
    "placeholder",
    "blank",
    "spacer",
    "example",
    "here",
    "this",
    "link",
    "click here",
    "download",
    "view",
    "header",
    "footer",
    "no alt",
    "none",
    "n/a",
    "file",
    "image1",
    "image2",
    "img1",
    "img2",
    "picture1",
    "picture2",
    "screen shot1",
}

# Phrases that indicate the alt text is a file reference rather than a description.
_FILENAME_RE = re.compile(r"^[\w\-. ]+\.(png|jpe?g|gif|svg|webp|bmp|tiff?|avif)$", re.IGNORECASE)
_HASH_RE = re.compile(r"^[0-9a-f]{16,}$", re.IGNORECASE)
_ONLY_PUNCT_RE = re.compile(r"^[\W_]+$", re.UNICODE)

# Sources that are known to be badges / status pills.
_BADGE_HOSTS = (
    "shields.io",
    "img.shields.io",
    "badge.fury.io",
    "badgen.net",
    "codecov.io",
    "coveralls.io",
    "travis-ci.com",
    "circleci.com",
    "appveyor.com",
    "flat.badgen",
    "opencollective.com",
    "img.shields.io",
    "herokucdn.com",
    "nodei.co",
)
_BADGE_PATH_RE = re.compile(r"(/badge/|/badge\?|\bbadge\b|status\.svg|/build\.svg|/coverage\.svg)", re.IGNORECASE)

# Sources that are spacers / tracking pixels / separators.
_DECORATIVE_NAMES = {
    "spacer",
    "spacer.gif",
    "spacer.png",
    "spacer.svg",
    "blank",
    "blank.gif",
    "blank.png",
    "transparent",
    "transparent.gif",
    "transparent.png",
    "pixel",
    "pixel.gif",
    "pixel.png",
    "1x1",
    "1x1.gif",
    "1x1.png",
    "clear.gif",
    "divider",
    "divider.png",
    "separator.png",
    "horizontal-rule.png",
}
_SPACER_RE = re.compile(r"(^|[/_.-])(spacer|pixel|blank|transparent|divider|separator)([/_.-]|$)", re.IGNORECASE)


def _basename(src: str) -> str:
    """Return the last path segment of *src* without a query string."""
    if not src:
        return ""
    cleaned = src.split("?")[0].split("#")[0].rstrip("/")
    return cleaned.split("/")[-1].lower()


def _stem(src: str) -> str:
    """Return the last path segment of *src* without extension."""
    name = _basename(src)
    if "." in name:
        name = name.rsplit(".", 1)[0]
    return name


def is_badge(src: str) -> bool:
    """True when *src* points at a CI badge / status pill."""
    if not src:
        return False
    lowered = src.lower()
    if any(host in lowered for host in _BADGE_HOSTS):
        return True
    if lowered.startswith("data:image/svg"):
        return True
    return bool(_BADGE_PATH_RE.search(lowered))


def is_decorative(src: str) -> bool:
    """True when *src* points at a badge, spacer, separator or tracking pixel."""
    if is_badge(src):
        return True
    name = _basename(src)
    if name in _DECORATIVE_NAMES:
        return True
    if _SPACER_RE.search(name):
        return True
    # A bare "spacer" style name without extension.
    stem = _stem(src)
    if stem in {"spacer", "pixel", "blank", "transparent", "divider", "separator"}:
        return True
    return False


def is_filename_echo(alt: str, src: str) -> bool:
    """True when the alt text is just the file name of the image."""
    if not alt or not src:
        return False
    alt_norm = alt.strip().lower()
    if not alt_norm:
        return False
    base = _basename(src)
    stem = _stem(src)
    if alt_norm in {base, stem}:
        return True
    # "chart.png" style names that merely repeat the file.
    if _FILENAME_RE.match(alt_norm) and alt_norm == base:
        return True
    return False


def is_generic(alt: str) -> bool:
    """True when the alt text carries no information."""
    if alt is None:
        return True
    norm = " ".join(alt.strip().lower().split())
    if not norm:
        return True
    if norm in GENERIC_ALT_TEXTS:
        return True
    if _ONLY_PUNCT_RE.match(norm):
        return True
    if _HASH_RE.match(norm):
        return True
    if _FILENAME_RE.match(norm):
        return True
    if len(norm) < 3:
        return True
    # "image1", "screenshot 2", "photo (1)" and friends.
    if re.match(r"^(image|img|picture|photo|screenshot|graph|chart|diagram|logo|icon)\s*[-_#]?\s*\d{0,3}$", norm):
        return True
    return False


def classify(alt: Optional[str], src: str = "") -> ImageClass:
    """Classify an image from its alt text and source.

    Args:
        alt: The alt text currently in the document (``None`` when absent).
        src: The image source path or URL.

    Returns:
        One of the :class:`ImageClass` values.
    """
    if is_decorative(src):
        return ImageClass.DECORATIVE
    if alt is None or not alt.strip():
        return ImageClass.MISSING
    if is_generic(alt) or is_filename_echo(alt, src):
        return ImageClass.LOW_QUALITY
    return ImageClass.OK


# Backwards compatible aliases used by earlier revisions of the project.
classify_image = classify
