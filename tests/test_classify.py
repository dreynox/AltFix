"""Tests for the rule based classifier."""

from __future__ import annotations

import pytest

from altfix.classify import (
    ImageClass,
    classify,
    is_badge,
    is_decorative,
    is_filename_echo,
    is_generic,
)


class TestClassification:
    def test_missing_when_no_alt(self):
        assert classify(None, "a.png") is ImageClass.MISSING
        assert classify("", "a.png") is ImageClass.MISSING
        assert classify("   ", "a.png") is ImageClass.MISSING

    @pytest.mark.parametrize(
        "alt",
        ["image", "Image", "picture", "screenshot", "photo", "img", "logo", "graph", "diagram"],
    )
    def test_low_quality_for_generic_words(self, alt):
        assert classify(alt, "a.png") is ImageClass.LOW_QUALITY

    def test_low_quality_for_filename_echo(self):
        assert classify("chart.png", "images/chart.png") is ImageClass.LOW_QUALITY
        assert classify("chart", "images/chart.png") is ImageClass.LOW_QUALITY

    def test_low_quality_for_numbered_generic(self):
        assert classify("image1", "a.png") is ImageClass.LOW_QUALITY
        assert classify("screenshot 2", "a.png") is ImageClass.LOW_QUALITY

    def test_ok_for_real_description(self):
        alt = "Bar chart of monthly sales rising from 10 to 40 units."
        assert classify(alt, "chart.png") is ImageClass.OK

    def test_decorative_for_badge(self):
        assert classify("Build Status", "https://shields.io/badge/build-passing-green") is ImageClass.DECORATIVE

    def test_decorative_for_spacer(self):
        assert classify("", "assets/spacer.png") is ImageClass.DECORATIVE
        assert classify("x", "images/pixel.gif") is ImageClass.DECORATIVE

    def test_decorative_wins_over_missing(self):
        assert classify(None, "https://img.shields.io/badge/x-y-blue") is ImageClass.DECORATIVE


class TestHelpers:
    def test_is_badge(self):
        assert is_badge("https://shields.io/badge/a-b-c")
        assert is_badge("https://img.shields.io/badge/a-b-c")
        assert not is_badge("images/architecture.png")

    def test_is_decorative(self):
        assert is_decorative("assets/spacer.gif")
        assert is_decorative("blank.png")
        assert not is_decorative("images/architecture.png")

    def test_is_filename_echo(self):
        assert is_filename_echo("diagram.png", "docs/diagram.png")
        assert not is_filename_echo("An architecture diagram", "docs/diagram.png")

    def test_is_generic(self):
        assert is_generic("image")
        assert is_generic("IMG")
        assert not is_generic("A terminal showing a deploy")

    def test_classification_values(self):
        assert ImageClass.MISSING.value == "missing"
        assert ImageClass.LOW_QUALITY.value == "low_quality"
        assert ImageClass.OK.value == "ok"
        assert ImageClass.DECORATIVE.value == "decorative"
