"""Run the AltFix evaluation suite against the live local model.

Usage:

    python eval/run.py                 # run every fixture repo
    python eval/run.py --no-cache      # force a fresh model call per image
    python eval/run.py --repo repo_charts

Metrics produced (all from a real run, nothing is estimated):

* detection recall and precision against ``eval/expected.json``
* classification accuracy per image
* quality check pass rate
* diff purity: only alt text bytes changed
* mean latency per image
* cache hit rate
* human rating summary, once ``eval/ratings.csv`` has been filled in
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import statistics
import sys
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from altfix.cache import DescriptionCache  # noqa: E402
from altfix.classify import ImageClass  # noqa: E402
from altfix.client import LocalVisionClient  # noqa: E402
from altfix.config import load_config  # noqa: E402
from altfix.describe import Describer  # noqa: E402
from altfix.patch import build_patch, diff_only_alt_text, plan_edit  # noqa: E402
from altfix.pipeline import resolve_image_path  # noqa: E402
from altfix.quality import NEEDS_REVIEW  # noqa: E402
from altfix.scan import scan_path  # noqa: E402

FIXTURE_ROOT = Path(__file__).resolve().parent / "fixtures"
EXPECTED_PATH = Path(__file__).resolve().parent / "expected.json"
RESULTS_DIR = REPO_ROOT / "results"
RATINGS_CSV = Path(__file__).resolve().parent / "ratings.csv"


@dataclass
class ImageOutcome:
    """What happened to one image during the evaluation run."""

    file: str
    line: int
    src: str
    old_alt: str
    detected_class: str
    expected_class: str
    should_fix: bool
    described: bool = False
    new_alt: str = ""
    quality_ok: bool = False
    quality_reason: str = ""
    attempts: int = 0
    latency_ms: float = 0.0
    cached: bool = False
    model: str = ""
    prompt_version: str = ""
    needs_review: bool = False
    error: str = ""


@dataclass
class EvalResult:
    """The full result of one evaluation run."""

    started_at: str
    finished_at: str
    model: str
    quantization: str
    base_url: str
    context_length: int
    temperature: float
    seed: int
    max_tokens: int
    prompt_version: str
    reasoning_effort: str
    use_cache: bool
    total_images_scanned: int = 0
    expected_images: int = 0
    detected_images: int = 0
    true_positives: int = 0
    false_positives: int = 0
    false_negatives: int = 0
    true_negatives: int = 0
    classification_correct: int = 0
    classification_total: int = 0
    quality_attempted: int = 0
    quality_passed: int = 0
    diff_pure: int = 0
    diff_total: int = 0
    needs_review: int = 0
    latencies_ms: list[float] = field(default_factory=list)
    cache_hits: int = 0
    cache_requests: int = 0
    outcomes: list[dict[str, Any]] = field(default_factory=list)
    human_ratings: dict[str, Any] = field(default_factory=dict)
    notes: list[str] = field(default_factory=list)

    @property
    def detection_recall(self) -> float:
        if self.true_positives + self.false_negatives == 0:
            return 0.0
        return self.true_positives / (self.true_positives + self.false_negatives)

    @property
    def detection_precision(self) -> float:
        if self.true_positives + self.false_positives == 0:
            return 0.0
        return self.true_positives / (self.true_positives + self.false_positives)

    @property
    def quality_pass_rate(self) -> float:
        if self.quality_attempted == 0:
            return 0.0
        return self.quality_passed / self.quality_attempted

    @property
    def diff_purity_rate(self) -> float:
        if self.diff_total == 0:
            return 0.0
        return self.diff_pure / self.diff_total

    @property
    def mean_latency_ms(self) -> float:
        if not self.latencies_ms:
            return 0.0
        return statistics.fmean(self.latencies_ms)

    @property
    def cache_hit_rate(self) -> float:
        if self.cache_requests == 0:
            return 0.0
        return self.cache_hits / self.cache_requests

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data.update(
            {
                "detection_recall": round(self.detection_recall, 4),
                "detection_precision": round(self.detection_precision, 4),
                "classification_accuracy": round(
                    self.classification_correct / self.classification_total, 4
                )
                if self.classification_total
                else 0.0,
                "quality_pass_rate": round(self.quality_pass_rate, 4),
                "diff_purity_rate": round(self.diff_purity_rate, 4),
                "mean_latency_ms": round(self.mean_latency_ms, 1),
                "median_latency_ms": round(statistics.median(self.latencies_ms), 1)
                if self.latencies_ms
                else 0.0,
                "cache_hit_rate": round(self.cache_hit_rate, 4),
            }
        )
        return data


def load_expected() -> dict[str, Any]:
    with open(EXPECTED_PATH, "r", encoding="utf-8") as handle:
        return json.load(handle)


def relative_to_fixture(path: str | Path) -> str:
    """Return *path* relative to the fixture root, with forward slashes."""
    try:
        return Path(path).resolve().relative_to(FIXTURE_ROOT.resolve()).as_posix()
    except ValueError:
        return Path(path).as_posix()


def load_ratings() -> dict[str, Any]:
    """Load the manually filled in ratings CSV, if it exists."""
    if not RATINGS_CSV.is_file():
        return {"status": "not rated", "count": 0, "mean": None}
    rows = []
    with open(RATINGS_CSV, newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            value = (row.get("score") or "").strip()
            if value == "":
                continue
            try:
                rows.append(int(value))
            except ValueError:
                continue
    if not rows:
        return {"status": "not rated", "count": 0, "mean": None}
    return {
        "status": "rated",
        "count": len(rows),
        "mean": round(statistics.fmean(rows), 4),
        "distribution": {str(v): rows.count(v) for v in sorted(set(rows))},
    }


def run(
    repos: Optional[list[str]] = None,
    use_cache: bool = True,
    limit: Optional[int] = None,
) -> EvalResult:
    """Run the evaluation and return the populated result object."""
    config = load_config()
    expected = load_expected()
    expected_by_key: dict[tuple[str, int], dict[str, Any]] = {
        (entry["file"], entry["line"]): entry for entry in expected["images"]
    }
    excluded_keys = {
        (entry["file"], entry["line"]) for entry in expected.get("excluded", [])
    }

    client = LocalVisionClient(config)
    cache = DescriptionCache(config.cache_dir, enabled=use_cache)
    describer = Describer(config=config, client=client, cache=cache)

    started = datetime.now(timezone.utc)
    result = EvalResult(
        started_at=started.isoformat(),
        finished_at="",
        model=config.model,
        quantization=config.quantization,
        base_url=config.base_url,
        context_length=config.context_length,
        temperature=config.temperature,
        seed=config.seed,
        max_tokens=config.max_tokens,
        prompt_version=config.prompt_version,
        reasoning_effort=config.reasoning_effort,
        use_cache=use_cache,
        expected_images=len(expected["images"]),
    )

    fixture_dirs = sorted(p for p in FIXTURE_ROOT.iterdir() if p.is_dir())
    if repos:
        fixture_dirs = [p for p in fixture_dirs if p.name in repos]

    described_count = 0
    for fixture in fixture_dirs:
        scans = scan_path(fixture)
        for scan in scans:
            rel_file = relative_to_fixture(scan.file_path)
            result.total_images_scanned += len(scan.images)
            for occurrence in scan.images:
                key = (rel_file, occurrence.line_start)
                if key in excluded_keys:
                    continue
                if key not in expected_by_key:
                    result.notes.append(
                        f"unexpected image found at {rel_file}:{occurrence.line_start} "
                        f"({occurrence.src}) - not in expected.json"
                    )
                    continue

                truth = expected_by_key[key]
                outcome = ImageOutcome(
                    file=rel_file,
                    line=occurrence.line_start,
                    src=occurrence.src,
                    old_alt=occurrence.alt_text,
                    detected_class=occurrence.classification.value,
                    expected_class=truth["expected_class"],
                    should_fix=bool(truth["should_fix"]),
                    model=config.model,
                    prompt_version=config.prompt_version,
                )

                result.detected_images += 1
                if occurrence.classification.value == truth["expected_class"]:
                    result.classification_correct += 1
                result.classification_total += 1

                flagged = occurrence.needs_fix
                if flagged and truth["should_fix"]:
                    result.true_positives += 1
                elif flagged and not truth["should_fix"]:
                    result.false_positives += 1
                elif not flagged and truth["should_fix"]:
                    result.false_negatives += 1
                else:
                    result.true_negatives += 1

                if flagged and truth["should_fix"]:
                    image_path = resolve_image_path(fixture, occurrence)
                    if image_path is None:
                        outcome.error = "image file not found"
                        outcome.needs_review = True
                    else:
                        if limit is not None and described_count >= limit:
                            outcome.error = "skipped (limit reached)"
                        else:
                            described_count += 1
                            description = describer.describe(
                                image_path, occurrence, use_cache=use_cache
                            )
                            outcome.described = True
                            outcome.attempts = description.attempts
                            outcome.latency_ms = round(description.latency_ms, 1)
                            outcome.cached = description.cached
                            outcome.new_alt = description.text
                            outcome.quality_ok = description.ok
                            outcome.quality_reason = description.reason
                            outcome.needs_review = not description.ok
                            outcome.error = description.error
                            result.quality_attempted += 1
                            if description.ok:
                                result.quality_passed += 1
                            else:
                                result.needs_review += 1
                            result.latencies_ms.append(description.latency_ms)

                            if description.ok:
                                edit = plan_edit(occurrence, description.text)
                                if edit is not None:
                                    original = Path(occurrence.file_path).read_bytes().decode("utf-8")
                                    patch = build_patch(occurrence.file_path, original, [edit])
                                    result.diff_total += 1
                                    if diff_only_alt_text(patch.original, patch.updated):
                                        result.diff_pure += 1
                                    else:
                                        outcome.error = "diff touched non alt text"

                result.outcomes.append(asdict(outcome))

    result.cache_hits = cache.stats.hits
    result.cache_requests = cache.stats.requests
    result.human_ratings = load_ratings()
    result.finished_at = datetime.now(timezone.utc).isoformat()
    return result


def write_results(result: EvalResult) -> Path:
    """Write ``results/results.json`` and ``results/RESULTS.md``."""
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    json_path = RESULTS_DIR / "results.json"
    with open(json_path, "w", encoding="utf-8") as handle:
        json.dump(result.to_dict(), handle, indent=2, ensure_ascii=False)
    (RESULTS_DIR / "RESULTS.md").write_text(render_markdown(result), encoding="utf-8")
    return json_path


def render_markdown(result: EvalResult) -> str:
    """Render the human readable results report."""
    data = result.to_dict()
    ratings = result.human_ratings
    rating_line = (
        f"{ratings['mean']} / 2 over {ratings['count']} samples"
        if ratings.get("mean") is not None
        else "not rated yet (fill in `eval/ratings.csv`)"
    )
    lines = [
        "# AltFix evaluation results",
        "",
        "Every number below comes from the run recorded in `results/results.json`.",
        "",
        "## Run configuration",
        "",
        "| Setting | Value |",
        "| --- | --- |",
        f"| Model | `{data['model']}` |",
        f"| Quantization | {data['quantization'] or '(not recorded)'} |",
        f"| Endpoint | `{data['base_url']}` |",
        f"| Context length | {data['context_length']} |",
        f"| Temperature | {data['temperature']} |",
        f"| Seed | {data['seed']} |",
        f"| Max tokens | {data['max_tokens']} |",
        f"| Reasoning effort | {data['reasoning_effort']} |",
        f"| Prompt version | `{data['prompt_version']}` |",
        f"| Cache | {'enabled' if data['use_cache'] else 'disabled'} |",
        f"| Started | {data['started_at']} |",
        f"| Finished | {data['finished_at']} |",
        "",
        "## Metrics",
        "",
        "| Metric | Value |",
        "| --- | --- |",
        f"| Images scanned | {data['total_images_scanned']} |",
        f"| Images in ground truth | {data['expected_images']} |",
        f"| Detection recall | {data['detection_recall']:.1%} |",
        f"| Detection precision | {data['detection_precision']:.1%} |",
        f"| Classification accuracy | {data['classification_accuracy']:.1%} |",
        f"| Quality check pass rate | {data['quality_pass_rate']:.1%} |",
        f"| Diff only touches alt text | {data['diff_purity_rate']:.1%} |",
        f"| Mean latency per image | {data['mean_latency_ms']:.0f} ms |",
        f"| Median latency per image | {data['median_latency_ms']:.0f} ms |",
        f"| Cache hit rate | {data['cache_hit_rate']:.1%} |",
        f"| Images needing review | {data['needs_review']} |",
        f"| Human rating (0-2) | {rating_line} |",
        "",
        "## Detection detail",
        "",
        f"- True positives (flagged and should be fixed): {data['true_positives']}",
        f"- False positives (flagged but should not be): {data['false_positives']}",
        f"- False negatives (should be fixed but not flagged): {data['false_negatives']}",
        f"- True negatives: {data['true_negatives']}",
        "",
        "## Generated alt text",
        "",
        "| File | Line | Source | Old alt | New alt | Attempts | Cached | Latency (ms) |",
        "| --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for outcome in result.outcomes:
        if not outcome["described"]:
            continue
        old = outcome["old_alt"] or "(empty)"
        new = outcome["new_alt"] or NEEDS_REVIEW
        lines.append(
            f"| {outcome['file']} | {outcome['line']} | `{outcome['src']}` | {old} | {new} | "
            f"{outcome['attempts']} | {'yes' if outcome['cached'] else 'no'} | {outcome['latency_ms']:.0f} |"
        )

    if result.notes:
        lines.extend(["", "## Notes", ""])
        lines.extend(f"- {note}" for note in result.notes)

    lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the AltFix evaluation suite.")
    parser.add_argument("--repo", action="append", help="Only run this fixture repo (repeatable).")
    parser.add_argument("--no-cache", action="store_true", help="Ignore cached descriptions.")
    parser.add_argument("--limit", type=int, help="Only describe N images (smoke test).")
    args = parser.parse_args()

    config = load_config()
    print(f"model: {config.model}")
    print(f"endpoint: {config.base_url}")
    print(f"quantization: {config.quantization or '(not recorded)'}")

    client = LocalVisionClient(config)
    if not client.is_available():
        print("ERROR: the model server is not reachable.", file=sys.stderr)
        print(client.server_diagnostics(), file=sys.stderr)
        return 2

    result = run(repos=args.repo, use_cache=not args.no_cache, limit=args.limit)
    path = write_results(result)

    print()
    print(f"detection recall     : {result.detection_recall:.1%}")
    print(f"detection precision  : {result.detection_precision:.1%}")
    print(f"classification accuracy: {result.classification_correct}/{result.classification_total}")
    print(f"quality pass rate    : {result.quality_pass_rate:.1%}")
    print(f"diff purity          : {result.diff_purity_rate:.1%}")
    print(f"mean latency         : {result.mean_latency_ms:.0f} ms")
    print(f"cache hit rate       : {result.cache_hit_rate:.1%}")
    print(f"needs review         : {result.needs_review}")
    print(f"saved                : {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
