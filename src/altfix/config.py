"""Runtime configuration for AltFix.

Values are resolved in this order (last wins):

1. Built-in defaults
2. Config file (``altfix.toml`` / ``.altfix.toml`` / ``~/.altfix.toml`` or
   ``$ALTFIX_CONFIG``)
3. Environment variables (``ALTFIX_*``)

The model backend is a local OpenAI-compatible server (LM Studio by default).
Nothing here is specific to one machine: every value can be overridden.
"""

from __future__ import annotations

import os
import tomllib
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Optional

DEFAULT_BASE_URL = "http://localhost:1234/v1"
DEFAULT_MODEL = "qwen3.5-9b"
DEFAULT_TEMPERATURE = 0.2
DEFAULT_SEED = 42
DEFAULT_MAX_TOKENS = 200
DEFAULT_MAX_IMAGE_DIM = 1024
DEFAULT_TIMEOUT = 180.0
DEFAULT_CONTEXT_LENGTH = 4096
DEFAULT_PROMPT_VERSION = "v1"
DEFAULT_CACHE_DIR = ".altfix-cache"

CONFIG_FILENAMES = ("altfix.toml", ".altfix.toml")


@dataclass
class Config:
    """Everything AltFix needs to talk to the local model and store results."""

    base_url: str = DEFAULT_BASE_URL
    model: str = DEFAULT_MODEL
    quantization: str = ""
    temperature: float = DEFAULT_TEMPERATURE
    seed: int = DEFAULT_SEED
    max_tokens: int = DEFAULT_MAX_TOKENS
    max_image_dim: int = DEFAULT_MAX_IMAGE_DIM
    timeout: float = DEFAULT_TIMEOUT
    context_length: int = DEFAULT_CONTEXT_LENGTH
    prompt_version: str = DEFAULT_PROMPT_VERSION
    cache_dir: str = DEFAULT_CACHE_DIR
    max_alt_length: int = 125

    @property
    def chat_url(self) -> str:
        """Full URL of the chat completions endpoint."""
        return self.base_url.rstrip("/") + "/chat/completions"

    @property
    def models_url(self) -> str:
        """Full URL of the models endpoint."""
        return self.base_url.rstrip("/") + "/models"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _find_config_file(explicit: Optional[str] = None) -> Optional[Path]:
    """Locate the TOML config file, if any."""
    if explicit:
        path = Path(explicit).expanduser()
        return path if path.is_file() else None
    env = os.environ.get("ALTFIX_CONFIG")
    if env:
        path = Path(env).expanduser()
        if path.is_file():
            return path
    candidates = [Path.cwd() / name for name in CONFIG_FILENAMES]
    candidates.append(Path.home() / ".altfix.toml")
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    return None


def _read_config_file(path: Optional[Path]) -> dict[str, Any]:
    if path is None:
        return {}
    try:
        with open(path, "rb") as handle:
            data = tomllib.load(handle)
    except (OSError, tomllib.TOMLDecodeError):
        return {}
    section = data.get("altfix")
    if isinstance(section, dict):
        return section
    return {k: v for k, v in data.items() if isinstance(v, (str, int, float, bool))}


def _as_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def load_config(config_file: Optional[str] = None, **overrides: Any) -> Config:
    """Build a :class:`Config` from file, environment and explicit overrides."""
    values: dict[str, Any] = {}

    file_values = _read_config_file(_find_config_file(config_file))
    for key, value in file_values.items():
        if key in Config.__dataclass_fields__:
            values[key] = value

    env_map = {
        "ALTFIX_BASE_URL": "base_url",
        "ALTFIX_MODEL": "model",
        "ALTFIX_QUANT": "quantization",
        "ALTFIX_TEMPERATURE": "temperature",
        "ALTFIX_SEED": "seed",
        "ALTFIX_MAX_TOKENS": "max_tokens",
        "ALTFIX_MAX_IMAGE_DIM": "max_image_dim",
        "ALTFIX_TIMEOUT": "timeout",
        "ALTFIX_CONTEXT_LENGTH": "context_length",
        "ALTFIX_PROMPT_VERSION": "prompt_version",
        "ALTFIX_CACHE_DIR": "cache_dir",
        "ALTFIX_MAX_ALT_LENGTH": "max_alt_length",
    }
    for env_name, field_name in env_map.items():
        raw = os.environ.get(env_name)
        if raw is None or raw == "":
            continue
        current = getattr(Config(), field_name)
        if isinstance(current, bool):
            values[field_name] = _as_bool(raw)
        elif isinstance(current, int):
            values[field_name] = int(raw)
        elif isinstance(current, float):
            values[field_name] = float(raw)
        else:
            values[field_name] = raw

    for key, value in overrides.items():
        if value is not None and key in Config.__dataclass_fields__:
            values[key] = value

    config = Config(**values)
    return config
