"""Client for a local OpenAI-compatible vision server (LM Studio by default).

Nothing in this module talks to the network beyond the configured local
endpoint, which is the only place repository content is ever sent.
"""

from __future__ import annotations

import base64
import io
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

import httpx

from .config import Config, load_config
from .quality import strip_think

#: Model used when nothing else is configured. Override with ``ALTFIX_MODEL``.
DEFAULT_MODEL = "qwen3.5-9b"


class ModelUnavailable(RuntimeError):
    """Raised when the local model endpoint cannot be reached."""


@dataclass
class ModelResponse:
    """A single completion from the local server."""

    text: str
    model: str
    prompt_tokens: Optional[int] = None
    completion_tokens: Optional[int] = None
    raw: Optional[dict[str, Any]] = None


def encode_image(path: str | Path, max_dimension: int = 1024, quality: int = 85) -> str:
    """Return a base64 JPEG data URL for the image at *path*.

    Large images are downscaled first so the request stays small and fast.
    """
    from PIL import Image

    with Image.open(path) as img:
        image = img.convert("RGB")
        width, height = image.size
        if max(width, height) > max_dimension:
            scale = max_dimension / max(width, height)
            new_size = (max(1, int(width * scale)), max(1, int(height * scale)))
            image = image.resize(new_size, Image.Resampling.LANCZOS)
        buffer = io.BytesIO()
        image.save(buffer, format="JPEG", quality=quality)

    encoded = base64.b64encode(buffer.getvalue()).decode("ascii")
    return f"data:image/jpeg;base64,{encoded}"


class LocalVisionClient:
    """Thin wrapper around the OpenAI-compatible chat completions API."""

    def __init__(self, config: Optional[Config] = None, **overrides: Any) -> None:
        self.config = config or load_config(**overrides)

    # -- introspection ----------------------------------------------------
    def list_models(self) -> list[str]:
        """Return the model ids the local server exposes."""
        try:
            response = httpx.get(self.config.models_url, timeout=10.0)
            response.raise_for_status()
            payload = response.json()
        except Exception as exc:  # noqa: BLE001 - surfaced with context
            raise ModelUnavailable(
                f"Could not reach the model server at {self.config.base_url}: {exc}"
            ) from exc
        return [entry.get("id", "") for entry in payload.get("data", [])]

    def is_available(self) -> bool:
        """True when the server answers the models endpoint."""
        try:
            self.list_models()
        except ModelUnavailable:
            return False
        return True

    def server_diagnostics(self) -> str:
        """Human readable status of the configured endpoint."""
        try:
            models = self.list_models()
        except ModelUnavailable as exc:
            return str(exc)
        if not models:
            return f"Server at {self.config.base_url} exposes no models."
        return f"Server at {self.config.base_url} exposes: {', '.join(models)}"

    # -- completion --------------------------------------------------------
    def describe(
        self,
        image_path: str | Path,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: Optional[int] = None,
    ) -> ModelResponse:
        """Send one image plus *prompt* to the local model and return the reply.

        Raises:
            ModelUnavailable: when the endpoint is unreachable or errors out.
        """
        data_url = encode_image(image_path, max_dimension=self.config.max_image_dim)

        content: list[dict[str, Any]] = [
            {"type": "text", "text": prompt},
            {"type": "image_url", "image_url": {"url": data_url}},
        ]
        messages: list[dict[str, Any]] = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": content})

        payload: dict[str, Any] = {
            "model": self.config.model,
            "messages": messages,
            "max_tokens": max_tokens or self.config.max_tokens,
            "temperature": self.config.temperature,
            "stream": False,
        }
        if self.config.seed is not None:
            payload["seed"] = self.config.seed
        if self.config.reasoning_effort:
            payload["reasoning_effort"] = self.config.reasoning_effort

        try:
            response = httpx.post(
                self.config.chat_url,
                json=payload,
                timeout=self.config.timeout,
            )
        except Exception as exc:  # noqa: BLE001 - surfaced with context
            raise ModelUnavailable(
                f"Request to {self.config.chat_url} failed: {exc}"
            ) from exc

        if response.status_code == 400 and payload.get("reasoning_effort"):
            # The server does not understand reasoning_effort. Retry without it.
            payload.pop("reasoning_effort", None)
            try:
                response = httpx.post(
                    self.config.chat_url,
                    json=payload,
                    timeout=self.config.timeout,
                )
            except Exception as exc:  # noqa: BLE001
                raise ModelUnavailable(
                    f"Request to {self.config.chat_url} failed: {exc}"
                ) from exc

        if response.status_code != 200:
            raise ModelUnavailable(
                f"Model server returned {response.status_code}: {response.text[:400]}"
            )

        try:
            data = response.json()
        except ValueError as exc:
            raise ModelUnavailable(f"Model server returned invalid JSON: {exc}") from exc

        choices = data.get("choices") or []
        if not choices:
            raise ModelUnavailable("Model server returned no choices.")

        message = choices[0].get("message") or {}
        text = message.get("content") or ""
        if isinstance(text, list):
            # Some servers return content parts.
            text = "".join(part.get("text", "") for part in text if isinstance(part, dict))
        if not text:
            # Reasoning-only responses: fall back to the reasoning field.
            text = message.get("reasoning_content") or ""

        usage = data.get("usage") or {}
        return ModelResponse(
            text=strip_think(text),
            model=data.get("model", self.config.model),
            prompt_tokens=usage.get("prompt_tokens"),
            completion_tokens=usage.get("completion_tokens"),
            raw=data,
        )


# Backwards compatible alias.
OllamaVisionClient = LocalVisionClient
