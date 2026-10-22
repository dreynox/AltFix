"""Turn an image plus its surrounding context into a validated alt text.

The model is asked for a concise, objective description. The answer is then
run through the deterministic quality checks. If it fails, the model is
retried once with a stricter prompt. If it fails again the image is marked
``needs review`` - nothing is ever invented.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from .cache import DescriptionCache, hash_file, hash_text
from .client import LocalVisionClient, ModelUnavailable
from .config import Config, load_config
from .quality import MAX_ALT_LENGTH, NEEDS_REVIEW, check
from .scan import ImageOccurrence

SYSTEM_PROMPT = (
    "You are an accessibility specialist writing alt text for documentation images. "
    "You describe what is actually visible in the image. You never invent content "
    "and you never describe what the image is supposed to mean."
)

BASE_INSTRUCTIONS = """\
Write a single alt text for the image above.

Rules:
- Describe only what is visible in the image.
- Mention any readable text shown in a screenshot, quoted exactly.
- For a chart, state the trend and the key values, not the chart type alone.
- For a diagram, name the diagram type and the main components or actors.
- Be objective. Do not use the words "image of", "picture of" or "screenshot of".
- Do not mention the file name, the path, or that the image exists.
- Write one line of plain text, no markdown, no quotes, no trailing period.
- Keep it under {max_length} characters.
"""

STRICT_INSTRUCTIONS = """\
Your previous answer was unusable. Try again with a single plain-text line.

Rules:
- Start immediately with the subject of the image.
- Do not write "image of", "picture of", "screenshot of" or any similar phrase.
- Do not write the file name or path.
- Do not use markdown, quotes or a trailing period.
- If the image is a chart, name the trend and the values.
- If the image is a screenshot, quote the visible text.
- Keep it under {max_length} characters.
"""


@dataclass
class Description:
    """The outcome of describing one image."""

    text: str
    ok: bool
    reason: str = ""
    cached: bool = False
    attempts: int = 0
    latency_ms: float = 0.0
    model: str = ""
    prompt_version: str = ""
    image_hash: str = ""
    context_hash: str = ""
    error: str = ""
    context_used: dict[str, Optional[str]] = field(default_factory=dict)

    @property
    def needs_review(self) -> bool:
        return not self.ok


def build_context(occurrence: ImageOccurrence) -> str:
    """Assemble the document context handed to the model."""
    parts: list[str] = []
    if occurrence.context_heading:
        parts.append(f"Document section: {occurrence.context_heading}")
    if occurrence.context_caption:
        parts.append(f"Caption in the document: {occurrence.context_caption}")
    if occurrence.context_link:
        parts.append(f"Linked from: {occurrence.context_link}")
    if occurrence.context_before:
        parts.append(f"Text before the image: {occurrence.context_before}")
    if occurrence.context_after:
        parts.append(f"Text after the image: {occurrence.context_after}")
    if not parts:
        parts.append("The image appears in a documentation page with no surrounding text.")
    return "\n".join(parts)


class Describer:
    """Describes images with the local model, using the cache when possible."""

    def __init__(
        self,
        config: Optional[Config] = None,
        client: Optional[LocalVisionClient] = None,
        cache: Optional[DescriptionCache] = None,
        **overrides: object,
    ) -> None:
        self.config = config or load_config(**overrides)
        self.client = client or LocalVisionClient(self.config)
        self.cache = cache or DescriptionCache(self.config.cache_dir)

    def describe(
        self,
        image_path: str | Path,
        occurrence: ImageOccurrence,
        use_cache: bool = True,
    ) -> Description:
        """Describe the image at *image_path* using the context of *occurrence*."""
        context = build_context(occurrence)
        image_hash = hash_file(image_path)
        context_hash = hash_text(context)
        key = self.cache.key(
            self.config.model, self.config.prompt_version, image_hash, context_hash
        )

        if use_cache:
            cached = self.cache.get(key)
            if cached is not None:
                return Description(
                    text=cached.get("text", ""),
                    ok=bool(cached.get("ok", False)),
                    reason=cached.get("reason", ""),
                    cached=True,
                    attempts=cached.get("attempts", 0),
                    model=cached.get("model", self.config.model),
                    prompt_version=cached.get("prompt_version", self.config.prompt_version),
                    image_hash=image_hash,
                    context_hash=context_hash,
                    context_used=occurrence.__dict__ and {
                        "heading": occurrence.context_heading,
                        "before": occurrence.context_before,
                        "after": occurrence.context_after,
                    },
                )

        started = time.perf_counter()
        attempts = 0
        last_reason = ""
        last_text = ""

        prompts = [
            BASE_INSTRUCTIONS.format(max_length=self.config.max_alt_length) + "\n" + context,
            STRICT_INSTRUCTIONS.format(max_length=self.config.max_alt_length) + "\n" + context,
        ]

        for prompt in prompts:
            attempts += 1
            try:
                response = self.client.describe(
                    image_path, prompt, system_prompt=SYSTEM_PROMPT
                )
            except ModelUnavailable as exc:
                return Description(
                    text=NEEDS_REVIEW,
                    ok=False,
                    reason="model_unavailable",
                    error=str(exc),
                    attempts=attempts,
                    latency_ms=(time.perf_counter() - started) * 1000,
                    model=self.config.model,
                    prompt_version=self.config.prompt_version,
                    image_hash=image_hash,
                    context_hash=context_hash,
                )

            result = check(response.text, occurrence.src, self.config.max_alt_length)
            last_text = result.text
            last_reason = result.reason
            if result.ok:
                latency = (time.perf_counter() - started) * 1000
                description = Description(
                    text=result.text,
                    ok=True,
                    reason=result.reason,
                    attempts=attempts,
                    latency_ms=latency,
                    model=self.config.model,
                    prompt_version=self.config.prompt_version,
                    image_hash=image_hash,
                    context_hash=context_hash,
                )
                self.cache.put(
                    key,
                    {
                        "text": result.text,
                        "ok": True,
                        "reason": result.reason,
                        "attempts": attempts,
                        "model": self.config.model,
                        "prompt_version": self.config.prompt_version,
                        "image_hash": image_hash,
                        "context_hash": context_hash,
                        "src": occurrence.src,
                    },
                )
                return description

        latency = (time.perf_counter() - started) * 1000
        return Description(
            text=NEEDS_REVIEW,
            ok=False,
            reason=last_reason or "failed_quality_checks",
            attempts=attempts,
            latency_ms=latency,
            model=self.config.model,
            prompt_version=self.config.prompt_version,
            image_hash=image_hash,
            context_hash=context_hash,
        )
