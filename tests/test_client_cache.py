"""Tests for the config, cache and model client layers.

The model client is exercised against a stubbed HTTP transport, so these
tests never need a running LM Studio instance.
"""

from __future__ import annotations

import json

import httpx
import pytest

from altfix.cache import DescriptionCache, hash_file, hash_text
from altfix.client import LocalVisionClient, ModelUnavailable, encode_image
from altfix.config import Config, load_config
from altfix.describe import Describer
from altfix.scan import scan_text


def make_client(handler, **overrides):
    config = Config(**overrides)
    client = LocalVisionClient(config)
    client._transport = httpx.MockTransport(handler)
    return client


class TestConfig:
    def test_defaults(self):
        config = load_config()
        assert config.base_url == "http://localhost:1234/v1"
        assert config.chat_url == "http://localhost:1234/v1/chat/completions"
        assert config.models_url == "http://localhost:1234/v1/models"

    def test_env_overrides(self, monkeypatch):
        monkeypatch.setenv("ALTFIX_BASE_URL", "http://example.test/v1")
        monkeypatch.setenv("ALTFIX_MODEL", "some-other-model")
        monkeypatch.setenv("ALTFIX_QUANT", "Q4_K_M")
        config = load_config()
        assert config.base_url == "http://example.test/v1"
        assert config.model == "some-other-model"
        assert config.quantization == "Q4_K_M"

    def test_explicit_override_beats_env(self, monkeypatch):
        monkeypatch.setenv("ALTFIX_MODEL", "env-model")
        config = load_config(model="explicit-model")
        assert config.model == "explicit-model"

    def test_config_file(self, tmp_path, monkeypatch):
        monkeypatch.delenv("ALTFIX_MODEL", raising=False)
        config_file = tmp_path / "altfix.toml"
        config_file.write_text(
            '[altfix]\nmodel = "file-model"\nbase_url = "http://file.test/v1"\n',
            encoding="utf-8",
        )
        config = load_config(config_file=str(config_file))
        assert config.model == "file-model"
        assert config.base_url == "http://file.test/v1"

    def test_chat_url_normalises_trailing_slash(self):
        config = Config(base_url="http://localhost:1234/v1/")
        assert config.chat_url == "http://localhost:1234/v1/chat/completions"


class TestCache:
    def test_key_includes_all_inputs(self):
        cache = DescriptionCache(".cache", enabled=False)
        base = cache.key("m1", "v1", "img", "ctx")
        assert base != cache.key("m2", "v1", "img", "ctx")
        assert base != cache.key("m1", "v2", "img", "ctx")
        assert base != cache.key("m1", "v1", "img2", "ctx")
        assert base != cache.key("m1", "v1", "img", "ctx2")

    def test_roundtrip(self, tmp_path):
        cache = DescriptionCache(tmp_path / "c")
        key = cache.key("m", "v", "i", "c")
        cache.put(key, {"text": "hello", "model": "m"})
        record = cache.get(key)
        assert record["text"] == "hello"
        assert record["model"] == "m"
        assert "created_at" in record

    def test_miss_counts(self, tmp_path):
        cache = DescriptionCache(tmp_path / "c")
        assert cache.get("nope") is None
        assert cache.stats.misses == 1
        assert cache.stats.hits == 0

    def test_hit_rate(self, tmp_path):
        cache = DescriptionCache(tmp_path / "c")
        key = cache.key("m", "v", "i", "c")
        cache.put(key, {"text": "x"})
        cache.get(key)
        cache.get("missing")
        assert cache.stats.hits == 1
        assert cache.stats.misses == 1
        assert cache.stats.hit_rate == 0.5

    def test_disabled_cache_never_stores(self, tmp_path):
        cache = DescriptionCache(tmp_path / "c", enabled=False)
        key = cache.key("m", "v", "i", "c")
        cache.put(key, {"text": "x"})
        assert cache.get(key) is None

    def test_hashes(self, tmp_path):
        path = tmp_path / "a.bin"
        path.write_bytes(b"hello")
        assert hash_file(path) == hash_file(path)
        assert hash_text("a") != hash_text("b")


class TestClient:
    def test_encode_image_returns_data_url(self, sample_image):
        url = encode_image(sample_image)
        assert url.startswith("data:image/jpeg;base64,")

    def test_large_image_is_resized(self, tmp_path):
        from PIL import Image

        path = tmp_path / "big.png"
        Image.new("RGB", (3000, 2000)).save(path)
        url = encode_image(path, max_dimension=100)
        assert url.startswith("data:image/jpeg;base64,")

    def test_describe_sends_image_and_returns_text(self, sample_image):
        captured = {}

        def handler(request: httpx.Request) -> httpx.Response:
            captured["url"] = str(request.url)
            captured["body"] = json.loads(request.content)
            return httpx.Response(
                200,
                json={
                    "model": "qwen3.5-9b",
                    "choices": [{"message": {"content": "A red rectangle."}}],
                    "usage": {"prompt_tokens": 10, "completion_tokens": 5},
                },
            )

        client = make_client(handler, base_url="http://localhost:1234/v1")
        client._httpx_client = httpx.Client(transport=httpx.MockTransport(handler))

        # Patch the module-level httpx.post used by the client.
        import altfix.client as client_module

        original_post = httpx.post
        httpx.post = lambda *a, **k: httpx.Client(transport=httpx.MockTransport(handler)).post(*a, **k)
        try:
            response = client.describe(sample_image, "Describe it")
        finally:
            httpx.post = original_post

        assert captured["url"] == "http://localhost:1234/v1/chat/completions"
        body = captured["body"]
        assert body["model"] == "qwen3.5-9b"
        assert body["max_tokens"] > 0
        parts = body["messages"][-1]["content"]
        assert parts[0]["type"] == "text"
        assert parts[1]["type"] == "image_url"
        assert parts[1]["image_url"]["url"].startswith("data:image/jpeg;base64,")
        assert response.text == "A red rectangle."
        assert response.completion_tokens == 5

    def test_describe_raises_on_http_error(self, sample_image):
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(500, text="boom")

        import altfix.client as client_module

        original_post = httpx.post
        httpx.post = lambda *a, **k: httpx.Client(transport=httpx.MockTransport(handler)).post(*a, **k)
        try:
            client = make_client(handler)
            with pytest.raises(ModelUnavailable):
                client.describe(sample_image, "Describe it")
        finally:
            httpx.post = original_post

    def test_think_block_is_stripped(self, sample_image):
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(
                200,
                json={"choices": [{"message": {"content": "<think>reason</think>Answer."}}]},
            )

        import altfix.client as client_module

        original_post = httpx.post
        httpx.post = lambda *a, **k: httpx.Client(transport=httpx.MockTransport(handler)).post(*a, **k)
        try:
            client = make_client(handler)
            response = client.describe(sample_image, "Describe it")
        finally:
            httpx.post = original_post
        assert response.text == "Answer."

    def test_list_models(self):
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json={"data": [{"id": "qwen3.5-9b"}]})

        import altfix.client as client_module

        original_get = httpx.get
        httpx.get = lambda *a, **k: httpx.Client(transport=httpx.MockTransport(handler)).get(*a, **k)
        try:
            client = make_client(handler)
            assert client.list_models() == ["qwen3.5-9b"]
        finally:
            httpx.get = original_get


class TestDescriber:
    def test_describe_uses_cache_on_second_call(self, tmp_path, sample_image, monkeypatch):
        calls = {"n": 0}

        class FakeClient:
            config = Config(model="m", prompt_version="v1", cache_dir=str(tmp_path / "c"))

            def describe(self, path, prompt, system_prompt=None):
                calls["n"] += 1
                from altfix.client import ModelResponse

                return ModelResponse(text="A solid red rectangle.", model="m")

        occurrence = scan_text("![](a.png)", "d.md", "markdown").images[0]
        describer = Describer(
            config=FakeClient.config,
            client=FakeClient(),
            cache=DescriptionCache(tmp_path / "c"),
        )
        first = describer.describe(sample_image, occurrence)
        second = describer.describe(sample_image, occurrence)
        assert first.ok and not first.cached
        assert second.ok and second.cached
        assert calls["n"] == 1

    def test_needs_review_when_quality_fails(self, tmp_path, sample_image):
        class FakeClient:
            config = Config(model="m", prompt_version="v1", cache_dir=str(tmp_path / "c"))

            def __init__(self):
                self.n = 0

            def describe(self, path, prompt, system_prompt=None):
                from altfix.client import ModelResponse

                self.n += 1
                return ModelResponse(text="image", model="m")

        fake = FakeClient()
        occurrence = scan_text("![](a.png)", "d.md", "markdown").images[0]
        describer = Describer(
            config=fake.config,
            client=fake,
            cache=DescriptionCache(tmp_path / "c"),
        )
        result = describer.describe(sample_image, occurrence)
        assert not result.ok
        assert result.text == "[needs review]"
        assert fake.n == 2  # one retry with the stricter prompt

    def test_model_unavailable_is_not_fatal(self, tmp_path, sample_image):
        from altfix.client import ModelUnavailable

        class FakeClient:
            config = Config(model="m", prompt_version="v1", cache_dir=str(tmp_path / "c"))

            def describe(self, path, prompt, system_prompt=None):
                raise ModelUnavailable("server down")

        occurrence = scan_text("![](a.png)", "d.md", "markdown").images[0]
        describer = Describer(
            config=FakeClient.config,
            client=FakeClient(),
            cache=DescriptionCache(tmp_path / "c"),
        )
        result = describer.describe(sample_image, occurrence)
        assert not result.ok
        assert result.reason == "model_unavailable"
        assert "server down" in result.error
