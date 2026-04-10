"""
Tests for the PoliticalAgent class (Issue 4).
"""
import os
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from cag.abm.agent import PoliticalAgent, _DEFAULT_PRO_CLIMATE_PROMPT, _DEFAULT_ANTI_CLIMATE_PROMPT
from cag.abm.attributes.opinion import ClimatePolicyID, SURVEY_QUESTIONS


class TestPoliticalAgentInit(unittest.TestCase):

    def test_pro_climate_default_prompt(self):
        agent = PoliticalAgent("agent_a", "pro_climate")
        self.assertEqual(agent.side, "pro_climate")
        self.assertEqual(agent.system_prompt, _DEFAULT_PRO_CLIMATE_PROMPT)

    def test_anti_climate_default_prompt(self):
        agent = PoliticalAgent("agent_b", "anti_climate")
        self.assertEqual(agent.side, "anti_climate")
        self.assertEqual(agent.system_prompt, _DEFAULT_ANTI_CLIMATE_PROMPT)

    def test_pro_and_anti_prompts_differ(self):
        pro = PoliticalAgent("a", "pro_climate")
        anti = PoliticalAgent("b", "anti_climate")
        self.assertNotEqual(pro.system_prompt, anti.system_prompt)

    def test_custom_prompt_overrides_default(self):
        custom = "You are a moderate voice."
        agent = PoliticalAgent("agent_c", "pro_climate", system_prompt=custom)
        self.assertEqual(agent.system_prompt, custom)

    def test_invalid_side_raises(self):
        with self.assertRaises(ValueError):
            PoliticalAgent("agent_x", "neutral")

    def test_connected_citizens_starts_empty(self):
        agent = PoliticalAgent("agent_a", "pro_climate")
        self.assertEqual(agent.connected_citizens, [])

    def test_connected_citizens_assignable(self):
        agent = PoliticalAgent("agent_a", "pro_climate")
        agent.connected_citizens = ["citizen_1", "citizen_2"]
        self.assertEqual(len(agent.connected_citizens), 2)

    def test_agent_id_stored(self):
        agent = PoliticalAgent("political_agent_a", "pro_climate")
        self.assertEqual(agent.id, "political_agent_a")


class TestGenerateMessage(unittest.TestCase):

    @patch("cag.abm.agent.send_chat")
    def test_pro_climate_verb_is_supporting(self, mock_send):
        mock_send.return_value = "We must act now on renewables."
        agent = PoliticalAgent("a", "pro_climate")
        agent.generate_message(ClimatePolicyID.CARBON_TAX, api_key="fake")
        user_prompt = mock_send.call_args[0][1]
        self.assertIn("supporting", user_prompt)

    @patch("cag.abm.agent.send_chat")
    def test_anti_climate_verb_is_opposing(self, mock_send):
        mock_send.return_value = "This tax will hurt families."
        agent = PoliticalAgent("b", "anti_climate")
        agent.generate_message(ClimatePolicyID.CARBON_TAX, api_key="fake")
        user_prompt = mock_send.call_args[0][1]
        self.assertIn("opposing", user_prompt)

    @patch("cag.abm.agent.send_chat")
    def test_system_prompt_passed_to_send_chat(self, mock_send):
        mock_send.return_value = "Message text."
        agent = PoliticalAgent("a", "pro_climate")
        agent.generate_message(ClimatePolicyID.RENEWABLE_ENERGY, api_key="fake")
        system_prompt = mock_send.call_args[0][0]
        self.assertEqual(system_prompt, _DEFAULT_PRO_CLIMATE_PROMPT)

    @patch("cag.abm.agent.send_chat")
    def test_user_prompt_contains_policy_question(self, mock_send):
        mock_send.return_value = "Message text."
        agent = PoliticalAgent("a", "pro_climate")
        agent.generate_message(ClimatePolicyID.RENEWABLE_ENERGY, api_key="fake")
        user_prompt = mock_send.call_args[0][1]
        self.assertIn(SURVEY_QUESTIONS[ClimatePolicyID.RENEWABLE_ENERGY], user_prompt)

    @patch("cag.abm.agent.send_chat")
    def test_user_prompt_requests_word_count(self, mock_send):
        mock_send.return_value = "Message text."
        agent = PoliticalAgent("a", "pro_climate")
        agent.generate_message(ClimatePolicyID.GREEN_HOUSING, api_key="fake")
        user_prompt = mock_send.call_args[0][1]
        self.assertIn("150–200 words", user_prompt)

    @patch("cag.abm.agent.send_chat")
    def test_returns_message_string(self, mock_send):
        mock_send.return_value = "Invest in green energy now!"
        agent = PoliticalAgent("a", "pro_climate")
        result = agent.generate_message(ClimatePolicyID.RENEWABLE_ENERGY, api_key="fake")
        self.assertEqual(result, "Invest in green energy now!")

    @patch("cag.abm.agent.send_chat")
    def test_custom_prompt_used_in_generate(self, mock_send):
        mock_send.return_value = "Moderate stance message."
        custom = "You are a centrist commentator."
        agent = PoliticalAgent("c", "anti_climate", system_prompt=custom)
        agent.generate_message(ClimatePolicyID.BAN_PETROL_CARS, api_key="fake")
        system_prompt = mock_send.call_args[0][0]
        self.assertEqual(system_prompt, custom)


if __name__ == "__main__":
    unittest.main()
