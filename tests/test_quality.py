"""Tests for the quality checks applied to generated alt text."""

from __future__ import annotations

import pytest

from altfix.quality import (
    MAX_ALT_LENGTH,
    NEEDS_REVIEW,
    check,
    clean,
    strip_think,
    truncate,
)


class TestStripThink:
    def test_removes_think_block(self):
        assert strip_think("<think>reasoning here</think>The answer") == "The answer"

    def test_removes_unclosed_think_block(self):
        assert strip_think("<think>reasoning only") == ""

    def test_leaves_plain_text(self):
        assert strip_think("Plain answer") == "Plain answer"


class TestClean:
    def test_strips_quotes(self):
        assert clean('"A quoted description"') == "A quoted description"

    def test_strips_markdown_emphasis(self):
        assert clean("**Bold** description") == "Bold description"

    def test_strips_markdown_link(self):
        assert clean("See [the docs](https://x.dev) here") == "See the docs here"

    def test_strips_image_of_prefix(self):
        assert clean("Image of a red bicycle") == "a red bicycle"

    def test_strips_this_screenshot_shows_prefix(self):
        assert clean("This screenshot shows the login form") == "the login form"

    def test_strips_code_fence(self):
        assert clean("```\nA chart of sales\n```") == "A chart of sales"

    def test_collapses_whitespace(self):
        assert clean("A   chart\n\nwith   spaces") == "A chart with spaces"

    def test_removes_trailing_period(self):
        assert clean("A chart of sales.") == "A chart of sales"

    def test_empty_input(self):
        assert clean("") == ""
        assert clean("   ") == ""


class TestCheck:
    def test_valid_description_passes(self):
        result = check("A bar chart of monthly sales rising from 10 to 40 units.", "chart.png")
        assert result.ok
        assert result.text.startswith("A bar chart")

    def test_empty_is_rejected(self):
        result = check("", "a.png")
        assert not result.ok
        assert result.reason == "empty"

    def test_generic_is_rejected(self):
        result = check("image", "a.png")
        assert not result.ok
        assert result.reason == "generic"

    def test_filename_echo_is_rejected(self):
        result = check("chart.png", "images/chart.png")
        assert not result.ok
        assert result.reason == "filename_echo"

    def test_length_is_enforced(self):
        long_text = "A detailed chart of monthly sales " * 20
        result = check(long_text, "a.png")
        assert result.ok
        assert len(result.text) <= MAX_ALT_LENGTH
        assert result.reason == "truncated"

    def test_truncation_respects_max_length(self):
        result = check("word " * 100, "a.png")
        assert len(result.text) <= MAX_ALT_LENGTH

    def test_truncate_helper(self):
        assert truncate("hello world", 5) == "hello"
        assert truncate("short", 50) == "short"

    def test_think_only_output_is_empty(self):
        result = check("<think>only reasoning</think>", "a.png")
        assert not result.ok

    def test_needs_review_marker(self):
        assert NEEDS_REVIEW == "[needs review]"


class TestUnicode:
    def test_unicode_survives_cleaning(self):
        result = check("Un diagramme montrant un café — les données 2024", "d.png")
        assert result.ok
        assert "café" in result.text
        assert "—" in result.text
