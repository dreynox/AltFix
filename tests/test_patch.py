"""Tests for the patcher: exact spans, idempotency, byte preservation."""

from __future__ import annotations

from pathlib import Path

import pytest

from altfix.patch import (
    apply_edits,
    build_patch,
    diff_only_alt_text,
    escape_html_attr,
    escape_markdown_alt,
    outside_spans_unchanged,
    patch_file,
    plan_edit,
)
from altfix.scan import scan_text


def occurrence_for(text: str, fmt: str = "markdown", index: int = 0):
    return scan_text(text, "doc.md", fmt).images[index]


class TestMarkdownPatch:
    def test_replaces_only_alt_text(self):
        text = "Before ![old alt](img.png) after."
        occ = occurrence_for(text)
        edit = plan_edit(occ, "new alt")
        updated = apply_edits(text, [edit])
        assert updated == "Before ![new alt](img.png) after."

    def test_fills_empty_alt(self):
        text = "Before ![](img.png) after."
        occ = occurrence_for(text)
        edit = plan_edit(occ, "new alt")
        updated = apply_edits(text, [edit])
        assert updated == "Before ![new alt](img.png) after."

    def test_multiple_images_on_one_line(self):
        text = "![a](a.png) and ![b](b.png)"
        images = scan_text(text, "d.md", "markdown").images
        edits = [plan_edit(images[0], "first"), plan_edit(images[1], "second")]
        updated = apply_edits(text, edits)
        assert updated == "![first](a.png) and ![second](b.png)"

    def test_nested_link_preserved(self):
        text = "[![old](img.png)](https://example.com/page)"
        occ = occurrence_for(text)
        updated = apply_edits(text, [plan_edit(occ, "new")])
        assert updated == "[![new](img.png)](https://example.com/page)"

    def test_brackets_are_escaped(self):
        text = "![old](img.png)"
        occ = occurrence_for(text)
        updated = apply_edits(text, [plan_edit(occ, "a [b] c")])
        assert updated == "![a \\[b\\] c](img.png)"

    def test_surrounding_text_untouched(self):
        text = "Line one\n\n# Heading\n\n![old](img.png)\n\nTrailing text.\n"
        occ = occurrence_for(text)
        updated = apply_edits(text, [plan_edit(occ, "new")])
        assert updated == "Line one\n\n# Heading\n\n![new](img.png)\n\nTrailing text.\n"


class TestHtmlPatch:
    def test_replaces_alt_attribute(self):
        text = '<img src="a.png" alt="old">'
        occ = occurrence_for(text, "html")
        updated = apply_edits(text, [plan_edit(occ, "new")])
        assert updated == '<img src="a.png" alt="new">'

    def test_inserts_missing_alt_attribute(self):
        text = '<img src="a.png" class="hero">'
        occ = occurrence_for(text, "html")
        updated = apply_edits(text, [plan_edit(occ, "new")])
        assert updated == '<img src="a.png" alt="new" class="hero">'

    def test_quotes_are_escaped(self):
        text = '<img src="a.png" alt="old">'
        occ = occurrence_for(text, "html")
        updated = apply_edits(text, [plan_edit(occ, 'He said "hi"')])
        assert updated == '<img src="a.png" alt="He said &quot;hi&quot;">'

    def test_escape_helper(self):
        assert escape_html_attr('a & b < c "d"') == "a &amp; b &lt; c &quot;d&quot;"


class TestRstPatch:
    def test_replaces_alt_option(self):
        text = ".. image:: a.png\n   :alt: old\n"
        occ = occurrence_for(text, "rst")
        updated = apply_edits(text, [plan_edit(occ, "new")])
        assert updated == ".. image:: a.png\n   :alt: new\n"

    def test_inserts_missing_alt_option(self):
        text = ".. image:: a.png\n   :width: 200px\n"
        occ = occurrence_for(text, "rst")
        updated = apply_edits(text, [plan_edit(occ, "new")])
        assert ":alt: new" in updated
        assert ":width: 200px" in updated


class TestIdempotency:
    def test_applying_same_alt_twice_is_a_no_op(self):
        text = "![old](img.png)"
        occ = occurrence_for(text)
        updated = apply_edits(text, [plan_edit(occ, "new")])
        # Re-scan the updated file: the alt is now good, so no new edit.
        occ2 = occurrence_for(updated)
        assert occ2.alt_text == "new"
        assert plan_edit(occ2, "new") is None

    def test_patch_file_is_idempotent(self, tmp_path):
        path = tmp_path / "doc.md"
        path.write_text("![old](img.png)", encoding="utf-8")
        occ = occurrence_for("![old](img.png)")
        edit = plan_edit(occ, "new")
        patch_file(path, [edit], apply=True)
        first = path.read_text(encoding="utf-8")
        assert first == "![new](img.png)"

        occ2 = occurrence_for(first)
        edit2 = plan_edit(occ2, "new")
        assert edit2 is None
        patch_file(path, [edit2] if edit2 else [], apply=True)
        assert path.read_text(encoding="utf-8") == first


class TestBytePreservation:
    def test_crlf_preserved(self, tmp_path):
        path = tmp_path / "doc.md"
        raw = b"Line one\r\n\r\n![old](img.png)\r\n\r\nLast line\r\n"
        path.write_bytes(raw)
        text = raw.decode("utf-8")
        occ = occurrence_for(text)
        edit = plan_edit(occ, "new")
        patch_file(path, [edit], apply=True)
        out = path.read_bytes()
        assert b"\r\n" in out
        assert b"![new](img.png)" in out
        assert out.count(b"\n") == raw.count(b"\n")
        # Every byte outside the alt span is identical.
        assert out.replace(b"![new](img.png)", b"![old](img.png)") == raw

    def test_unicode_preserved(self, tmp_path):
        path = tmp_path / "doc.md"
        original = "héllo — 世界\n\n![old](img.png)\n\nfin\n"
        # Write bytes so the on-disk content is exactly what we scan.
        path.write_bytes(original.encode("utf-8"))
        occ = occurrence_for(original)
        edit = plan_edit(occ, "new")
        patch_file(path, [edit], apply=True)
        assert path.read_bytes().decode("utf-8") == "héllo — 世界\n\n![new](img.png)\n\nfin\n"

    def test_no_trailing_newline_added(self, tmp_path):
        path = tmp_path / "doc.md"
        path.write_text("![old](img.png)", encoding="utf-8")
        occ = occurrence_for("![old](img.png)")
        patch_file(path, [plan_edit(occ, "new")], apply=True)
        assert path.read_bytes() == b"![new](img.png)"

    def test_outside_spans_unchanged_helper(self):
        text = "![old](img.png)"
        occ = occurrence_for(text)
        edit = plan_edit(occ, "new")
        updated = apply_edits(text, [edit])
        assert outside_spans_unchanged(text, updated, [edit])


class TestDiff:
    def test_diff_contains_change(self):
        text = "![old](img.png)"
        occ = occurrence_for(text)
        patch = build_patch("doc.md", text, [plan_edit(occ, "new")])
        diff = patch.diff()
        assert "-![old](img.png)" in diff
        assert "+![new](img.png)" in diff

    def test_diff_only_alt_text(self):
        old = "![old](img.png)"
        new = "![new](img.png)"
        assert diff_only_alt_text(old, new)

    def test_diff_only_alt_text_detects_other_changes(self):
        assert not diff_only_alt_text("![old](img.png)", "![new](other.png)")

    def test_diff_only_alt_text_html(self):
        assert diff_only_alt_text(
            '<img src="a.png" alt="old">', '<img src="a.png" alt="new">'
        )

    def test_diff_only_alt_text_rst(self):
        assert diff_only_alt_text(
            ".. image:: a.png\n   :alt: old\n", ".. image:: a.png\n   :alt: new\n"
        )


class TestEscaping:
    def test_markdown_escape(self):
        assert escape_markdown_alt("a[b]c") == "a\\[b\\]c"
