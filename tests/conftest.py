"""Shared pytest fixtures."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

SRC = Path(__file__).resolve().parents[1] / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


@pytest.fixture()
def sample_image(tmp_path):
    """A small generated PNG so tests never depend on binary assets."""
    from PIL import Image

    path = tmp_path / "sample.png"
    image = Image.new("RGB", (32, 24), (200, 30, 30))
    image.save(path)
    return path
