"""Export generated alt text for manual rating, then score it.

Two modes:

1. ``python eval/rate.py export`` writes ``eval/ratings.csv`` with a random
   sample of (image, description) pairs. Fill in the ``score`` column with
   ``0`` (wrong), ``1`` (acceptable) or ``2`` (good).
2. ``python eval/rate.py score`` reads the file you filled in and prints the
   mean score.

The sample is deterministic: the same seed always picks the same rows, so
re-running the export does not invalidate ratings you already gave.
"""

from __future__ import annotations

import argparse
import csv
import json
import random
import statistics
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
RESULTS_PATH = REPO_ROOT / "results" / "results.json"
RATINGS_CSV = Path(__file__).resolve().parent / "ratings.csv"

SAMPLE_SIZE = 30
SEED = 20241022


def load_results() -> dict:
    if not RESULTS_PATH.is_file():
        print(
            f"ERROR: {RESULTS_PATH} not found. Run `python eval/run.py` first.",
            file=sys.stderr,
        )
        raise SystemExit(2)
    with open(RESULTS_PATH, "r", encoding="utf-8") as handle:
        return json.load(handle)


def export() -> int:
    """Write the rating sheet."""
    results = load_results()
    described = [o for o in results.get("outcomes", []) if o.get("described")]
    if not described:
        print("ERROR: the results file contains no described images.", file=sys.stderr)
        return 2

    rng = random.Random(SEED)
    sample = described if len(described) <= SAMPLE_SIZE else rng.sample(described, SAMPLE_SIZE)

    existing: dict[str, str] = {}
    if RATINGS_CSV.is_file():
        with open(RATINGS_CSV, newline="", encoding="utf-8") as handle:
            for row in csv.DictReader(handle):
                existing[row.get("key", "")] = (row.get("score") or "").strip()

    with open(RATINGS_CSV, "w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["key", "file", "line", "src", "old_alt", "new_alt", "score"])
        for outcome in sample:
            key = f"{outcome['file']}:{outcome['line']}"
            writer.writerow(
                [
                    key,
                    outcome["file"],
                    outcome["line"],
                    outcome["src"],
                    outcome["old_alt"],
                    outcome["new_alt"],
                    existing.get(key, ""),
                ]
            )

    print(f"Wrote {RATINGS_CSV} with {len(sample)} row(s).")
    print("Fill in the `score` column with 0 (wrong), 1 (acceptable) or 2 (good).")
    print("Then run: python eval/rate.py score")
    return 0


def score() -> int:
    """Print the mean of the manually assigned scores."""
    if not RATINGS_CSV.is_file():
        print(
            f"ERROR: {RATINGS_CSV} not found. Run `python eval/rate.py export` first.",
            file=sys.stderr,
        )
        return 2

    values: list[int] = []
    with open(RATINGS_CSV, newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            raw = (row.get("score") or "").strip()
            if not raw:
                continue
            try:
                values.append(int(raw))
            except ValueError:
                print(f"WARNING: ignoring non numeric score {raw!r}", file=sys.stderr)

    if not values:
        print("No scores filled in yet.")
        return 1

    mean = statistics.fmean(values)
    distribution = {value: values.count(value) for value in sorted(set(values))}
    print(f"Rated {len(values)} sample(s).")
    print(f"Distribution: {distribution}")
    print(f"Mean score: {mean:.2f} / 2")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Export and score AltFix alt text samples.")
    parser.add_argument("command", choices=["export", "score"], nargs="?", default="export")
    args = parser.parse_args()
    if args.command == "export":
        return export()
    return score()


if __name__ == "__main__":
    raise SystemExit(main())
