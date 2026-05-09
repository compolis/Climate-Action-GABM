"""Tests for the local OpenAI-compatible LLM provider in cag.io.llm.

These tests do not require a live local server: the OpenAI SDK call inside
``_send_local`` is mocked. Higher-level behaviour (registry lookup, base-URL
resolution, retry logic, api-key short-circuit) is exercised end-to-end.
"""

import os
import sys
from unittest import mock

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from cag.io import llm as llm_module
from cag.io.llm import (
    _LOCAL_CONFIG,
    _resolve_local_base_url,
    _resolve_local_timeout,
    _resolve_model_profile,
    configure_local,
    load_api_key,
    send_chat,
)


@pytest.fixture(autouse=True)
def _reset_local_config(monkeypatch):
    """Reset module-level local config and unknown-model cache between tests."""
    saved = dict(_LOCAL_CONFIG)
    _LOCAL_CONFIG["base_url"] = None
    _LOCAL_CONFIG["extra_body"] = None
    _LOCAL_CONFIG["timeout_s"] = None
    monkeypatch.delenv("CAG_LOCAL_BASE_URL", raising=False)
    monkeypatch.delenv("CAG_LOCAL_TIMEOUT_S", raising=False)
    llm_module._LOGGED_UNKNOWN_LOCAL_MODELS.clear()
    yield
    _LOCAL_CONFIG.update(saved)


# ===================================================================
# load_api_key short-circuit
# ===================================================================

class TestLoadApiKeyLocal:

    def test_returns_sentinel_without_csv_or_env(self, tmp_path, monkeypatch):
        # No CSV, no env var: load_api_key("local") still returns "not-needed".
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        assert load_api_key("local", csv_path=tmp_path / "missing.csv") == "not-needed"

    def test_case_insensitive(self, tmp_path):
        assert load_api_key("LOCAL", csv_path=tmp_path / "missing.csv") == "not-needed"


# ===================================================================
# Base URL / timeout resolution
# ===================================================================

class TestBaseUrlResolution:

    def test_default_when_unset(self):
        assert _resolve_local_base_url() == "http://localhost:8080/v1"

    def test_env_var_override(self, monkeypatch):
        monkeypatch.setenv("CAG_LOCAL_BASE_URL", "http://hpc-node-7:9000/v1")
        assert _resolve_local_base_url() == "http://hpc-node-7:9000/v1"

    def test_configure_local_overrides_env(self, monkeypatch):
        monkeypatch.setenv("CAG_LOCAL_BASE_URL", "http://env-host/v1")
        configure_local(base_url="http://config-host/v1")
        assert _resolve_local_base_url() == "http://config-host/v1"

    def test_timeout_default(self):
        assert _resolve_local_timeout() == 600.0

    def test_timeout_env(self, monkeypatch):
        monkeypatch.setenv("CAG_LOCAL_TIMEOUT_S", "120")
        assert _resolve_local_timeout() == 120.0

    def test_timeout_configure(self):
        configure_local(timeout_s=42)
        assert _resolve_local_timeout() == 42.0


# ===================================================================
# Model registry
# ===================================================================

class TestModelRegistry:

    def test_qwen3_match(self):
        prof = _resolve_model_profile("mlx-community/Qwen3-8B-4bit")
        assert prof["match"] == "qwen3"
        assert "thinking_extra_body" in prof
        body_thk = prof["thinking_extra_body"](True)
        assert body_thk["chat_template_kwargs"]["enable_thinking"] is True
        body_no = prof["thinking_extra_body"](False)
        assert body_no["chat_template_kwargs"]["enable_thinking"] is False

    def test_llama_match(self):
        prof = _resolve_model_profile("mlx-community/Llama-3.2-3B-Instruct-4bit")
        assert prof["match"] == "llama"
        assert "thinking_extra_body" not in prof

    def test_mistral_match(self):
        assert _resolve_model_profile("mistral-7b-instruct")["match"] == "mistral"

    def test_apertus_match(self):
        assert _resolve_model_profile("apertus-8b")["match"] == "apertus"

    def test_unknown_returns_empty(self):
        assert _resolve_model_profile("totally-novel-model") == {}

    def test_empty_model_returns_empty(self):
        assert _resolve_model_profile("") == {}
        assert _resolve_model_profile(None) == {}


# ===================================================================
# _send_local — dispatch & registry application
# ===================================================================

def _fake_openai_factory(captured):
    """Return a FakeOpenAI class that records every call into ``captured``."""

    class _Choice:
        def __init__(self, content):
            self.message = mock.Mock(content=content)

    class _Resp:
        def __init__(self, content):
            self.choices = [_Choice(content)]

    class _Completions:
        def __init__(self, content_factory):
            self._content_factory = content_factory

        def create(self, **kwargs):
            captured.append(kwargs)
            return _Resp(self._content_factory(kwargs, len(captured)))

    class _Chat:
        def __init__(self, content_factory):
            self.completions = _Completions(content_factory)

    class FakeOpenAI:
        last_init_kwargs = None

        def __init__(self, **kwargs):
            FakeOpenAI.last_init_kwargs = kwargs
            # Default content: non-empty echo
            self.chat = _Chat(getattr(FakeOpenAI, "_content_factory",
                                       lambda kw, n: "ok"))

    return FakeOpenAI


class TestSendLocalDispatch:

    def test_dispatcher_routes_to_local(self):
        captured = []
        FakeOpenAI = _fake_openai_factory(captured)
        with mock.patch("openai.OpenAI", FakeOpenAI):
            out = send_chat("sys", "user", model="some-model", provider="local",
                            temperature=0.3, thinking=False)
        assert out == "ok"
        assert len(captured) == 1
        assert captured[0]["model"] == "some-model"
        assert captured[0]["messages"] == [
            {"role": "system", "content": "sys"},
            {"role": "user", "content": "user"},
        ]

    def test_dispatcher_passes_api_key_not_needed(self):
        captured = []
        FakeOpenAI = _fake_openai_factory(captured)
        with mock.patch("openai.OpenAI", FakeOpenAI):
            send_chat("s", "u", model="any-model", provider="local")
        assert FakeOpenAI.last_init_kwargs["api_key"] == "not-needed"

    def test_base_url_passed_to_client(self):
        captured = []
        FakeOpenAI = _fake_openai_factory(captured)
        configure_local(base_url="http://my-server:1234/v1")
        with mock.patch("openai.OpenAI", FakeOpenAI):
            send_chat("s", "u", model="any-model", provider="local")
        assert FakeOpenAI.last_init_kwargs["base_url"] == "http://my-server:1234/v1"

    def test_timeout_passed_to_client(self):
        captured = []
        FakeOpenAI = _fake_openai_factory(captured)
        configure_local(timeout_s=42)
        with mock.patch("openai.OpenAI", FakeOpenAI):
            send_chat("s", "u", model="any-model", provider="local")
        assert FakeOpenAI.last_init_kwargs["timeout"] == 42.0


class TestRegistryInjection:

    def test_qwen3_thinking_on_injects_extra_body(self):
        captured = []
        FakeOpenAI = _fake_openai_factory(captured)
        with mock.patch("openai.OpenAI", FakeOpenAI):
            send_chat("s", "u", model="mlx-community/Qwen3-8B-4bit",
                      provider="local", thinking=True)
        eb = captured[0]["extra_body"]
        assert eb["chat_template_kwargs"]["enable_thinking"] is True
        # Sampling preset for thinking-mode Qwen3.
        assert captured[0]["temperature"] == 0.6
        assert captured[0]["top_p"] == 0.95
        assert captured[0]["max_tokens"] == 16384

    def test_qwen3_thinking_off_injects_extra_body(self):
        captured = []
        FakeOpenAI = _fake_openai_factory(captured)
        with mock.patch("openai.OpenAI", FakeOpenAI):
            send_chat("s", "u", model="mlx-community/Qwen3-8B-4bit",
                      provider="local", thinking=False)
        eb = captured[0]["extra_body"]
        assert eb["chat_template_kwargs"]["enable_thinking"] is False
        assert captured[0]["temperature"] == 0.7
        assert captured[0]["top_p"] == 0.8
        assert captured[0]["max_tokens"] == 2048

    def test_llama_no_extra_body(self):
        captured = []
        FakeOpenAI = _fake_openai_factory(captured)
        with mock.patch("openai.OpenAI", FakeOpenAI):
            send_chat("s", "u", model="mlx-community/Llama-3.2-3B-Instruct-4bit",
                      provider="local", thinking=False)
        # Llama profile defines no extra_body, so the kwarg should be absent.
        assert "extra_body" not in captured[0]
        assert captured[0]["temperature"] == 0.7
        assert captured[0]["top_p"] == 0.9

    def test_unknown_model_uses_caller_temperature(self):
        captured = []
        FakeOpenAI = _fake_openai_factory(captured)
        with mock.patch("openai.OpenAI", FakeOpenAI):
            send_chat("s", "u", model="brand-new-model",
                      provider="local", temperature=0.42)
        assert captured[0]["temperature"] == 0.42
        # Default token cap for non-thinking calls.
        assert captured[0]["max_tokens"] == 2048
        assert "extra_body" not in captured[0]

    def test_user_extra_body_overrides_registry(self):
        captured = []
        FakeOpenAI = _fake_openai_factory(captured)
        configure_local(extra_body={"chat_template_kwargs": {"enable_thinking": False}})
        with mock.patch("openai.OpenAI", FakeOpenAI):
            send_chat("s", "u", model="mlx-community/Qwen3-8B-4bit",
                      provider="local", thinking=True)
        # User override should win over the registry's thinking=True injection.
        assert captured[0]["extra_body"]["chat_template_kwargs"]["enable_thinking"] is False


class TestThinkingRetry:

    def test_empty_thinking_content_triggers_retry_without_thinking(self):
        captured = []
        FakeOpenAI = _fake_openai_factory(captured)
        # First call returns "" (truncated reasoning), retry returns "ok".
        FakeOpenAI._content_factory = lambda kw, n: "" if n == 1 else "ok"
        with mock.patch("openai.OpenAI", FakeOpenAI):
            out = send_chat("s", "u", model="mlx-community/Qwen3-8B-4bit",
                            provider="local", thinking=True)
        assert out == "ok"
        assert len(captured) == 2
        # Retry should have flipped enable_thinking to False.
        assert captured[1]["extra_body"]["chat_template_kwargs"]["enable_thinking"] is False
        # Retry uses the non-thinking sampling preset and token cap.
        assert captured[1]["temperature"] == 0.7
        assert captured[1]["max_tokens"] == 2048

    def test_empty_non_thinking_content_does_not_retry(self):
        captured = []
        FakeOpenAI = _fake_openai_factory(captured)
        FakeOpenAI._content_factory = lambda kw, n: ""
        with mock.patch("openai.OpenAI", FakeOpenAI):
            out = send_chat("s", "u", model="any-model",
                            provider="local", thinking=False)
        assert out == ""
        assert len(captured) == 1


class TestUnsupportedProvider:

    def test_unsupported_provider_lists_local(self):
        with pytest.raises(ValueError, match="local"):
            send_chat("s", "u", model="x", provider="bogus", api_key="x")
