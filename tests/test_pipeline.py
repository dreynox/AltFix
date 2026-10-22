"""Tests for the end to end pipeline and the CLI surface.

A stub client is used so the pipeline can be exercised without a live model.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from altfix.cli import app
from altfix.config import Config
from altfix.pipeline import resolve_image_path, run_fix


class StubClient:
    """Returns a canned description and records what it was asked."""

    def __init__(self, text="A solid red rectangle on a white background."):
        self.text = text
        self.prompts = []

    def describe(self, image_path, prompt, system_prompt=None):
        from altfix.client import ModelResponse

        self.prompts.append(prompt)
        return ModelResponse(text=self.text, model="stub-model")


def make_config(tmp_path, **overrides):
    values = dict(
        model="stub-model",
        prompt_version="v1",
        cache_dir=str(tmp_path / "cache"),
        max_alt_length=125,
    )
    values.update(overrides)
    return Config(**values)


@pytest.fixture()
def docs(tmp_path):
    """A tiny documentation tree with one PNG."""
    from PIL import Image

    (tmp_path / "docs").mkdir()
    Image.new("RGB", (16, 16), (10, 120, 200)).save(tmp_path / "docs" / "hero.png")
    (tmp_path / "docs" / "README.md").write_text(
        "# Title\n\n"
        "Some context about the product.\n\n"
        "![](hero.png)\n\n"
        "```\n![](ignored.png)\n```\n",
        encoding="utf-8",
    )
    return tmp_path


class TestPipeline:
    def test_dry_run_does_not_write(self, docs, monkeypatch):
        from altfix import pipeline

        monkeypatch.setattr(pipeline, "LocalVisionClient", lambda config: StubClient())
        before = (docs / "docs" / "README.md").read_text(encoding="utf-8")
        result = run_fix(docs, config=make_config(docs), dry_run=True)
        assert result.tasks
        assert (docs / "docs" / "README.md").read_text(encoding="utf-8") == before
        assert result.patches[0].changed

    def test_apply_writes_only_alt_text(self, docs, monkeypatch):
        from altfix import pipeline

        monkeypatch.setattr(pipeline, "LocalVisionClient", lambda config: StubClient())
        run_fix(docs, config=make_config(docs), dry_run=False)
        after = (docs / "docs" / "README.md").read_text(encoding="utf-8")
        assert "![A solid red rectangle on a white background](hero.png)" in after
        # The code fence content is untouched.
        assert "![](ignored.png)" in after

    def test_second_run_is_idempotent(self, docs, monkeypatch):
        from altfix import pipeline

        monkeypatch.setattr(pipeline, "LocalVisionClient", lambda config: StubClient())
        run_fix(docs, config=make_config(docs), dry_run=False)
        first = (docs / "docs" / "README.md").read_text(encoding="utf-8")
        result = run_fix(docs, config=make_config(docs), dry_run=False)
        second = (docs / "docs" / "README.md").read_text(encoding="utf-8")
        assert first == second
        assert not result.patches or not result.patches[0].changed

    def test_context_is_passed_to_the_model(self, docs, monkeypatch):
        from altfix import pipeline

        stub = StubClient()
        monkeypatch.setattr(pipeline, "LocalVisionClient", lambda config: stub)
        run_fix(docs, config=make_config(docs), dry_run=True)
        assert stub.prompts
        assert "Title" in stub.prompts[0]

    def test_failed_quality_is_marked_needs_review(self, docs, monkeypatch):
        from altfix import pipeline

        monkeypatch.setattr(pipeline, "LocalVisionClient", lambda config: StubClient("image"))
        result = run_fix(docs, config=make_config(docs), dry_run=True)
        assert result.needs_review
        assert not result.patches

    def test_missing_image_file_is_reported(self, docs, monkeypatch):
        from altfix import pipeline

        monkeypatch.setattr(pipeline, "LocalVisionClient", lambda config: StubClient())
        (docs / "docs" / "hero.png").unlink()
        result = run_fix(docs, config=make_config(docs), dry_run=True)
        assert result.tasks[0].error

    def test_resolve_image_path(self, docs):
        from altfix.scan import scan_path

        scans = scan_path(docs)
        occ = scans[0].images[0]
        assert resolve_image_path(docs, occ) == docs / "docs" / "hero.png"

    def test_crlf_file_keeps_line_endings(self, tmp_path, monkeypatch):
        from altfix import pipeline

        from PIL import Image

        Image.new("RGB", (8, 8), (0, 200, 0)).save(tmp_path / "hero.png")
        readme = tmp_path / "README.md"
        raw = b"# Title\r\n\r\n![](hero.png)\r\n\r\nEnd.\r\n"
        readme.write_bytes(raw)

        monkeypatch.setattr(pipeline, "LocalVisionClient", lambda config: StubClient())
        run_fix(tmp_path, config=make_config(tmp_path), dry_run=False)

        out = readme.read_bytes()
        assert out.count(b"\r\n") == raw.count(b"\r\n")
        assert b"![A solid red rectangle on a white background](hero.png)" in out
        # Nothing outside the alt span changed.
        assert out.replace(
            b"![A solid red rectangle on a white background](hero.png)",
            b"![](hero.png)",
        ) == raw

    def test_resolve_image_path_rejects_remote(self):
        from altfix.scan import scan_text

        occ = scan_text("![](https://x.dev/a.png)", "d.md", "markdown").images[0]
        assert resolve_image_path(".", occ) is None


class TestCli:
    def test_scan_command(self, docs):
        runner = CliRunner()
        result = runner.invoke(app, ["scan", str(docs)])
        assert result.exit_code == 0
        assert "missing" in result.stdout

    def test_scan_json(self, docs):
        runner = CliRunner()
        result = runner.invoke(app, ["scan", str(docs), "--json"])
        assert result.exit_code == 0
        payload = json.loads(result.stdout)
        assert payload["counts"]["missing"] == 1

    def test_fix_dry_run_does_not_write(self, docs, monkeypatch):
        from altfix import pipeline

        monkeypatch.setattr(pipeline, "LocalVisionClient", lambda config: StubClient())
        runner = CliRunner()
        before = (docs / "docs" / "README.md").read_text(encoding="utf-8")
        result = runner.invoke(app, ["fix", str(docs), "--dry-run"])
        assert result.exit_code == 0
        assert (docs / "docs" / "README.md").read_text(encoding="utf-8") == before

    def test_fix_apply_writes(self, docs, monkeypatch):
        from altfix import pipeline

        monkeypatch.setattr(pipeline, "LocalVisionClient", lambda config: StubClient())
        runner = CliRunner()
        result = runner.invoke(app, ["fix", str(docs), "--apply", "--no-dry-run"])
        assert result.exit_code == 0
        assert "![A solid red rectangle" in (docs / "docs" / "README.md").read_text(encoding="utf-8")

    def test_help_lists_all_commands(self):
        runner = CliRunner()
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        for command in ("scan", "fix", "pr", "review", "demo"):
            assert command in result.stdout
