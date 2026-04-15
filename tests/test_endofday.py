"""Tests for Issue 8: end-of-day survey (without clamping)."""

import os
import sys
from unittest import mock

import pytest
import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from cag.abm.agent import SurveyedCitizen
from cag.abm.attributes.opinion import (
    ClimatePolicyID, SURVEY_QUESTIONS, RESPONSE_SCALE,
)


# ===================================================================
# Helpers
# ===================================================================

def _make_citizen():
    """Citizen with mocked persona/narrative and fake survey data."""
    env = mock.MagicMock()
    citizen = SurveyedCitizen(
        agent_id=1, environment=env, year_of_birth=1990,
        original_survey_data={"page5posttreatment6_9": 4.0},
    )
    citizen.get_persona = mock.MagicMock(return_value="I am a 36 year old teacher.")
    citizen.get_narrative = mock.MagicMock(return_value="I care about fairness.")
    return citizen


# ===================================================================
# administer_survey stores opinion_history
# ===================================================================

class TestAdministerSurveyStoresHistory:

    @mock.patch("cag.abm.agent.send_chat", return_value="D")
    def test_day0_creates_history_entry(self, mock_send):
        citizen = _make_citizen()
        policy = ClimatePolicyID.CARBON_TAX
        citizen.administer_survey(policy, day=0)
        assert policy in citizen.opinion_history
        assert citizen.opinion_history[policy] == [(0, 0)]

    @mock.patch("cag.abm.agent.send_chat", return_value="F")
    def test_day1_appends_to_history(self, mock_send):
        citizen = _make_citizen()
        policy = ClimatePolicyID.CARBON_TAX
        # Seed day 0
        citizen.opinion_history[policy] = [(0, 0)]
        citizen.administer_survey(policy, day=1)
        assert len(citizen.opinion_history[policy]) == 2
        assert citizen.opinion_history[policy][1] == (1, 2)

    @mock.patch("cag.abm.agent.send_chat", return_value="A")
    def test_multiple_days_append(self, mock_send):
        citizen = _make_citizen()
        policy = ClimatePolicyID.CARBON_TAX
        citizen.administer_survey(policy, day=0)
        mock_send.return_value = "C"
        citizen.administer_survey(policy, day=1)
        mock_send.return_value = "E"
        citizen.administer_survey(policy, day=2)
        history = citizen.opinion_history[policy]
        assert len(history) == 3
        assert history[0] == (0, -3)  # A
        assert history[1] == (1, -1)  # C
        assert history[2] == (2, 1)   # E


# ===================================================================
# Day > 0 prompt includes reflections and previous response
# ===================================================================

class TestEndOfDayPrompts:

    @mock.patch("cag.abm.agent.send_chat", return_value="D")
    def test_day1_system_prompt_includes_reflections(self, mock_send):
        citizen = _make_citizen()
        citizen.reflections = [
            {"day": 1, "phase": "P-A", "policy_id": ClimatePolicyID.CARBON_TAX, "text": "The carbon tax idea seems fair."},
        ]
        citizen.opinion_history[ClimatePolicyID.CARBON_TAX] = [(0, 1)]
        citizen.administer_survey(ClimatePolicyID.CARBON_TAX, day=1)
        system_prompt = mock_send.call_args[0][0]
        assert "carbon tax idea seems fair" in system_prompt

    @mock.patch("cag.abm.agent.send_chat", return_value="D")
    def test_day1_user_prompt_includes_previous_response(self, mock_send):
        citizen = _make_citizen()
        citizen.opinion_history[ClimatePolicyID.CARBON_TAX] = [(0, 1)]
        citizen.administer_survey(ClimatePolicyID.CARBON_TAX, day=1)
        user_prompt = mock_send.call_args[0][1]
        assert "previous response" in user_prompt.lower()

    @mock.patch("cag.abm.agent.send_chat", return_value="D")
    def test_day0_prompt_does_not_include_reflections(self, mock_send):
        citizen = _make_citizen()
        citizen.reflections = [
            {"day": 1, "phase": "P-A", "text": "Should not appear in day 0."},
        ]
        citizen.administer_survey(ClimatePolicyID.CARBON_TAX, day=0)
        system_prompt = mock_send.call_args[0][0]
        assert "Should not appear" not in system_prompt


# ===================================================================
# run_end_of_day_survey on SurveyedNation
# ===================================================================

class TestRunEndOfDaySurvey:

    @mock.patch("cag.abm.agent.send_chat", return_value="E")
    def test_returns_dataframe(self, mock_send):
        from cag.abm.environment import SurveyedNation
        nation = mock.MagicMock(spec=SurveyedNation)

        # Build two agents with baseline history
        agents = []
        for i in range(2):
            c = _make_citizen()
            c.id = i
            c.opinion_history[ClimatePolicyID.CARBON_TAX] = [(0, 0)]
            agents.append(c)
        nation.agents_active = {a.id: a for a in agents}

        # Call the real method
        df = SurveyedNation.run_end_of_day_survey(
            nation, policy_id=ClimatePolicyID.CARBON_TAX, day=1)

        assert isinstance(df, pd.DataFrame)
        assert len(df) == 2
        assert "raw_letter" in df.columns
        assert "raw_numeric" in df.columns
        assert "shift" in df.columns

    @mock.patch("cag.abm.agent.send_chat", return_value="G")
    def test_shift_computed_correctly(self, mock_send):
        from cag.abm.environment import SurveyedNation
        nation = mock.MagicMock(spec=SurveyedNation)

        c = _make_citizen()
        c.id = 1
        c.opinion_history[ClimatePolicyID.CARBON_TAX] = [(0, -1)]  # baseline = -1
        nation.agents_active = {1: c}

        df = SurveyedNation.run_end_of_day_survey(
            nation, policy_id=ClimatePolicyID.CARBON_TAX, day=1)

        # G = +3, previous = -1, shift = +4
        assert df.iloc[0]["raw_numeric"] == 3
        assert df.iloc[0]["shift"] == 4
