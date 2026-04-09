"""Tests for cag.io.llm module."""

import csv
import os
import tempfile
from unittest import mock

import pytest

import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from cag.io.llm import load_api_key, parse_letter_response, send_chat


# ===================================================================
# parse_letter_response
# ===================================================================

class TestParseLetterResponse:
    """Tests for parse_letter_response."""

    # --- Happy-path cases from the acceptance criteria ---

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

    # --- Error cases ---

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
        # H is not in A-G
        with pytest.raises(ValueError):
            parse_letter_response("H")


# ===================================================================
# load_api_key
# ===================================================================

class TestLoadApiKey:
    """Tests for load_api_key."""

    def _write_csv(self, path, rows):
        """Helper to write a CSV without header."""
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
    """Tests for send_chat (mocked — no real API calls)."""

    def test_raises_for_unsupported_provider(self):
        with pytest.raises(ValueError, match="Unsupported provider"):
            send_chat("sys", "usr", "key", "model", provider="anthropic")

    @mock.patch("cag.io.llm._send_openai", return_value="Hello!")
    def test_openai_dispatch(self, mock_openai):
        result = send_chat("sys", "usr", "key", "gpt-4o-mini", provider="openai")
        assert result == "Hello!"
        mock_openai.assert_called_once_with("sys", "usr", "key", "gpt-4o-mini", 0.7)

    @mock.patch("cag.io.llm._send_genai", return_value="Hi from Gemini!")
    def test_genai_dispatch(self, mock_genai):
        result = send_chat("sys", "usr", "key", "gemini-2.0-flash", provider="genai")
        assert result == "Hi from Gemini!"
        mock_genai.assert_called_once_with("sys", "usr", "key", "gemini-2.0-flash", 0.7)

    @mock.patch("cag.io.llm._send_openai", return_value="warm")
    def test_temperature_passed(self, mock_openai):
        send_chat("sys", "usr", "key", "model", provider="openai", temperature=0.3)
        mock_openai.assert_called_once_with("sys", "usr", "key", "model", 0.3)

    @mock.patch("cag.io.llm._send_openai", return_value="OPENAI")
    def test_provider_case_insensitive(self, mock_openai):
        result = send_chat("sys", "usr", "key", "model", provider="OpenAI")
        assert result == "OPENAI"
