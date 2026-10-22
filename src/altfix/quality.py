"""Quality checks for generated alt text.

No second model is used as a judge. Everything here is deterministic:

* strip ``<think>`` blocks, quotes and markdown decoration
* strip filler prefixes such as "Image of" / "This screenshot shows"
* enforce a hard character budget (default 125)
* reject descriptions that merely echo the file name
* reject descriptions that are still generic after cleaning
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional

from .classify import is_filename_echo, is_generic

MAX_ALT_LENGTH = 125

#: Text used when a description could not be produced.
NEEDS_REVIEW = "[needs review]"

_THINK_RE = re.compile(r"<think>.*?</think>", re.DOTALL | re.IGNORECASE)
_THINK_OPEN_RE = re.compile(r"<think>.*\Z", re.DOTALL | re.IGNORECASE)
_CODE_FENCE_RE = re.compile(r"^```[a-zA-Z0-9_+-]*\s*|\s*```$", re.MULTILINE)
_QUOTE_RE = re.compile(r"^[\"'“‘`«]+|[\"'”’`»]+$")
_MD_LINK_RE = re.compile(r"\[([^\]]*)\]\([^)]*\)")
_MD_EMPHASIS_RE = re.compile(r"(\*{1,3}|_{1,3})(.+?)\1", re.DOTALL)
_BULLET_RE = re.compile(r"^\s*[-*+]\s+")
_NUMBERING_RE = re.compile(r"^\s*\d+[.)]\s+")
_LABEL_RE = re.compile(r"^\s*(alt|alt text|description|caption)\s*[:\-]\s*", re.IGNORECASE)

#: Filler prefixes that carry no information and must be removed. Only
#: synonyms for the image itself belong here - "a chart of" is real content
#: and must survive.
FILLER_PREFIXES = (
    "this image shows",
    "this image is",
    "this image depicts",
    "this picture shows",
    "this picture is",
    "this screenshot shows",
    "this screenshot is",
    "this screenshot of",
    "this photo shows",
    "this photo is",
    "the image shows",
    "the image is",
    "the picture shows",
    "the picture is",
    "the screenshot shows",
    "the screenshot is",
    "an image of",
    "a image of",
    "a picture of",
    "a photo of",
    "a screenshot of",
    "image of",
    "picture of",
    "photo of",
    "screenshot of",
    "image showing",
    "picture showing",
    "photo showing",
    "screenshot showing",
    "illustration of",
    "an illustration of",
    "graphic of",
    "a graphic of",
    "rendering of",
    "a rendering of",
    "picture:",
    "image:",
    "photo:",
    "screenshot:",
)

#: Words that on their own make a description useless.
_USELESS_ONLY = {
    "an image",
    "a image",
    "the image",
    "a picture",
    "the picture",
    "a photo",
    "the photo",
    "a screenshot",
    "the screenshot",
    "a diagram",
    "the diagram",
    "a chart",
    "the chart",
    "a graph",
    "the graph",
    "an illustration",
    "a graphic",
    "image",
    "picture",
    "photo",
    "screenshot",
    "diagram",
    "chart",
    "graph",
    "logo",
    "icon",
    "alt text",
    "alt",
    "none",
    "n/a",
    "unknown",
    "todo",
}


@dataclass
class QualityResult:
    """Outcome of running the quality checks on one candidate description."""

    text: str
    ok: bool
    reason: str = ""

    def __bool__(self) -> bool:  # pragma: no cover - convenience
        return self.ok


def strip_think(text: str) -> str:
    """Remove ``<think>...</think>`` reasoning blocks emitted by the model."""
    if not text:
        return ""
    cleaned = _THINK_RE.sub(" ", text)
    cleaned = _THINK_OPEN_RE.sub(" ", cleaned)
    return cleaned.strip()


def _strip_markdown(text: str) -> str:
    """Remove markdown decoration the model may have wrapped the answer in."""
    cleaned = text.strip()
    cleaned = _CODE_FENCE_RE.sub(" ", cleaned)
    cleaned = _MD_LINK_RE.sub(r"\1", cleaned)
    cleaned = _MD_EMPHASIS_RE.sub(r"\2", cleaned)
    cleaned = _BULLET_RE.sub("", cleaned)
    cleaned = _NUMBERING_RE.sub("", cleaned)
    cleaned = _LABEL_RE.sub("", cleaned)
    return cleaned


def _strip_filler(text: str) -> str:
    """Remove leading filler phrases such as "Image of"."""
    current = text.strip()
    changed = True
    while changed:
        changed = False
        lowered = current.lower()
        for prefix in FILLER_PREFIXES:
            if lowered.startswith(prefix):
                current = current[len(prefix):].strip()
                changed = True
                break
        # Strip repeated leading articles after removing a filler phrase.
        for article in ("a ", "an ", "the "):
            if current.lower().startswith(article) and len(current) > len(article) + 3:
                candidate = current[len(article):]
                if candidate[:1].isupper() and not candidate.startswith("An "):
                    current = candidate
                    changed = True
                    break
    return current


def truncate(text: str, max_length: int) -> str:
    """Truncate *text* to at most *max_length* characters on a word boundary."""
    if len(text) <= max_length:
        return text
    clipped = text[:max_length].rstrip()
    if " " in clipped:
        clipped = clipped[: clipped.rfind(" ")].rstrip()
    if not clipped:
        clipped = text[:max_length].rstrip()
    return clipped


def clean(raw: str, max_length: int = MAX_ALT_LENGTH) -> str:
    """Normalise raw model output into a candidate alt text."""
    if not raw:
        return ""
    text = strip_think(raw)
    text = _strip_markdown(text)
    text = _QUOTE_RE.sub("", text)
    text = _strip_filler(text)
    text = " ".join(text.split())
    text = text.strip().strip(".,;:").strip()
    return text


def check(raw: str, src: str = "", max_length: int = MAX_ALT_LENGTH) -> QualityResult:
    """Run every quality rule on *raw* and report the outcome.

    Args:
        raw: Raw model output.
        src: The image source, used to detect file-name echoes.
        max_length: Maximum number of characters allowed.

    Returns:
        A :class:`QualityResult` with the cleaned text and a failure reason.
    """
    text = clean(raw, max_length)

    if not text:
        return QualityResult(text="", ok=False, reason="empty")

    # Length is enforced first so that a long-but-useful description is
    # truncated rather than thrown away.
    truncated = False
    if len(text) > max_length:
        text = truncate(text, max_length)
        truncated = True
        if len(text) < 10:
            return QualityResult(text=text, ok=False, reason="too_short_after_truncation")

    if is_filename_echo(text, src):
        return QualityResult(text=text, ok=False, reason="filename_echo")
    if text.lower() in _USELESS_ONLY:
        return QualityResult(text=text, ok=False, reason="generic")
    if is_generic(text):
        return QualityResult(text=text, ok=False, reason="generic")
    if truncated:
        return QualityResult(text=text, ok=True, reason="truncated")
    return QualityResult(text=text, ok=True, reason="")


def validate(raw: str, src: str = "", max_length: int = MAX_ALT_LENGTH) -> tuple[str, bool]:
    """Backwards compatible helper returning ``(text, ok)``."""
    result = check(raw, src, max_length)
    return result.text, result.ok
