"""Tests for the scanner: formats, spans, code fences and context."""

from __future__ import annotations

import pytest

from altfix.scan import scan_text


def scan_markdown(text: str):
    return scan_text(text, "doc.md", "markdown").images


def scan_html(text: str):
    return scan_text(text, "doc.html", "html").images


def scan_rst(text: str):
    return scan_text(text, "doc.rst", "rst").images


class TestMarkdown:
    def test_inline_image(self):
        images = scan_markdown("Hello ![a chart](chart.png) world")
        assert len(images) == 1
        assert images[0].alt_text == "a chart"
        assert images[0].src == "chart.png"
        assert images[0].alt_span is not None

    def test_empty_alt(self):
        images = scan_markdown("![](chart.png)")
        assert len(images) == 1
        assert images[0].alt_text == ""

    def test_alt_span_points_at_alt_text(self):
        text = "Hello ![a chart](chart.png) world"
        image = scan_markdown(text)[0]
        start, end = image.alt_span
        assert text[start:end] == "a chart"

    def test_reference_style(self):
        text = "See ![caption][ref].\n\n[ref]: images/photo.png\n"
        images = scan_markdown(text)
        assert len(images) == 1
        assert images[0].kind == "reference"
        assert images[0].alt_text == "caption"
        assert images[0].src == "images/photo.png"

    def test_collapsed_reference(self):
        text = "See ![caption][].\n\n[caption]: images/photo.png\n"
        images = scan_markdown(text)
        assert len(images) == 1
        assert images[0].src == "images/photo.png"

    def test_multiple_images_on_one_line(self):
        text = "![one](a.png) and ![two](b.png) and ![three](c.png)"
        images = scan_markdown(text)
        assert len(images) == 3
        assert [i.src for i in images] == ["a.png", "b.png", "c.png"]

    def test_nested_link_image(self):
        text = "[![alt text](img.png)](https://example.com)"
        images = scan_markdown(text)
        assert len(images) == 1
        assert images[0].alt_text == "alt text"
        assert images[0].context_link == "https://example.com"

    def test_image_with_title(self):
        images = scan_markdown('![alt](img.png "The title")')
        assert len(images) == 1
        assert images[0].src == "img.png"

    def test_image_with_angle_bracket_src(self):
        images = scan_markdown("![alt](<my image.png>)")
        assert images[0].src == "my image.png"

    def test_heading_context(self):
        text = "# Getting started\n\nSome text.\n\n![alt](x.png)\n"
        images = scan_markdown(text)
        assert images[0].context_heading == "Getting started"

    def test_paragraph_context(self):
        text = "# Title\n\nThe quick brown fox jumps over the lazy dog.\n\n![alt](x.png)\n"
        images = scan_markdown(text)
        assert "quick brown fox" in images[0].context_before

    def test_unicode_alt(self):
        images = scan_markdown("![日本語のキャプション](画像.png)")
        assert images[0].alt_text == "日本語のキャプション"
        assert images[0].src == "画像.png"

    def test_special_characters_in_src(self):
        images = scan_markdown("![alt](images/a_b-c(1).png)")
        assert len(images) == 1


class TestCodeFences:
    def test_backtick_fence_ignored(self):
        text = "```md\n![in fence](a.png)\n```\n\n![real](b.png)\n"
        images = scan_markdown(text)
        assert len(images) == 1
        assert images[0].src == "b.png"

    def test_tilde_fence_ignored(self):
        text = "~~~\n![in fence](a.png)\n~~~\n\n![real](b.png)\n"
        images = scan_markdown(text)
        assert len(images) == 1
        assert images[0].src == "b.png"

    def test_longer_fence_ignored(self):
        text = "````md\n![in fence](a.png)\n````\n\n![real](b.png)\n"
        images = scan_markdown(text)
        assert len(images) == 1
        assert images[0].src == "b.png"

    def test_unclosed_fence_ignores_rest(self):
        text = "```\n![in fence](a.png)\n"
        images = scan_markdown(text)
        assert len(images) == 0

    def test_fence_with_inner_backticks(self):
        text = "````\n```\n![in fence](a.png)\n```\n````\n\n![real](b.png)\n"
        images = scan_markdown(text)
        assert len(images) == 1
        assert images[0].src == "b.png"

    def test_indented_fence_ignored(self):
        text = "  ```\n  ![in fence](a.png)\n  ```\n\n![real](b.png)\n"
        images = scan_markdown(text)
        assert len(images) == 1


class TestHtml:
    def test_img_with_alt(self):
        images = scan_html('<img src="a.png" alt="A description">')
        assert len(images) == 1
        assert images[0].alt_text == "A description"
        assert images[0].src == "a.png"

    def test_img_without_alt(self):
        images = scan_html('<img src="a.png">')
        assert len(images) == 1
        assert images[0].alt_text == ""
        assert images[0].insert_span is not None
        assert images[0].insert_template == ' alt="{}"'

    def test_img_single_quoted_alt(self):
        images = scan_html("<img src='a.png' alt='single'>")
        assert images[0].alt_text == "single"

    def test_img_unquoted_alt(self):
        images = scan_html("<img src=a.png alt=bare>")
        assert images[0].alt_text == "bare"

    def test_picture_with_img(self):
        text = (
            "<picture>"
            '<source srcset="a.webp" type="image/webp">'
            '<img src="a.png" alt="Inside a picture">'
            "</picture>"
        )
        images = scan_html(text)
        assert len(images) == 1
        assert images[0].alt_text == "Inside a picture"

    def test_html_pre_block_ignored(self):
        text = "<pre>![alt](a.png)</pre>\n<img src=\"b.png\" alt=\"real\">"
        images = scan_html(text)
        assert len(images) == 1
        assert images[0].src == "b.png"

    def test_html_code_block_ignored(self):
        text = "<code><img src=\"a.png\" alt=\"x\"></code>"
        assert len(scan_html(text)) == 0

    def test_html_heading_context(self):
        text = "<h1>Install</h1>\n<p>Run it.</p>\n<img src=\"a.png\" alt=\"\">"
        images = scan_html(text)
        assert images[0].context_heading == "Install"


class TestRst:
    def test_image_with_alt(self):
        text = ".. image:: img/photo.png\n   :alt: A photo of a cat\n"
        images = scan_rst(text)
        assert len(images) == 1
        assert images[0].src == "img/photo.png"
        assert images[0].alt_text == "A photo of a cat"

    def test_image_without_alt(self):
        text = ".. image:: img/photo.png\n   :width: 200px\n"
        images = scan_rst(text)
        assert len(images) == 1
        assert images[0].alt_text == ""
        assert images[0].insert_span is not None
        assert ":alt:" in images[0].insert_template

    def test_figure(self):
        text = ".. figure:: img/plot.png\n\n   The caption.\n"
        images = scan_rst(text)
        assert len(images) == 1
        assert images[0].kind == "figure"

    def test_code_block_ignored(self):
        text = ".. code-block:: python\n\n   ![alt](a.png)\n"
        assert len(scan_rst(text)) == 0

    def test_alt_span_points_at_value(self):
        text = ".. image:: img/photo.png\n   :alt: A photo of a cat\n"
        image = scan_rst(text)[0]
        start, end = image.alt_span
        assert text[start:end] == "A photo of a cat"


class TestSpans:
    @pytest.mark.parametrize(
        "text,fmt",
        [
            ("![alt](a.png)", "markdown"),
            ('<img src="a.png" alt="alt">', "html"),
            (".. image:: a.png\n   :alt: alt\n", "rst"),
        ],
    )
    def test_span_matches_source_text(self, text, fmt):
        image = scan_text(text, "d", fmt).images[0]
        start, end = image.alt_span
        assert text[start:end] == image.alt_text
