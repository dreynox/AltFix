"""End to end pipeline: scan, describe, patch.

This module is shared by the CLI and the evaluation suite so that both use
exactly the same code path.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from .cache import DescriptionCache
from .classify import ImageClass
from .client import LocalVisionClient
from .config import Config, load_config
from .describe import Description, Describer
from .patch import AltEdit, FilePatch, build_patch, plan_edit
from .quality import NEEDS_REVIEW
from .scan import ImageOccurrence, ScanResult, scan_path


@dataclass
class ImageTask:
    """One image that needs alt text, plus what happened to it."""

    occurrence: ImageOccurrence
    description: Optional[Description] = None
    edit: Optional[AltEdit] = None
    error: str = ""

    @property
    def new_alt(self) -> str:
        if self.description is None or not self.description.ok:
            return NEEDS_REVIEW
        return self.description.text

    @property
    def will_change(self) -> bool:
        return self.edit is not None


@dataclass
class RunResult:
    """Everything a single run produced."""

    root: str
    tasks: list[ImageTask] = field(default_factory=list)
    scans: list[ScanResult] = field(default_factory=list)
    patches: list[FilePatch] = field(default_factory=list)
    total_images: int = 0
    elapsed_s: float = 0.0
    cache_hits: int = 0
    cache_requests: int = 0
    model: str = ""
    prompt_version: str = ""

    @property
    def needs_review(self) -> list[ImageTask]:
        return [t for t in self.tasks if t.description is not None and not t.description.ok]

    @property
    def applied(self) -> int:
        return sum(1 for p in self.patches if p.changed)


def resolve_image_path(root: str | Path, occurrence: ImageOccurrence) -> Optional[Path]:
    """Locate the image file referenced by *occurrence* relative to *root*."""
    if not occurrence.src or occurrence.src.startswith(("http://", "https://", "data:")):
        return None
    src = occurrence.src.split("?")[0].split("#")[0]
    if not src:
        return None
    base = Path(root)
    candidates = [
        base / src,
        Path(occurrence.file_path).parent / src,
    ]
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    return None


def run_fix(
    root: str | Path,
    config: Optional[Config] = None,
    use_cache: bool = True,
    dry_run: bool = True,
    limit: Optional[int] = None,
    console=None,
) -> RunResult:
    """Scan *root*, describe every image that needs alt text and build patches.

    Args:
        root: File or directory to scan.
        config: Runtime configuration.
        use_cache: Reuse cached descriptions when the cache is enabled.
        dry_run: Build the patches but do not write anything to disk.
        limit: Maximum number of images to describe (useful for smoke tests).
        console: Optional rich console for progress output.
    """
    config = config or load_config()
    client = LocalVisionClient(config)
    cache = DescriptionCache(config.cache_dir, enabled=use_cache)
    describer = Describer(config=config, client=client, cache=cache)

    started = time.perf_counter()
    scans = scan_path(root)
    result = RunResult(
        root=str(root),
        scans=scans,
        model=config.model,
        prompt_version=config.prompt_version,
    )
    result.total_images = sum(len(scan.images) for scan in scans)

    by_file: dict[str, list[AltEdit]] = {}
    described = 0

    for scan in scans:
        for occurrence in scan.images:
            if occurrence.classification not in (ImageClass.MISSING, ImageClass.LOW_QUALITY):
                continue
            task = ImageTask(occurrence=occurrence)
            result.tasks.append(task)

            if limit is not None and described >= limit:
                task.error = "skipped (limit reached)"
                continue

            image_path = resolve_image_path(root, occurrence)
            if image_path is None:
                task.error = "image file not found or remote"
                continue

            try:
                description = describer.describe(image_path, occurrence, use_cache=use_cache)
            except Exception as exc:  # noqa: BLE001 - reported per image
                task.error = str(exc)
                continue

            task.description = description
            described += 1
            if not description.ok:
                task.error = description.reason or "needs review"
                continue

            edit = plan_edit(occurrence, description.text)
            if edit is None:
                continue
            task.edit = edit
            by_file.setdefault(occurrence.file_path, []).append(edit)

    for file_path, edits in by_file.items():
        path = Path(file_path)
        try:
            original = path.read_bytes().decode("utf-8")
        except OSError:
            continue
        result.patches.append(build_patch(path, original, edits))

    if not dry_run:
        for patch in result.patches:
            if patch.changed:
                Path(patch.file_path).write_bytes(patch.updated.encode("utf-8"))

    result.elapsed_s = time.perf_counter() - started
    result.cache_hits = cache.stats.hits
    result.cache_requests = cache.stats.requests
    return result


def render_diff(result: RunResult) -> str:
    """Render the unified diff of every patched file."""
    chunks: list[str] = []
    for patch in result.patches:
        if patch.changed:
            chunks.append(patch.diff())
    return "".join(chunks)
