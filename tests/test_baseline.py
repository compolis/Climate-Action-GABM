"""Tests for Issue 3: baseline survey, opinion_history, and real survey responses."""

import os
import sys
from unittest import mock

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from cag.abm.agent import SurveyedCitizen
from cag.abm.attributes.opinion import (
    SURVEY_QUESTIONS, RESPONSE_SCALE, SURVEY_COLUMN_MAP,
    ALL_CLIMATE_POLICIES, ClimatePolicyID,
)


# ===================================================================
# Helpers
# ===================================================================

def _make_citizen(survey_data=None):
    """Create a bare SurveyedCitizen with optional survey data."""
    return SurveyedCitizen(agent_id=1, original_survey_data=survey_data)


def _make_citizen_with_env():
    """Create a SurveyedCitizen with a mock environment for persona/narrative."""
    env = mock.MagicMock()
    # get_persona and get_narrative access environment maps, so mock them
    citizen = SurveyedCitizen(agent_id=1, environment=env, year_of_birth=1990)
    # Patch the methods directly to avoid needing real maps
    citizen.get_persona = mock.MagicMock(return_value="I am a 36 year old female living in London.")
    citizen.get_narrative = mock.MagicMock(return_value="I care about the environment.")
    return citizen


def _dummy_survey_data():
    """Fake original survey row with known values for all 6 policies."""
    return {
        "page5posttreatment6_1": 5.0,   # renewable_energy: 5 -> numeric 1
        "page5posttreatment6_4": 2.0,   # ban_fossil_fuel: 2 -> numeric -2
        "page5posttreatment6_5": 4.0,   # ban_petrol_cars: 4 -> numeric 0
        "page5posttreatment6_7": 6.0,   # green_housing: 6 -> numeric 2
        "page5posttreatment6_9": 1.0,   # carbon_tax: 1 -> numeric -3
        "page5posttreatment6_11": 7.0,  # climate_compensation: 7 -> numeric 3
    }


# ===================================================================
# opinion_history
# ===================================================================

class TestOpinionHistory:

    def test_opinion_history_exists(self):
        citizen = _make_citizen()
        assert hasattr(citizen, "opinion_history")

    def test_opinion_history_is_empty_dict(self):
        citizen = _make_citizen()
        assert citizen.opinion_history == {}


# ===================================================================
# get_real_survey_response
# ===================================================================

class TestGetRealSurveyResponse:

    def test_returns_correct_numeric_value(self):
        data = _dummy_survey_data()
        citizen = _make_citizen(survey_data=data)
        # CSV value 5 -> 5 - 4 = 1
        assert citizen.get_real_survey_response(ClimatePolicyID.RENEWABLE_ENERGY) == 1

    def test_all_policies_return_expected_values(self):
        data = _dummy_survey_data()
        citizen = _make_citizen(survey_data=data)
        expected = {
            ClimatePolicyID.RENEWABLE_ENERGY: 1,
            ClimatePolicyID.BAN_FOSSIL_FUEL: -2,
            ClimatePolicyID.BAN_PETROL_CARS: 0,
            ClimatePolicyID.GREEN_HOUSING: 2,
            ClimatePolicyID.CARBON_TAX: -3,
            ClimatePolicyID.CLIMATE_COMPENSATION: 3,
        }
        for policy_id, expected_value in expected.items():
            assert citizen.get_real_survey_response(policy_id) == expected_value

    def test_extremes_of_scale(self):
        # CSV 1 -> -3, CSV 7 -> +3
        data_low = {"page5posttreatment6_9": 1.0}
        citizen_low = _make_citizen(survey_data=data_low)
        assert citizen_low.get_real_survey_response(ClimatePolicyID.CARBON_TAX) == -3

        data_high = {"page5posttreatment6_9": 7.0}
        citizen_high = _make_citizen(survey_data=data_high)
        assert citizen_high.get_real_survey_response(ClimatePolicyID.CARBON_TAX) == 3


# ===================================================================
# administer_survey (mocked LLM)
# ===================================================================

class TestAdministerSurvey:

    @mock.patch("cag.abm.agent.send_chat", return_value="E")
    def test_returns_letter_and_numeric(self, mock_send):
        citizen = _make_citizen_with_env()
        letter, numeric = citizen.administer_survey(ClimatePolicyID.BAN_FOSSIL_FUEL)
        assert letter == "E"
        assert numeric == 1  # E -> +1

    @mock.patch("cag.abm.agent.send_chat", return_value="A. Strongly oppose")
    def test_parses_letter_from_verbose_response(self, mock_send):
        citizen = _make_citizen_with_env()
        letter, numeric = citizen.administer_survey(ClimatePolicyID.CARBON_TAX)
        assert letter == "A"
        assert numeric == -3

    @mock.patch("cag.abm.agent.send_chat", return_value="G")
    def test_system_prompt_uses_persona_and_narrative(self, mock_send):
        citizen = _make_citizen_with_env()
        citizen.administer_survey(ClimatePolicyID.GREEN_HOUSING)
        call_args = mock_send.call_args
        system_prompt = call_args[0][0] if call_args[0] else call_args[1].get("system_prompt")
        # get_persona() now returns merged demographics + values in a single string;
        # _make_citizen_with_env mocks it to return only the demographics line.
        assert "36 year old female" in system_prompt

    @mock.patch("cag.abm.agent.send_chat", return_value="D")
    def test_user_prompt_contains_question_and_options(self, mock_send):
        citizen = _make_citizen_with_env()
        citizen.administer_survey(ClimatePolicyID.BAN_FOSSIL_FUEL)
        call_args = mock_send.call_args
        user_prompt = call_args[0][1] if len(call_args[0]) > 1 else call_args[1].get("user_prompt")
        assert "Ban new oil/gas/coal licenses" in user_prompt
        assert "Strongly oppose" in user_prompt
        assert "Strongly support" in user_prompt
        assert "Respond with a single letter A-G" in user_prompt

    @mock.patch("cag.abm.agent.send_chat", return_value="C")
    def test_all_seven_letters_map_correctly(self, mock_send):
        citizen = _make_citizen_with_env()
        for letter_input, expected_numeric in RESPONSE_SCALE.items():
            mock_send.return_value = letter_input
            letter, numeric = citizen.administer_survey(ClimatePolicyID.RENEWABLE_ENERGY)
            assert letter == letter_input
            assert numeric == expected_numeric


# ===================================================================
# run_baseline (mocked LLM)
# ===================================================================

class TestRunBaseline:

    @mock.patch("cag.abm.agent.send_chat", return_value="D")
    def test_returns_dict_with_six_policies(self, mock_send):
        citizen = _make_citizen_with_env()
        results = citizen.run_baseline()
        assert len(results) == 6

    @mock.patch("cag.abm.agent.send_chat", return_value="D")
    def test_opinion_history_populated(self, mock_send):
        citizen = _make_citizen_with_env()
        citizen.run_baseline()
        assert len(citizen.opinion_history) == 6
        for policy_id, history in citizen.opinion_history.items():
            assert len(history) == 1
            day, numeric = history[0]
            assert day == 0

    @mock.patch("cag.abm.agent.send_chat", return_value="F")
    def test_results_match_opinion_history(self, mock_send):
        citizen = _make_citizen_with_env()
        results = citizen.run_baseline()
        for policy_id, (letter, numeric) in results.items():
            assert letter == "F"
            assert numeric == 2  # F -> +2
            assert citizen.opinion_history[policy_id] == [(0, 2)]

    @mock.patch("cag.abm.agent.send_chat", return_value="B")
    def test_all_responses_are_valid_letters(self, mock_send):
        citizen = _make_citizen_with_env()
        results = citizen.run_baseline()
        valid_letters = set("ABCDEFG")
        for policy_id, (letter, numeric) in results.items():
            assert letter in valid_letters
            assert -3 <= numeric <= 3
