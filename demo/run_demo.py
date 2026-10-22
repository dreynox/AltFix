"""Run the AltFix demo on the bundled sample repository.

Two modes:

``python demo/run_demo.py --pregenerate``
    Calls the local model once for every image in the sample repo and stores
    the answers in ``demo/pregenerated_cache/``. The file it writes is
    labelled as pre-generated so nobody mistakes it for a live run.

``python demo/run_demo.py``
    Plays the demo. It uses the pre-generated cache when one is available
    and says so, or runs live against the model with ``--live``.

    python demo/run_demo.py --live      # ignore the cache, call the model
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from altfix.cache import DescriptionCache  # noqa: E402
from altfix.client import LocalVisionClient  # noqa: E402
from altfix.config import load_config  # noqa: E402
from altfix.describe import Describer  # noqa: E402
from altfix.pipeline import resolve_image_path  # noqa: E402
from altfix.scan import scan_path  # noqa: E402

SAMPLE_REPO = REPO_ROOT / "demo" / "sample_repo"
PREGENERATED_DIR = REPO_ROOT / "demo" / "pregenerated_cache"

PREGENERATED_BANNER = (
    "PRE-GENERATED DEMO OUTPUT - these descriptions were produced by an "
    "earlier real run of the local model and are cached for a fast, "
    "reproducible demo. They are not mocked or hand written."
)


def pregenerate() -> int:
    """Call the model for every image and store the answers."""
    config = load_config()
    client = LocalVisionClient(config)
    if not client.is_available():
        print("ERROR: the model server is not reachable.")
        print(client.server_diagnostics())
        return 2

    if PREGENERATED_DIR.exists():
        shutil.rmtree(PREGENERATED_DIR)

    cache = DescriptionCache(PREGENERATED_DIR)
    describer = Describer(config=config, client=client, cache=cache)

    count = 0
    for scan in scan_path(SAMPLE_REPO):
        for occurrence in scan.images:
            if not occurrence.needs_fix:
                continue
            image_path = resolve_image_path(SAMPLE_REPO, occurrence)
            if image_path is None:
                print(f"  skipped (image not found): {occurrence.src}")
                continue
            description = describer.describe(image_path, occurrence, use_cache=False)
            count += 1
            state = "ok" if description.ok else f"needs review ({description.reason})"
            print(f"  {occurrence.src}: {description.text}  [{state}]")

    manifest = {
        "banner": PREGENERATED_BANNER,
        "model": config.model,
        "prompt_version": config.prompt_version,
        "base_url": config.base_url,
        "temperature": config.temperature,
        "seed": config.seed,
        "images_described": count,
    }
    with open(PREGENERATED_DIR / "MANIFEST.json", "w", encoding="utf-8") as handle:
        json.dump(manifest, handle, indent=2, ensure_ascii=False)

    print(f"\nPre-generated {count} description(s) into {PREGENERATED_DIR}")
    return 0


def play(live: bool) -> int:
    """Run the demo and show the before/after."""
    config = load_config()

    if live:
        print("LIVE mode: every description is produced by the local model now.\n")
        client = LocalVisionClient(config)
        if not client.is_available():
            print("ERROR: the model server is not reachable.")
            print(client.server_diagnostics())
            return 2
        cache = DescriptionCache(config.cache_dir)
        use_cache = False
    else:
        manifest_path = PREGENERATED_DIR / "MANIFEST.json"
        if not manifest_path.is_file():
            print("No pre-generated cache found. Run:")
            print("    python demo/run_demo.py --pregenerate")
            print("or pass --live to describe the images now.")
            return 2
        with open(manifest_path, "r", encoding="utf-8") as handle:
            manifest = json.load(handle)
        print(f"[yellow]{manifest['banner']}[/]\n")
        print(f"  model: {manifest['model']}")
        print(f"  prompt version: {manifest['prompt_version']}")
        print(f"  images described: {manifest['images_described']}\n")
        cache = DescriptionCache(PREGENERATED_DIR)
        use_cache = True

    # Work on a copy so the demo never mutates the bundled sample repo.
    with tempfile.TemporaryDirectory() as tmp:
        work = Path(tmp) / "sample_repo"
        shutil.copytree(SAMPLE_REPO, work)

        cmd = [
            sys.executable,
            "-m",
            "altfix.cli",
            "fix",
            str(work),
            "--apply",
            "--no-dry-run",
        ]
        if use_cache:
            cmd += ["--cache"]
        else:
            cmd += ["--no-cache"]

        env = {
            **dict(__import__("os").environ),
            "ALTFIX_CACHE_DIR": str(cache.dir),
        }
        result = subprocess.run(cmd, env=env)
        if result.returncode != 0:
            return result.returncode

        print("\n--- Patched README.md ---\n")
        readme = work / "README.md"
        if readme.is_file():
            print(readme.read_text(encoding="utf-8"))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="AltFix demo runner.")
    parser.add_argument("--pregenerate", action="store_true", help="Generate the cached demo output.")
    parser.add_argument("--live", action="store_true", help="Describe the images now, ignoring the cache.")
    args = parser.parse_args()

    if args.pregenerate:
        return pregenerate()
    return play(live=args.live)


if __name__ == "__main__":
    raise SystemExit(main())
