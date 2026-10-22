"""Apply alt text changes by exact character span.

Every edit is a ``(start, end, replacement)`` triple over the *original* file
text. Applying a set of edits therefore cannot touch a single byte outside
the recorded spans, which is what makes the diffs reviewable.
"""

from __future__ import annotations

import difflib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, Optional

from .scan import ImageOccurrence


def escape_markdown_alt(text: str) -> str:
    """Escape characters that would break out of a Markdown ``![...]`` span."""
    return text.replace("\\", "\\\\").replace("[", "\\[").replace("]", "\\]")


def escape_html_attr(text: str) -> str:
    """Escape a value that will be placed inside a double-quoted HTML attribute."""
    return (
        text.replace("&", "&amp;")
        .replace('"', "&quot;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def escape_rst_alt(text: str) -> str:
    """Normalise a value for an RST ``:alt:`` option."""
    return " ".join(text.split())


@dataclass
class AltEdit:
    """One replacement of an alt text region."""

    file_path: str
    start: int
    end: int
    replacement: str
    #: Human readable description, used in reports.
    label: str = ""

    def apply_to(self, text: str) -> str:
        return text[: self.start] + self.replacement + text[self.end :]


@dataclass
class FilePatch:
    """All edits for a single file, plus the resulting unified diff."""

    file_path: str
    original: str
    updated: str
    edits: list[AltEdit] = field(default_factory=list)

    @property
    def changed(self) -> bool:
        return self.original != self.updated

    def diff(self, from_file: str | None = None, to_file: str | None = None) -> str:
        """Return a unified diff of the change."""
        source = from_file or f"a/{self._relpath()}"
        target = to_file or f"b/{self._relpath()}"
        lines = difflib.unified_diff(
            self.original.splitlines(keepends=True),
            self.updated.splitlines(keepends=True),
            fromfile=source,
            tofile=target,
            n=3,
        )
        return "".join(lines)

    def _relpath(self) -> str:
        return str(self.file_path).replace("\\", "/")


def plan_edit(occurrence: ImageOccurrence, new_alt: str) -> Optional[AltEdit]:
    """Return the edit that sets *occurrence* to *new_alt*, or ``None``.

    ``None`` means the alt text is already correct and nothing has to change.
    """
    if occurrence.alt_span is not None:
        start, end = occurrence.alt_span
        if occurrence.fmt == "markdown":
            replacement = escape_markdown_alt(new_alt)
        elif occurrence.fmt == "html":
            replacement = escape_html_attr(new_alt)
        else:
            replacement = escape_rst_alt(new_alt)
        if start == end and not replacement:
            return None
        if occurrence.alt_text == replacement:
            return None
        return AltEdit(
            file_path=occurrence.file_path,
            start=start,
            end=end,
            replacement=replacement,
            label=occurrence.src,
        )

    if occurrence.insert_span is not None:
        start, end = occurrence.insert_span
        if occurrence.fmt == "html":
            replacement = occurrence.insert_template.format(escape_html_attr(new_alt))
        elif occurrence.fmt == "rst":
            replacement = occurrence.insert_template.format(escape_rst_alt(new_alt))
        else:
            replacement = occurrence.insert_template.format(escape_markdown_alt(new_alt))
        return AltEdit(
            file_path=occurrence.file_path,
            start=start,
            end=end,
            replacement=replacement,
            label=occurrence.src,
        )

    return None


def apply_edits(text: str, edits: Iterable[AltEdit]) -> str:
    """Apply *edits* to *text*.

    Edits are applied from the end of the file backwards so earlier offsets
    stay valid.
    """
    ordered = sorted(edits, key=lambda edit: (edit.start, edit.end), reverse=True)
    result = text
    for edit in ordered:
        result = result[: edit.start] + edit.replacement + result[edit.end :]
    return result


def build_patch(
    file_path: str | Path,
    original: str,
    edits: list[AltEdit],
) -> FilePatch:
    """Build a :class:`FilePatch` for *edits* against *original*."""
    updated = apply_edits(original, edits)
    return FilePatch(
        file_path=str(file_path),
        original=original,
        updated=updated,
        edits=list(edits),
    )


def patch_file(
    file_path: str | Path,
    edits: list[AltEdit],
    apply: bool = False,
) -> FilePatch:
    """Build a patch for *file_path* and optionally write it to disk.

    The file is read and written as bytes so that line endings and encoding
    outside the edited spans are preserved exactly.
    """
    path = Path(file_path)
    raw = path.read_bytes()
    text = raw.decode("utf-8")
    patch = build_patch(path, text, edits)
    if apply and patch.changed:
        path.write_bytes(patch.updated.encode("utf-8"))
    return patch


def outside_spans_unchanged(original: str, updated: str, edits: list[AltEdit]) -> bool:
    """Verify that only the edited spans differ between two texts."""
    expected = apply_edits(original, edits)
    return expected == updated


def diff_only_alt_text(original: str, updated: str) -> bool:
    """Heuristic check that a diff only touches alt text.

    Used by the evaluation suite: the changed lines must differ only inside
    an alt attribute, a Markdown image span or an RST ``:alt:`` option.
    """
    original_lines = original.splitlines()
    updated_lines = updated.splitlines()
    if len(original_lines) != len(updated_lines):
        return False
    for old, new in zip(original_lines, updated_lines):
        if old == new:
            continue
        if _line_is_alt_only(old, new):
            continue
        return False
    return True


def _line_is_alt_only(old: str, new: str) -> bool:
    """True when two lines differ only in their alt text."""
    if old.replace(" ", "") == new.replace(" ", ""):
        return True
    # Markdown: ![old](src) -> ![new](src)
    stripped_old = _strip_md_alt(old)
    stripped_new = _strip_md_alt(new)
    if stripped_old == stripped_new:
        return True
    # HTML: alt="old" -> alt="new"
    stripped_old = _strip_html_alt(old)
    stripped_new = _strip_html_alt(new)
    if stripped_old == stripped_new:
        return True
    # RST: :alt: old -> :alt: new
    stripped_old = _strip_rst_alt(old)
    stripped_new = _strip_rst_alt(new)
    return stripped_old == stripped_new


def _strip_md_alt(line: str) -> str:
    import re

    return re.sub(r"!\[([^\]]*)\]", "![ALT]", line)


def _strip_html_alt(line: str) -> str:
    import re

    return re.sub(r'\balt\s*=\s*"[^"]*"', 'alt="ALT"', line)


def _strip_rst_alt(line: str) -> str:
    import re

    return re.sub(r"(:alt:)[ \t]*.*$", r"\1 ALT", line)
