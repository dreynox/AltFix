"""Content-addressed cache for model descriptions.

The cache key mixes every input that can change the answer:

* model id
* prompt version
* hash of the image bytes
* hash of the surrounding document context

Every cached record stores the model id and prompt version alongside the
description, so a stale cache can never masquerade as a fresh result.
"""

from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional


def hash_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def hash_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def hash_file(path: str | Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


@dataclass
class CacheStats:
    """Hit/miss counters for one run."""

    hits: int = 0
    misses: int = 0
    writes: int = 0

    @property
    def requests(self) -> int:
        return self.hits + self.misses

    @property
    def hit_rate(self) -> float:
        if self.requests == 0:
            return 0.0
        return self.hits / self.requests


class DescriptionCache:
    """Filesystem cache storing one JSON document per (model, prompt, image, context)."""

    def __init__(self, cache_dir: str | Path, enabled: bool = True) -> None:
        self.dir = Path(cache_dir).expanduser()
        self.enabled = enabled
        self.stats = CacheStats()
        if self.enabled:
            self.dir.mkdir(parents=True, exist_ok=True)

    def key(
        self,
        model: str,
        prompt_version: str,
        image_hash: str,
        context_hash: str,
    ) -> str:
        raw = "|".join([model, prompt_version, image_hash, context_hash])
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    def _path(self, key: str) -> Path:
        return self.dir / f"{key}.json"

    def get(self, key: str) -> Optional[dict[str, Any]]:
        if not self.enabled:
            return None
        path = self._path(key)
        if not path.is_file():
            self.stats.misses += 1
            return None
        try:
            with open(path, "r", encoding="utf-8") as handle:
                record = json.load(handle)
        except (OSError, json.JSONDecodeError):
            self.stats.misses += 1
            return None
        self.stats.hits += 1
        return record

    def put(self, key: str, record: dict[str, Any]) -> None:
        if not self.enabled:
            return
        record = dict(record)
        record.setdefault("created_at", time.time())
        path = self._path(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".tmp")
        with open(tmp, "w", encoding="utf-8") as handle:
            json.dump(record, handle, ensure_ascii=False, indent=2, sort_keys=True)
        tmp.replace(path)
        self.stats.writes += 1
