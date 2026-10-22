"""Find images in documentation files and record where their alt text lives.

The scanner is the foundation of the whole tool: it records the *exact
character span* of every alt-text region so the patcher can later replace
that region and nothing else.

Supported formats
-----------------
* Markdown / MDX  - inline ``![alt](src)``, reference ``![alt][label]`` and
  collapsed ``![alt][]`` images
* HTML            - ``<img>`` elements, including those inside ``<picture>``
* RST             - ``.. image::`` and ``.. figure::`` directives with an
  optional ``:alt:`` option

Content inside fenced code blocks, ``<pre>``/``<code>`` elements and RST
literal blocks is ignored.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, Iterator, Optional

from .classify import ImageClass, classify

DOC_EXTENSIONS = {
    ".md": "markdown",
    ".mdx": "markdown",
    ".rst": "rst",
    ".html": "html",
    ".htm": "html",
}

SKIP_DIRS = {
    ".git",
    ".hg",
    ".svn",
    "node_modules",
    ".venv",
    "venv",
    "env",
    "__pycache__",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    "dist",
    "build",
    ".next",
    "site-packages",
    ".altfix-cache",
    ".altfix",
}

# --------------------------------------------------------------------------
# Markdown
# --------------------------------------------------------------------------

#: Inline image: ``![alt](src "title")``. Nested brackets in the alt text are
#: allowed one level deep, which covers the common ``![a [b] c](x.png)``.
MD_INLINE_RE = re.compile(
    r"!\[(?P<alt>(?:[^\[\]]|\[[^\[\]]*\])*)\]"
    r"\(\s*(?P<src><[^>]*>|[^\s)]+)"
    r"(?:\s+(?P<title>\"[^\"]*\"|'[^']*'|\([^)]*\)))?\s*\)"
)

#: Full or collapsed reference image: ``![alt][label]`` / ``![alt][]``.
MD_REFERENCE_RE = re.compile(r"!\[(?P<alt>(?:[^\[\]]|\[[^\[\]]*\])*)\]\[(?P<label>[^\]]*)\]")

#: Link definition: ``[label]: src "title"``.
MD_DEFINITION_RE = re.compile(
    r"^[ \t]{0,3}\[(?P<label>[^\]^][^\]]*)\]:[ \t]*(?P<src><[^>]*>|\S+)(?:[ \t]+(?P<title>.+))?$",
    re.MULTILINE,
)

#: Fenced code block opener.
MD_FENCE_RE = re.compile(r"^(?P<indent>[ ]{0,3})(?P<fence>`{3,}|~{3,})(?P<info>.*)$", re.MULTILINE)

#: ATX heading.
MD_HEADING_RE = re.compile(r"^(?P<hashes>#{1,6})[ \t]+(?P<text>.+?)[ \t]*#*[ \t]*$", re.MULTILINE)

# --------------------------------------------------------------------------
# HTML
# --------------------------------------------------------------------------

HTML_IMG_RE = re.compile(r"<img\b(?P<attrs>[^>]*?)(?:/>|>)", re.IGNORECASE | re.DOTALL)
HTML_ALT_ATTR_RE = re.compile(
    r"\balt\s*=\s*(?:\"(?P<dq>[^\"]*)\"|'(?P<sq>[^']*)'|(?P<uq>[^\s>]+))",
    re.IGNORECASE,
)
HTML_PICTURE_RE = re.compile(r"<picture\b", re.IGNORECASE)
HTML_HEADING_RE = re.compile(
    r"<h(?P<level>[1-6])\b[^>]*>(?P<text>.*?)</h\1>", re.IGNORECASE | re.DOTALL
)
HTML_PRESKIP_RE = re.compile(
    r"<(pre|code)\b[^>]*>.*?</\1\s*>", re.IGNORECASE | re.DOTALL
)

# --------------------------------------------------------------------------
# RST
# --------------------------------------------------------------------------

RST_DIRECTIVE_RE = re.compile(
    r"^(?P<indent>[ \t]*)\.\.[ \t]+(?P<name>image|figure)::[ \t]*(?P<src>\S+)[ \t]*$",
    re.MULTILINE,
)
RST_OPTION_RE = re.compile(r"^(?P<indent>[ \t]+):(?P<name>[a-zA-Z][\w-]*):[ \t]*(?P<value>.*)$")
RST_LITERAL_RE = re.compile(
    r"^\.\.[ \t]+(?:code-block|code|literalinclude|sourcecode|parsed-literal)::.*$",
    re.MULTILINE,
)


@dataclass
class ImageOccurrence:
    """A single image found in a document.

    The ``alt_span`` / ``insert_span`` fields describe precisely where the
    alt text lives in the file so that a patch touches nothing else.

    ``fmt`` is the format of the *file* (used to pick the context rules) and
    ``syntax`` is the markup the image is written in (used to write the
    patch). They differ for raw HTML inside a Markdown file.
    """

    file_path: str
    fmt: str
    kind: str
    line_start: int
    col_start: int
    src: str
    syntax: str = ""
    alt_text: str = ""
    #: Character span of the existing alt text (may be empty for ``![]()``).
    alt_span: Optional[tuple[int, int]] = None
    #: Where to insert an alt attribute when none exists (HTML / RST).
    insert_span: Optional[tuple[int, int]] = None
    #: Template used when inserting a new alt attribute.
    insert_template: str = ""
    context_heading: Optional[str] = None
    context_before: Optional[str] = None
    context_after: Optional[str] = None
    context_link: Optional[str] = None
    context_caption: Optional[str] = None
    in_code_block: bool = False
    classification: ImageClass = field(init=False)

    def __post_init__(self) -> None:
        self.classification = classify(self.alt_text, self.src)

    @property
    def needs_fix(self) -> bool:
        return self.classification in (ImageClass.MISSING, ImageClass.LOW_QUALITY)


@dataclass
class ScanResult:
    """All images found in one file."""

    file_path: str
    fmt: str = "markdown"
    images: list[ImageOccurrence] = field(default_factory=list)

    @property
    def needs_fix(self) -> list[ImageOccurrence]:
        return [img for img in self.images if img.needs_fix]


def _line_of(text: str, offset: int) -> tuple[int, int]:
    """Return the 1-based line number and 0-based column of *offset*."""
    line = text.count("\n", 0, offset) + 1
    line_start = text.rfind("\n", 0, offset) + 1
    return line, offset - line_start


def _block_ranges(text: str) -> list[tuple[int, int]]:
    """Return character ranges that must not be scanned (code blocks)."""
    ranges: list[tuple[int, int]] = []

    # Markdown fenced code blocks.
    pos = 0
    for match in MD_FENCE_RE.finditer(text):
        if match.start() < pos:
            continue
        fence = match.group("fence")
        marker = fence[0]
        length = len(fence)
        # Find the closing fence: same character, at least as long, nothing else.
        close_re = re.compile(
            r"^[ \t]{0,3}" + re.escape(marker) + "{" + str(length) + r",}[ \t]*$",
            re.MULTILINE,
        )
        close = close_re.search(text, match.end())
        if close:
            ranges.append((match.start(), close.end()))
            pos = close.end()
        else:
            ranges.append((match.start(), len(text)))
            pos = len(text)

    # HTML pre / code elements.
    for match in HTML_PRESKIP_RE.finditer(text):
        ranges.append((match.start(), match.end()))

    # RST literal blocks: the directive plus its indented body.
    for match in RST_LITERAL_RE.finditer(text):
        start = match.start()
        end = match.end()
        base_indent = len(text[:start].split("\n")[-1]) - len(text[:start].split("\n")[-1].lstrip())
        for line in text[end:].splitlines(keepends=True):
            if not line.strip():
                end += len(line)
                continue
            indent = len(line) - len(line.lstrip())
            if indent > base_indent:
                end += len(line)
            else:
                break
        ranges.append((start, end))

    ranges.sort()
    return ranges


def _in_ranges(ranges: Iterable[tuple[int, int]], offset: int) -> bool:
    return any(start <= offset < end for start, end in ranges)


def _squeeze(text: str, limit: int = 400) -> str:
    """Collapse whitespace and trim to *limit* characters."""
    collapsed = " ".join(text.split())
    if len(collapsed) > limit:
        collapsed = collapsed[:limit].rsplit(" ", 1)[0]
    return collapsed


def _markdown_context(text: str, start: int, end: int) -> dict[str, Optional[str]]:
    """Collect heading, surrounding paragraphs and link text for Markdown."""
    heading = None
    for match in MD_HEADING_RE.finditer(text, 0, start):
        heading = match.group("text").strip()
    if heading is None:
        # Setext heading: a line of text underlined with === or ---
        for match in re.finditer(r"^(?P<t>[^\n]+)\n(?P<u>=+|-+)[ \t]*$", text[:start], re.MULTILINE):
            heading = match.group("t").strip()

    before = _squeeze(text[max(0, start - 400):start])
    before = re.sub(r"!\[[^\]]*\]\([^)]*\)", " ", before).strip()
    after = _squeeze(text[end:end + 400])
    after = re.sub(r"!\[[^\]]*\]\([^)]*\)", " ", after).strip()

    # Link text: find a `](...)` immediately following the image.
    link = None
    tail = text[end:end + 200]
    link_match = re.match(r"\]\((?P<url>[^)]*)\)", tail)
    if link_match:
        link = link_match.group("url")

    # Caption: the first emphasised run on the next non-empty line.
    caption = None
    rest = text[end:]
    for line in rest.split("\n", 2)[1:2]:
        stripped = line.strip()
        emph = re.match(r"^(?:_\*|_|\*)\s*(?P<text>.+?)\s*(?:_\*|_|\*)$", stripped)
        if emph:
            caption = emph.group("text").strip()
        elif stripped.startswith("*") and stripped.endswith("*") and len(stripped) > 2:
            caption = stripped.strip("*").strip()
        break

    return {
        "context_heading": heading,
        "context_before": before or None,
        "context_after": after or None,
        "context_link": link,
        "context_caption": caption,
    }


def _html_context(text: str, start: int, end: int) -> dict[str, Optional[str]]:
    heading = None
    for match in HTML_HEADING_RE.finditer(text, 0, start):
        heading = _squeeze(re.sub(r"<[^>]+>", " ", match.group("text")), 200)
    before = _squeeze(re.sub(r"<[^>]+>", " ", text[max(0, start - 400):start]))
    after = _squeeze(re.sub(r"<[^>]+>", " ", text[end:end + 400]))
    return {
        "context_heading": heading,
        "context_before": before or None,
        "context_after": after or None,
        "context_link": None,
        "context_caption": None,
    }


def _rst_context(text: str, start: int, end: int) -> dict[str, Optional[str]]:
    heading = None
    for match in re.finditer(r"^(?P<t>[^\n]+)\n(?P<u>[=\-~^\"'`#*+]{2,})[ \t]*$", text[:start], re.MULTILINE):
        heading = match.group("t").strip()
    before = _squeeze(text[max(0, start - 400):start])
    after = _squeeze(text[end:end + 400])
    return {
        "context_heading": heading,
        "context_before": before or None,
        "context_after": after or None,
        "context_link": None,
        "context_caption": None,
    }


def scan_markdown(text: str, file_path: str, ranges: list[tuple[int, int]]) -> list[ImageOccurrence]:
    """Scan Markdown / MDX text for images."""
    found: list[ImageOccurrence] = []
    definitions: dict[str, str] = {}
    for match in MD_DEFINITION_RE.finditer(text):
        definitions[match.group("label").strip().lower()] = match.group("src").strip()

    for match in MD_INLINE_RE.finditer(text):
        if _in_ranges(ranges, match.start()):
            continue
        alt = match.group("alt")
        src = match.group("src").strip()
        if src.startswith("<") and src.endswith(">"):
            src = src[1:-1]
        line, col = _line_of(text, match.start())
        occurrence = ImageOccurrence(
            file_path=file_path,
            fmt="markdown",
            kind="inline",
            line_start=line,
            col_start=col,
            src=src,
            syntax="markdown",
            alt_text=alt,
            alt_span=(match.start("alt"), match.end("alt")),
        )
        occurrence.__dict__.update(_markdown_context(text, match.start(), match.end()))
        found.append(occurrence)

    for match in MD_REFERENCE_RE.finditer(text):
        if _in_ranges(ranges, match.start()):
            continue
        # Skip references that are actually inline images (already handled).
        if MD_INLINE_RE.match(text, match.start()):
            continue
        alt = match.group("alt")
        label = match.group("label").strip()
        if not label:
            # Collapsed reference: the alt text itself is the label.
            label = alt.strip()
        src = definitions.get(label.lower(), "")
        line, col = _line_of(text, match.start())
        occurrence = ImageOccurrence(
            file_path=file_path,
            fmt="markdown",
            kind="reference",
            line_start=line,
            col_start=col,
            src=src,
            syntax="markdown",
            alt_text=alt,
            alt_span=(match.start("alt"), match.end("alt")),
        )
        occurrence.__dict__.update(_markdown_context(text, match.start(), match.end()))
        found.append(occurrence)

    # Markdown files may embed raw HTML, which is common in READMEs and
    # always used in MDX. Pick those images up as well.
    for occurrence in scan_html(text, file_path, ranges, fmt="markdown"):
        found.append(occurrence)

    return found


def scan_html(
    text: str,
    file_path: str,
    ranges: list[tuple[int, int]],
    fmt: str = "html",
) -> list[ImageOccurrence]:
    """Scan text for ``<img>`` elements."""
    found: list[ImageOccurrence] = []
    for match in HTML_IMG_RE.finditer(text):
        if _in_ranges(ranges, match.start()):
            continue
        attrs = match.group("attrs") or ""
        alt_match = HTML_ALT_ATTR_RE.search(attrs)
        src_match = re.search(r"\bsrc\s*=\s*(?:\"(?P<dq>[^\"]*)\"|'(?P<sq>[^']*)'|(?P<uq>[^\s>]+))", attrs, re.IGNORECASE)
        src = ""
        if src_match:
            src = src_match.group("dq") or src_match.group("sq") or src_match.group("uq") or ""

        line, col = _line_of(text, match.start())
        alt_text = ""
        alt_span = None
        insert_span = None
        insert_template = ""
        if alt_match:
            # Offsets inside `attrs` are relative to the attrs group, so shift
            # them into document coordinates.
            attrs_offset = match.start("attrs")
            group = "dq" if alt_match.group("dq") is not None else "sq"
            if alt_match.group(group) is not None:
                value = alt_match.group(group)
                alt_text = value
                start = attrs_offset + alt_match.start(group)
                alt_span = (start, start + len(value))
            else:
                value = alt_match.group("uq") or ""
                alt_text = value
                start = attrs_offset + alt_match.start("uq")
                alt_span = (start, start + len(value))
        else:
            # No alt attribute: insert one after the src attribute when there
            # is one (that is where authors conventionally put it), otherwise
            # directly after the tag name.
            insert_at = match.start() + len("<img")
            if src_match is not None:
                insert_at = match.start("attrs") + src_match.end()
            insert_span = (insert_at, insert_at)
            insert_template = ' alt="{}"'

        occurrence = ImageOccurrence(
            file_path=file_path,
            fmt=fmt,
            kind="img",
            line_start=line,
            col_start=col,
            src=src,
            syntax="html",
            alt_text=alt_text,
            alt_span=alt_span,
            insert_span=insert_span,
            insert_template=insert_template,
        )
        if fmt == "html":
            occurrence.__dict__.update(_html_context(text, match.start(), match.end()))
        else:
            occurrence.__dict__.update(_markdown_context(text, match.start(), match.end()))
        found.append(occurrence)

    return found


def scan_rst(text: str, file_path: str, ranges: list[tuple[int, int]]) -> list[ImageOccurrence]:
    """Scan RST text for ``.. image::`` and ``.. figure::`` directives."""
    found: list[ImageOccurrence] = []
    for match in RST_DIRECTIVE_RE.finditer(text):
        if _in_ranges(ranges, match.start()):
            continue
        src = match.group("src")
        base_indent = match.group("indent")

        # Find the option block belonging to this directive.
        body_start = match.end()
        alt_option = None
        cursor = body_start
        for line in text[body_start:].splitlines(keepends=True):
            if not line.strip():
                cursor += len(line)
                continue
            indent = len(line) - len(line.lstrip())
            if indent <= len(base_indent):
                break
            option = RST_OPTION_RE.match(line.rstrip("\n"))
            if option and option.group("name").lower() == "alt" and alt_option is None:
                # The match was made against the line alone, so shift the
                # value offset into document coordinates.
                alt_option = (option, cursor)
            cursor += len(line)

        line, col = _line_of(text, match.start())
        alt_text = ""
        alt_span = None
        insert_span = None
        insert_template = ""
        if alt_option is not None:
            option, option_offset = alt_option
            value = option.group("value")
            alt_text = value
            value_start = option_offset + option.start("value")
            alt_span = (value_start, value_start + len(value))
        else:
            # Insert a new ":alt:" option line directly after the directive.
            line_end = text.find("\n", body_start)
            if line_end == -1:
                line_end = len(text)
            else:
                line_end += 1
            insert_span = (line_end, line_end)
            insert_template = f"{base_indent}   :alt: {{}}\n"

        occurrence = ImageOccurrence(
            file_path=file_path,
            fmt="rst",
            kind=match.group("name"),
            line_start=line,
            col_start=col,
            src=src,
            syntax="rst",
            alt_text=alt_text,
            alt_span=alt_span,
            insert_span=insert_span,
            insert_template=insert_template,
        )
        occurrence.__dict__.update(_rst_context(text, match.start(), match.end()))
        found.append(occurrence)

    return found


def scan_text(text: str, file_path: str = "<memory>", fmt: str = "markdown") -> ScanResult:
    """Scan a string and return the images it contains."""
    ranges = _block_ranges(text)
    if fmt == "html":
        images = scan_html(text, file_path, ranges)
    elif fmt == "rst":
        images = scan_rst(text, file_path, ranges)
    else:
        images = scan_markdown(text, file_path, ranges)
    images.sort(key=lambda img: (img.line_start, img.col_start))
    return ScanResult(file_path=file_path, fmt=fmt, images=images)


def iter_doc_files(root: str | Path) -> Iterator[Path]:
    """Yield documentation files under *root* in a stable order."""
    root_path = Path(root)
    if root_path.is_file():
        if root_path.suffix.lower() in DOC_EXTENSIONS:
            yield root_path
        return
    for dirpath, dirnames, filenames in os_walk(root_path):
        dirnames[:] = sorted(d for d in dirnames if d not in SKIP_DIRS and not d.startswith(".git"))
        for name in sorted(filenames):
            path = Path(dirpath) / name
            if path.suffix.lower() in DOC_EXTENSIONS:
                yield path


def os_walk(root: Path):
    """Small wrapper so the walk can be patched in tests."""
    import os

    return os.walk(root)


def scan_file(path: str | Path) -> ScanResult:
    """Scan one documentation file."""
    path = Path(path)
    fmt = DOC_EXTENSIONS.get(path.suffix.lower(), "markdown")
    raw = path.read_bytes()
    # Preserve CRLF: decode as utf-8 and keep the newlines exactly as they are.
    text = raw.decode("utf-8", errors="replace")
    result = scan_text(text, str(path), fmt)
    result.file_path = str(path)
    return result


def scan_path(root: str | Path) -> list[ScanResult]:
    """Scan a file or directory tree and return one result per file."""
    results: list[ScanResult] = []
    for path in iter_doc_files(root):
        try:
            results.append(scan_file(path))
        except OSError:
            continue
    return results


def summarize(results: list[ScanResult]) -> dict[str, int]:
    """Count images per classification across *results*."""
    counts = {cls.value: 0 for cls in ImageClass}
    for result in results:
        for image in result.images:
            counts[image.classification.value] += 1
    return counts
