"""Tests for Issue 9: tiered memory system."""

import os
import sys
from unittest import mock

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from cag.abm.agent import SurveyedCitizen, NUMERIC_TO_LETTER
from cag.abm.attributes.opinion import ClimatePolicyID


# ===================================================================
# Helpers
# ===================================================================

def _make_citizen():
    env = mock.MagicMock()
    citizen = SurveyedCitizen(agent_id=1, environment=env, year_of_birth=1990)
    citizen.get_persona = mock.MagicMock(return_value="I am a 36 year old teacher.")
    citizen.get_narrative = mock.MagicMock(return_value="I care about fairness.")
    return citizen


def _add_reflections(citizen, day, n=2, phase="P-A", policy_id=ClimatePolicyID.CARBON_TAX):
    for i in range(n):
        citizen.reflections.append({
            "day": day,
            "phase": phase,
            "policy_id": policy_id,
            "text": f"Reflection {i} from day {day}.",
            "messages_received": ["msg"],
        })


# ===================================================================
# Init
# ===================================================================

class TestMemoryInit:

    def test_daily_summaries_empty(self):
        c = _make_citizen()
        assert c.daily_summaries == {}


# ===================================================================
# assemble_context
# ===================================================================

class TestAssembleContext:

    def test_day0_has_persona_only(self):
        c = _make_citizen()
        ctx = c.assemble_context(day=0)
        assert "36 year old teacher" in ctx
        assert "fairness" in ctx
        assert "reflections" not in ctx.lower()

    def test_day1_includes_recent_reflections(self):
        c = _make_citizen()
        _add_reflections(c, day=1)
        ctx = c.assemble_context(day=1)
        assert "Reflection 0 from day 1" in ctx
        assert "Reflection 1 from day 1" in ctx

    def test_day1_includes_day0_reflections_as_recent(self):
        c = _make_citizen()
        _add_reflections(c, day=0, n=1)
        _add_reflections(c, day=1, n=1)
        ctx = c.assemble_context(day=1)
        assert "from day 1" in ctx
        assert "from day 0" in ctx  # day 0 is d-1

    def test_daily_summaries_included_for_older_days(self):
        c = _make_citizen()
        pid = ClimatePolicyID.CARBON_TAX
        c.daily_summaries[(2, pid)] = "Agent became more supportive on day 2."
        c.daily_summaries[(3, pid)] = "Agent reconsidered on day 3."
        _add_reflections(c, day=5)
        ctx = c.assemble_context(day=5, policy_id=pid)
        assert "became more supportive on day 2" in ctx
        assert "reconsidered on day 3" in ctx

    def test_daily_summaries_excluded_for_recent_days(self):
        c = _make_citizen()
        pid = ClimatePolicyID.CARBON_TAX
        c.daily_summaries[(4, pid)] = "Should not appear as summary."
        _add_reflections(c, day=5)
        ctx = c.assemble_context(day=5, policy_id=pid)
        # Day 4 is d-1, so it should be in recent reflections not summaries
        assert "Should not appear as summary" not in ctx

    def test_opinion_trajectory_included(self):
        c = _make_citizen()
        c.opinion_history[ClimatePolicyID.CARBON_TAX] = [(0, -1), (1, 1)]
        _add_reflections(c, day=2)
        ctx = c.assemble_context(day=2)
        assert "Day 0: C" in ctx
        assert "Day 1: E" in ctx

    def test_persona_included_at_end(self):
        c = _make_citizen()
        _add_reflections(c, day=3)
        ctx = c.assemble_context(day=3)
        # Persona appears after reflections (at the bottom)
        ref_pos = ctx.index("Reflection 0 from day 3")
        persona_pos = ctx.rindex("36 year old teacher")
        assert persona_pos > ref_pos


# ===================================================================
# compress_memories
# ===================================================================

class TestCompressMemories:

    @mock.patch("cag.abm.agent.send_chat", return_value="A concise summary.")
    def test_returns_summary(self, mock_send):
        c = _make_citizen()
        result = c.compress_memories("Some long text about reflections.")
        assert result == "A concise summary."

    @mock.patch("cag.abm.agent.send_chat", return_value="Summary.")
    def test_sends_text_to_llm(self, mock_send):
        c = _make_citizen()
        c.compress_memories("reflection text here")
        user_prompt = mock_send.call_args[0][1]
        assert "reflection text here" in user_prompt


# ===================================================================
# compress_daily_memory
# ===================================================================

class TestCompressDailyMemory:

    @mock.patch("cag.abm.agent.send_chat", return_value="Agent shifted toward support.")
    def test_stores_summary(self, mock_send):
        c = _make_citizen()
        pid = ClimatePolicyID.CARBON_TAX
        _add_reflections(c, day=3, n=3)
        summary = c.compress_daily_memory(3, pid)
        assert c.daily_summaries[(3, pid)] == summary
        assert "shifted toward support" in summary

    @mock.patch("cag.abm.agent.send_chat", return_value="Summary.")
    def test_sends_reflections_to_llm(self, mock_send):
        c = _make_citizen()
        pid = ClimatePolicyID.CARBON_TAX
        _add_reflections(c, day=2, n=2)
        c.compress_daily_memory(2, pid)
        user_prompt = mock_send.call_args[0][1]
        assert "Reflection 0 from day 2" in user_prompt
        assert "Reflection 1 from day 2" in user_prompt

    def test_returns_empty_if_no_reflections(self):
        c = _make_citizen()
        pid = ClimatePolicyID.CARBON_TAX
        result = c.compress_daily_memory(5, pid)
        assert result == ""
        assert (5, pid) not in c.daily_summaries


# ===================================================================
# manage_memory
# ===================================================================

class TestManageMemory:

    @mock.patch("cag.abm.agent.send_chat", return_value="Compressed.")
    def test_compresses_day_minus_2(self, mock_send):
        c = _make_citizen()
        pid = ClimatePolicyID.CARBON_TAX
        _add_reflections(c, day=1, n=2)
        _add_reflections(c, day=2, n=2)
        _add_reflections(c, day=3, n=2)
        c.manage_memory(day=3, policy_id=pid)
        assert (1, pid) in c.daily_summaries  # day 3-2 = 1

    @mock.patch("cag.abm.agent.send_chat", return_value="Compressed.")
    def test_does_not_compress_recent_days(self, mock_send):
        c = _make_citizen()
        pid = ClimatePolicyID.CARBON_TAX
        _add_reflections(c, day=3, n=2)
        c.manage_memory(day=3, policy_id=pid)
        assert (3, pid) not in c.daily_summaries
        assert (2, pid) not in c.daily_summaries

    def test_does_not_compress_on_early_days(self):
        c = _make_citizen()
        pid = ClimatePolicyID.CARBON_TAX
        _add_reflections(c, day=1, n=2)
        c.manage_memory(day=1, policy_id=pid)
        assert len(c.daily_summaries) == 0

    @mock.patch("cag.abm.agent.send_chat", return_value="Compressed.")
    def test_does_not_recompress_existing_summary(self, mock_send):
        c = _make_citizen()
        pid = ClimatePolicyID.CARBON_TAX
        c.daily_summaries[(3, pid)] = "Already compressed."
        _add_reflections(c, day=3, n=2)
        _add_reflections(c, day=5, n=2)
        c.manage_memory(day=5, policy_id=pid)
        assert c.daily_summaries[(3, pid)] == "Already compressed."
        mock_send.assert_not_called()


# ===================================================================
# NUMERIC_TO_LETTER
# ===================================================================

class TestNumericToLetter:

    def test_all_values_mapped(self):
        for num in range(-3, 4):
            assert num in NUMERIC_TO_LETTER

    def test_matches_response_scale_inverse(self):
        from cag.abm.attributes.opinion import RESPONSE_SCALE
        for letter, num in RESPONSE_SCALE.items():
            assert NUMERIC_TO_LETTER[num] == letter
