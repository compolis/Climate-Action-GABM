"""Tests for cag.io.llm module."""

import csv
import os
from unittest import mock

import pytest

import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from cag.io.llm import load_api_key, parse_letter_response, send_chat


# ===================================================================
# parse_letter_response
# ===================================================================

class TestParseLetterResponse:

    def test_just_letter(self):
        assert parse_letter_response("G") == "G"

    def test_letter_with_period(self):
        assert parse_letter_response("B.") == "B"

    def test_letter_with_comma(self):
        assert parse_letter_response("B,") == "B"

    def test_letter_with_explanation_dash(self):
        assert parse_letter_response("I would choose B - Somewhat oppose") == "B"

    def test_letter_with_explanation_values(self):
        assert parse_letter_response("Based on my values, E.") == "E"

    def test_letter_at_start_with_explanation(self):
        assert parse_letter_response("E. I slightly support...") == "E"

    def test_letter_with_newline(self):
        assert parse_letter_response("G\n\nI strongly support...") == "G"

    def test_lowercase_letter(self):
        assert parse_letter_response("b") == "B"

    def test_letter_with_leading_whitespace(self):
        assert parse_letter_response("  A  ") == "A"

    def test_answer_is_pattern(self):
        assert parse_letter_response("My answer is C") == "C"

    def test_no_valid_letter(self):
        with pytest.raises(ValueError):
            parse_letter_response("I'm not sure")

    def test_empty_string(self):
        with pytest.raises(ValueError):
            parse_letter_response("")

    def test_whitespace_only(self):
        with pytest.raises(ValueError):
            parse_letter_response("   ")

    def test_letter_outside_range(self):
        with pytest.raises(ValueError):
            parse_letter_response("H")


# ===================================================================
# load_api_key
# ===================================================================

class TestLoadApiKey:

    def _write_csv(self, path, rows):
        with open(path, "w", newline="") as fh:
            writer = csv.writer(fh)
            for row in rows:
                writer.writerow(row)

    def test_reads_key_from_csv(self, tmp_path):
        csv_file = tmp_path / "keys.csv"
        self._write_csv(csv_file, [
            ["openai", "sk-test-123"],
            ["genai", "ai-test-456"],
        ])
        assert load_api_key("openai", csv_path=str(csv_file)) == "sk-test-123"
        assert load_api_key("genai", csv_path=str(csv_file)) == "ai-test-456"

    def test_case_insensitive_provider(self, tmp_path):
        csv_file = tmp_path / "keys.csv"
        self._write_csv(csv_file, [["OpenAI", "sk-test"]])
        assert load_api_key("openai", csv_path=str(csv_file)) == "sk-test"

    def test_falls_back_to_env_var(self, tmp_path):
        csv_file = tmp_path / "nonexistent.csv"
        with mock.patch.dict(os.environ, {"OPENAI_API_KEY": "env-key-123"}):
            assert load_api_key("openai", csv_path=str(csv_file)) == "env-key-123"

    def test_genai_env_var_fallback(self, tmp_path):
        csv_file = tmp_path / "nonexistent.csv"
        with mock.patch.dict(os.environ, {"GENAI_API_KEY": "genai-env-key"}):
            assert load_api_key("genai", csv_path=str(csv_file)) == "genai-env-key"

    def test_anthropic_env_var_fallback(self, tmp_path):
        csv_file = tmp_path / "nonexistent.csv"
        with mock.patch.dict(os.environ, {"ANTHROPIC_API_KEY": "anthropic-env-key"}):
            assert load_api_key("anthropic", csv_path=str(csv_file)) == "anthropic-env-key"

    def test_raises_when_no_key_found(self, tmp_path):
        csv_file = tmp_path / "empty.csv"
        self._write_csv(csv_file, [])
        with mock.patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ValueError, match="No API key found"):
                load_api_key("openai", csv_path=str(csv_file))

    def test_raises_for_unknown_provider_no_csv(self, tmp_path):
        csv_file = tmp_path / "nonexistent.csv"
        with mock.patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ValueError, match="No API key found"):
                load_api_key("unknown_provider", csv_path=str(csv_file))


# ===================================================================
# send_chat
# ===================================================================

class TestSendChat:

    def test_raises_for_unsupported_provider(self):
        with pytest.raises(ValueError, match="Unsupported provider"):
            send_chat("sys", "usr", api_key="key", model="model", provider="unsupported")

    @mock.patch("cag.io.llm._send_openai", return_value="Hello!")
    def test_openai_dispatch(self, mock_openai):
        result = send_chat("sys", "usr", api_key="key", model="gpt-4o-mini", provider="openai")
        assert result == "Hello!"
        mock_openai.assert_called_once_with("sys", "usr", "key", "gpt-4o-mini", 0.5, False)

    @mock.patch("cag.io.llm._send_genai", return_value="Hi from Gemini!")
    def test_genai_dispatch(self, mock_genai):
        result = send_chat("sys", "usr", api_key="key", model="gemini-2.0-flash", provider="genai")
        assert result == "Hi from Gemini!"
        mock_genai.assert_called_once_with("sys", "usr", "key", "gemini-2.0-flash", 0.5, False)

    @mock.patch("cag.io.llm._send_openai", return_value="warm")
    def test_temperature_passed(self, mock_openai):
        send_chat("sys", "usr", api_key="key", model="model", provider="openai", temperature=0.3)
        mock_openai.assert_called_once_with("sys", "usr", "key", "model", 0.3, False)

    @mock.patch("cag.io.llm._send_anthropic", return_value="Hello from Claude!")
    def test_anthropic_dispatch(self, mock_anthropic):
        result = send_chat("sys", "usr", api_key="key", model="claude-haiku-4-5", provider="anthropic")
        assert result == "Hello from Claude!"
        mock_anthropic.assert_called_once_with("sys", "usr", "key", "claude-haiku-4-5", 0.5, False)

    @mock.patch("cag.io.llm._send_openai", return_value="OPENAI")
    def test_provider_case_insensitive(self, mock_openai):
        result = send_chat("sys", "usr", api_key="key", model="model", provider="OpenAI")
        assert result == "OPENAI"

    @mock.patch("cag.io.llm.load_api_key", return_value="auto-loaded-key")
    @mock.patch("cag.io.llm._send_openai", return_value="auto key works")
    def test_auto_loads_api_key_when_none(self, mock_openai, mock_load_key):
        result = send_chat("sys", "usr", model="model", provider="openai")
        assert result == "auto key works"
        mock_load_key.assert_called_once_with("openai")
        mock_openai.assert_called_once_with("sys", "usr", "auto-loaded-key", "model", 0.5, False)

    @mock.patch("cag.io.llm._send_openai", return_value="thinking!")
    def test_thinking_passed(self, mock_openai):
        send_chat("sys", "usr", api_key="key", model="model", provider="openai", thinking=True)
        mock_openai.assert_called_once_with("sys", "usr", "key", "model", 0.5, True)


# ===================================================================
# _resilient_call
# ===================================================================

from cag.io.llm import _resilient_call, _extract_rejected_param


class TestExtractRejectedParam:
    """Unit tests for the error-message parser."""

    def test_openai_param_field(self):
        msg = ("Error code: 400 - {'error': {'message': \"Unsupported value: "
               "'temperature' does not support 0.5\", 'type': 'invalid_request_error', "
               "'param': 'temperature', 'code': 'unsupported_value'}}")
        assert _extract_rejected_param(msg) == "temperature"

    def test_openai_reasoning_effort(self):
        msg = ("Error code: 400 - {'error': {'message': \"Unexpected keyword argument: "
               "'reasoning_effort'\", 'type': 'invalid_request_error', "
               "'param': 'reasoning_effort', 'code': 'unsupported_value'}}")
        assert _extract_rejected_param(msg) == "reasoning_effort"

    def test_anthropic_thinking_not_supported(self):
        msg = "adaptive thinking is not supported on this model"
        assert _extract_rejected_param(msg) == "thinking"

    def test_anthropic_thinking_subkey(self):
        msg = "thinking.adaptive.budget_tokens: Extra inputs are not permitted"
        assert _extract_rejected_param(msg) == "thinking"

    def test_unknown_message_returns_none(self):
        assert _extract_rejected_param("Connection timed out") is None


class TestResilientCall:
    """Unit tests for the generic retry helper."""

    @pytest.fixture(autouse=True)
    def _clear_unsupported_cache(self):
        """Reset the (provider, model) → unsupported-params cache between tests."""
        from cag.io.llm import _KNOWN_UNSUPPORTED
        _KNOWN_UNSUPPORTED.clear()
        yield
        _KNOWN_UNSUPPORTED.clear()

    def test_success_on_first_try(self):
        fn = mock.Mock(return_value="ok")
        result = _resilient_call(fn, {"a": 1}, "Test")
        assert result == "ok"
        fn.assert_called_once_with(a=1)

    def test_strips_rejected_param_and_retries(self):
        """400 naming 'temperature' → strip it → retry succeeds."""
        fn = mock.Mock(side_effect=[
            Exception("400 - {'error': {'param': 'temperature', "
                      "'type': 'invalid_request_error'}}"),
            "ok",
        ])
        kwargs = {"model": "m", "temperature": 0.5}
        result = _resilient_call(fn, kwargs, "Test")
        assert result == "ok"
        assert "temperature" not in kwargs
        assert fn.call_count == 2

    def test_strips_two_params_sequentially(self):
        """Two params rejected in sequence → both stripped, third call succeeds."""
        fn = mock.Mock(side_effect=[
            Exception("400 - {'error': {'param': 'temperature', "
                      "'type': 'invalid_request_error'}}"),
            Exception("400 - {'error': {'param': 'reasoning_effort', "
                      "'type': 'invalid_request_error'}}"),
            "ok",
        ])
        kwargs = {"model": "m", "temperature": 0.5, "reasoning_effort": "medium"}
        result = _resilient_call(fn, kwargs, "Test")
        assert result == "ok"
        assert "temperature" not in kwargs
        assert "reasoning_effort" not in kwargs
        assert fn.call_count == 3

    def test_non_400_error_raises_immediately(self):
        """Auth / rate limit errors should not be retried."""
        fn = mock.Mock(side_effect=Exception("401 Unauthorized"))
        with pytest.raises(RuntimeError, match="Test API call failed"):
            _resilient_call(fn, {"a": 1}, "Test")
        fn.assert_called_once()

    def test_on_strip_callback_called(self):
        """Verify on_strip hook is invoked when a param is stripped."""
        fn = mock.Mock(side_effect=[
            Exception("400 - {'error': {'param': 'thinking', "
                      "'type': 'invalid_request_error'}}"),
            "ok",
        ])
        on_strip = mock.Mock()
        kwargs = {"thinking": {"type": "adaptive"}, "max_tokens": 16000}
        _resilient_call(fn, kwargs, "Test", on_strip=on_strip)
        on_strip.assert_called_once_with(kwargs, "thinking")

    def test_gives_up_after_max_retries(self):
        """If every retry also fails with 400, eventually raises."""
        fn = mock.Mock(side_effect=[
            Exception("400 - {'error': {'param': 'a', 'type': 'invalid_request_error'}}"),
            Exception("400 - {'error': {'param': 'b', 'type': 'invalid_request_error'}}"),
            Exception("400 - {'error': {'param': 'c', 'type': 'invalid_request_error'}}"),
            Exception("400 - {'error': {'param': 'd', 'type': 'invalid_request_error'}}"),
        ])
        kwargs = {"a": 1, "b": 2, "c": 3, "d": 4}
        with pytest.raises(RuntimeError, match="after 3 retries"):
            _resilient_call(fn, kwargs, "Test", max_retries=3)

    def test_400_but_unknown_param_raises_immediately(self):
        """400 error where we can't parse the param name → raise, don't loop."""
        fn = mock.Mock(side_effect=Exception(
            "400 - {'error': {'message': 'Something went wrong', "
            "'type': 'invalid_request_error'}}"
        ))
        with pytest.raises(RuntimeError, match="Test API call failed"):
            _resilient_call(fn, {"a": 1}, "Test")


# ===================================================================
# GenAI error patterns & resilient call
# ===================================================================

class TestExtractRejectedParamGenAI:
    """GenAI-specific error-message parser tests."""

    def test_genai_parameter_keyword(self):
        msg = "400 Unsupported parameter 'temperature' for model gemini-1.0-pro"
        assert _extract_rejected_param(msg) == "temperature"

    def test_genai_field_keyword(self):
        msg = "400 Unsupported field 'thinking_config' in GenerateContentConfig"
        assert _extract_rejected_param(msg) == "thinking_config"

    def test_genai_thinking_budget_maps_to_thinking_config(self):
        msg = "400 Unsupported field 'thinking_budget' for this model"
        assert _extract_rejected_param(msg) == "thinking_config"

    def test_genai_include_thoughts_maps_to_thinking_config(self):
        msg = "400 Unsupported field 'include_thoughts' for this model"
        assert _extract_rejected_param(msg) == "thinking_config"


class TestGenAIResilientCall:
    """Verify _send_genai routes through _resilient_call for auto-stripping."""

    @mock.patch("cag.io.llm._resilient_call")
    def test_send_genai_uses_resilient_call(self, mock_resilient):
        """_send_genai delegates to _resilient_call, not a bare try/except."""
        mock_response = mock.Mock()
        mock_response.text = "Hello from Gemini!"
        mock_resilient.return_value = mock_response

        from cag.io.llm import _send_genai
        result = _send_genai("sys", "usr", "fake-key", "gemini-2.0-flash", 0.5, False)

        assert result == "Hello from Gemini!"
        mock_resilient.assert_called_once()
        # Provider label should mention GenAI.
        args = mock_resilient.call_args
        assert args[0][2] == "Google GenAI"

    @mock.patch("cag.io.llm._resilient_call")
    def test_send_genai_thinking_enabled_omits_thinking_config(self, mock_resilient):
        """When thinking=True, thinking_config should NOT be in config_kwargs."""
        mock_response = mock.Mock()
        mock_response.text = "thought about it"
        mock_resilient.return_value = mock_response

        from cag.io.llm import _send_genai
        _send_genai("sys", "usr", "fake-key", "gemini-2.0-flash", 0.5, True)

        config_kwargs = mock_resilient.call_args[0][1]
        assert "thinking_config" not in config_kwargs

    @mock.patch("cag.io.llm._resilient_call")
    def test_send_genai_thinking_disabled_sets_budget_zero(self, mock_resilient):
        """When thinking=False, thinking_config with budget=0 is passed."""
        mock_response = mock.Mock()
        mock_response.text = "no thinking"
        mock_resilient.return_value = mock_response

        from cag.io.llm import _send_genai
        _send_genai("sys", "usr", "fake-key", "gemini-2.0-flash", 0.5, False)

        config_kwargs = mock_resilient.call_args[0][1]
        assert "thinking_config" in config_kwargs
