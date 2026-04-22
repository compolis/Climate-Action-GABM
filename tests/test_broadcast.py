"""Tests for Issue 6: Political Broadcast Phases (P-A, P-B)."""

import os
import sys
import unittest
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from cag.abm.agent import SurveyedCitizen, PoliticalAgent
from cag.abm.environment import SurveyedNation
from cag.abm.attributes.opinion import ClimatePolicyID, PACKAGE_SCOPE, SURVEY_QUESTIONS
from cag.abm.democracy.elections.brexit import BrexitVoteID
from cag.abm.democracy.elections.ukge2019 import UKGE2019VoteID
from gabm.abm.attributes.politics import PoliticsID


# ===================================================================
# Helpers
# ===================================================================

_MOCK_REFLECTION = "This message makes me reconsider my position on this policy."
_MOCK_MESSAGE = "We must act now on climate change for the good of all citizens."

_PROFILES = [
    # 0: A-only (Remain + Labour)
    {"brexit_vote_id": BrexitVoteID.REMAIN, "ukge2019_vote_id": UKGE2019VoteID.LABOUR, "politics_id": PoliticsID.FAIRLY_LEFT_WING},
    # 1: A-only (Remain + Green)
    {"brexit_vote_id": BrexitVoteID.REMAIN, "ukge2019_vote_id": UKGE2019VoteID.GREEN, "politics_id": PoliticsID.VERY_LEFT_WING},
    # 2: B-only (Leave + Conservative)
    {"brexit_vote_id": BrexitVoteID.LEAVE, "ukge2019_vote_id": UKGE2019VoteID.CONSERVATIVE, "politics_id": PoliticsID.FAIRLY_RIGHT_WING},
    # 3: B-only (Leave + Brexit)
    {"brexit_vote_id": BrexitVoteID.LEAVE, "ukge2019_vote_id": UKGE2019VoteID.BREXIT, "politics_id": PoliticsID.VERY_RIGHT_WING},
    # 4: both (Leave + Labour, mixed)
    {"brexit_vote_id": BrexitVoteID.LEAVE, "ukge2019_vote_id": UKGE2019VoteID.LABOUR, "politics_id": PoliticsID.CENTRE},
    # 5: both (Remain + Conservative, mixed)
    {"brexit_vote_id": BrexitVoteID.REMAIN, "ukge2019_vote_id": UKGE2019VoteID.CONSERVATIVE, "politics_id": PoliticsID.SLIGHTLY_RIGHT_OF_CENTRE},
    # 6: neither (Unknown both)
    {"brexit_vote_id": BrexitVoteID.UNKNOWN, "ukge2019_vote_id": UKGE2019VoteID.UNKNOWN, "politics_id": PoliticsID.DONT_KNOW},
]


def _make_nation():
    """Create a small SurveyedNation with 7 citizens covering all exposure categories."""
    sn = SurveyedNation()
    sn.political_agent_a = PoliticalAgent("agent_a", "pro_climate")
    sn.political_agent_b = PoliticalAgent("agent_b", "anti_climate")

    for i, profile in enumerate(_PROFILES):
        citizen = SurveyedCitizen(
            agent_id=i,
            environment=sn,
            brexit_vote_id=profile.get("brexit_vote_id"),
            ukge2019_vote_id=profile.get("ukge2019_vote_id"),
            politics_id=profile.get("politics_id"),
        )
        sn.agents_active[citizen.id] = citizen

    sn.assign_political_exposure()
    return sn


# ===================================================================
# Tests: SurveyedCitizen.receive_political_message()
# ===================================================================

class TestReceivePoliticalMessage(unittest.TestCase):

    def setUp(self):
        self.citizen = SurveyedCitizen(agent_id=0, environment=MagicMock())
        # Mock get_system_prompt so we don't need full environment maps
        self.citizen.get_system_prompt = MagicMock(return_value="I am a test persona.")

    @patch("cag.abm.agent.send_chat", return_value=_MOCK_REFLECTION)
    def test_returns_reflection_text(self, mock_send):
        result = self.citizen.receive_political_message(
            _MOCK_MESSAGE, ClimatePolicyID.CARBON_TAX, "P-A", day=1
        )
        self.assertEqual(result, _MOCK_REFLECTION)

    @patch("cag.abm.agent.send_chat", return_value=_MOCK_REFLECTION)
    def test_appends_to_reflections(self, mock_send):
        self.citizen.receive_political_message(
            _MOCK_MESSAGE, ClimatePolicyID.CARBON_TAX, "P-A", day=1
        )
        self.assertEqual(len(self.citizen.reflections), 1)

    @patch("cag.abm.agent.send_chat", return_value=_MOCK_REFLECTION)
    def test_reflection_dict_keys(self, mock_send):
        self.citizen.receive_political_message(
            _MOCK_MESSAGE, ClimatePolicyID.CARBON_TAX, "P-A", day=1
        )
        ref = self.citizen.reflections[0]
        self.assertEqual(set(ref.keys()), {"day", "phase", "policy_id", "text", "messages_received"})

    @patch("cag.abm.agent.send_chat", return_value=_MOCK_REFLECTION)
    def test_reflection_day_and_phase(self, mock_send):
        self.citizen.receive_political_message(
            _MOCK_MESSAGE, ClimatePolicyID.RENEWABLE_ENERGY, "P-B", day=3
        )
        ref = self.citizen.reflections[0]
        self.assertEqual(ref["day"], 3)
        self.assertEqual(ref["phase"], "P-B")

    @patch("cag.abm.agent.send_chat", return_value=_MOCK_REFLECTION)
    def test_reflection_messages_received(self, mock_send):
        self.citizen.receive_political_message(
            _MOCK_MESSAGE, ClimatePolicyID.CARBON_TAX, "P-A", day=1
        )
        ref = self.citizen.reflections[0]
        self.assertIsInstance(ref["messages_received"], list)
        self.assertEqual(ref["messages_received"], [_MOCK_MESSAGE])

    @patch("cag.abm.agent.send_chat", return_value=_MOCK_REFLECTION)
    def test_multiple_calls_accumulate(self, mock_send):
        self.citizen.receive_political_message(
            _MOCK_MESSAGE, ClimatePolicyID.CARBON_TAX, "P-A", day=1
        )
        self.citizen.receive_political_message(
            "Another message", ClimatePolicyID.GREEN_HOUSING, "P-B", day=1
        )
        self.assertEqual(len(self.citizen.reflections), 2)
        self.assertEqual(self.citizen.reflections[0]["phase"], "P-A")
        self.assertEqual(self.citizen.reflections[1]["phase"], "P-B")

    @patch("cag.abm.agent.send_chat", return_value=_MOCK_REFLECTION)
    def test_calls_send_chat_with_correct_args(self, mock_send):
        self.citizen.receive_political_message(
            _MOCK_MESSAGE, ClimatePolicyID.CARBON_TAX, "P-A", day=1,
            api_key="test-key", model="gpt-4o", provider="openai", temperature=0.5
        )
        mock_send.assert_called_once()
        call_kwargs = mock_send.call_args
        self.assertEqual(call_kwargs.kwargs["api_key"], "test-key")
        self.assertEqual(call_kwargs.kwargs["model"], "gpt-4o")
        self.assertEqual(call_kwargs.kwargs["temperature"], 0.5)

    @patch("cag.abm.agent.send_chat", return_value=_MOCK_REFLECTION)
    def test_user_prompt_contains_message_and_policy(self, mock_send):
        self.citizen.receive_political_message(
            _MOCK_MESSAGE, ClimatePolicyID.CARBON_TAX, "P-A", day=1
        )
        user_prompt = mock_send.call_args[0][1]
        self.assertIn(_MOCK_MESSAGE, user_prompt)
        self.assertIn(SURVEY_QUESTIONS[ClimatePolicyID.CARBON_TAX], user_prompt)
        self.assertIn("Do not state a final position", user_prompt)


# ===================================================================
# Tests: SurveyedCitizen.reflections default
# ===================================================================

class TestReflectionsAttribute(unittest.TestCase):

    def test_default_reflections_empty_list(self):
        c = SurveyedCitizen(agent_id=0)
        self.assertEqual(c.reflections, [])

    def test_reflections_not_shared(self):
        c1 = SurveyedCitizen(agent_id=0)
        c2 = SurveyedCitizen(agent_id=1)
        c1.reflections.append({"test": True})
        self.assertEqual(c2.reflections, [])


# ===================================================================
# Tests: SurveyedNation.run_political_broadcast()
# ===================================================================

class TestRunPoliticalBroadcast(unittest.TestCase):

    def setUp(self):
        self.sn = _make_nation()

    @patch("cag.abm.agent.SurveyedCitizen.get_system_prompt", return_value="Test persona.")
    @patch("cag.abm.agent.send_chat", return_value=_MOCK_REFLECTION)
    def test_pa_only_a_connected_get_reflections(self, mock_send, mock_prompt):
        """P-A broadcast: only citizens connected to agent_a get reflections."""
        self.sn.run_political_broadcast(
            "P-A", ClimatePolicyID.CARBON_TAX, day=1
        )
        a_ids = {c.id for c in self.sn.political_agent_a.connected_citizens}
        for cid, citizen in self.sn.agents_active.items():
            if cid in a_ids:
                self.assertGreater(len(citizen.reflections), 0,
                                   f"Agent {cid} should have reflections")
            else:
                self.assertEqual(len(citizen.reflections), 0,
                                 f"Agent {cid} should have no reflections")

    @patch("cag.abm.agent.SurveyedCitizen.get_system_prompt", return_value="Test persona.")
    @patch("cag.abm.agent.send_chat", return_value=_MOCK_REFLECTION)
    def test_pb_only_b_connected_get_reflections(self, mock_send, mock_prompt):
        """P-B broadcast: only citizens connected to agent_b get reflections."""
        self.sn.run_political_broadcast(
            "P-B", ClimatePolicyID.CARBON_TAX, day=1
        )
        b_ids = {c.id for c in self.sn.political_agent_b.connected_citizens}
        for cid, citizen in self.sn.agents_active.items():
            if cid in b_ids:
                self.assertGreater(len(citizen.reflections), 0,
                                   f"Agent {cid} should have reflections")
            else:
                self.assertEqual(len(citizen.reflections), 0,
                                 f"Agent {cid} should have no reflections")

    @patch("cag.abm.agent.SurveyedCitizen.get_system_prompt", return_value="Test persona.")
    @patch("cag.abm.agent.send_chat", return_value=_MOCK_REFLECTION)
    def test_reflection_count_matches_connected(self, mock_send, mock_prompt):
        """Reflection count equals number of connected citizens."""
        result = self.sn.run_political_broadcast(
            "P-A", ClimatePolicyID.CARBON_TAX, day=1
        )
        expected = len(self.sn.political_agent_a.connected_citizens)
        self.assertEqual(result["reflections_count"], expected)

    @patch("cag.abm.agent.SurveyedCitizen.get_system_prompt", return_value="Test persona.")
    @patch("cag.abm.agent.send_chat", return_value=_MOCK_REFLECTION)
    def test_return_dict_keys(self, mock_send, mock_prompt):
        result = self.sn.run_political_broadcast(
            "P-A", ClimatePolicyID.CARBON_TAX, day=1
        )
        self.assertEqual(set(result.keys()), {"message", "reflections_count", "sample_reflections"})

    @patch("cag.abm.agent.SurveyedCitizen.get_system_prompt", return_value="Test persona.")
    @patch("cag.abm.agent.send_chat", return_value=_MOCK_REFLECTION)
    def test_return_message_is_string(self, mock_send, mock_prompt):
        result = self.sn.run_political_broadcast(
            "P-A", ClimatePolicyID.CARBON_TAX, day=1
        )
        self.assertIsInstance(result["message"], str)
        self.assertTrue(len(result["message"]) > 0)

    @patch("cag.abm.agent.SurveyedCitizen.get_system_prompt", return_value="Test persona.")
    @patch("cag.abm.agent.send_chat", return_value=_MOCK_REFLECTION)
    def test_sample_reflections_at_most_two(self, mock_send, mock_prompt):
        result = self.sn.run_political_broadcast(
            "P-A", ClimatePolicyID.CARBON_TAX, day=1
        )
        self.assertLessEqual(len(result["sample_reflections"]), 2)

    def test_invalid_phase_raises(self):
        with self.assertRaises(ValueError):
            self.sn.run_political_broadcast(
                "P-C", ClimatePolicyID.CARBON_TAX, day=1
            )

    @patch("cag.abm.agent.SurveyedCitizen.get_system_prompt", return_value="Test persona.")
    @patch("cag.abm.agent.send_chat", return_value=_MOCK_REFLECTION)
    def test_generate_message_called_once(self, mock_send, mock_prompt):
        """Political agent's generate_message is called exactly once per broadcast."""
        n_connected = len(self.sn.political_agent_a.connected_citizens)
        self.sn.run_political_broadcast(
            "P-A", ClimatePolicyID.CARBON_TAX, day=1
        )
        # send_chat is called once for generate_message + once per connected citizen
        self.assertEqual(mock_send.call_count, 1 + n_connected)

    @patch("cag.abm.agent.SurveyedCitizen.get_system_prompt", return_value="Test persona.")
    @patch("cag.abm.agent.send_chat", return_value=_MOCK_REFLECTION)
    def test_neither_citizens_no_reflections_after_both_phases(self, mock_send, mock_prompt):
        """Citizens with 'neither' exposure get no reflections from either phase."""
        self.sn.run_political_broadcast("P-A", ClimatePolicyID.CARBON_TAX, day=1)
        self.sn.run_political_broadcast("P-B", ClimatePolicyID.CARBON_TAX, day=1)
        neither_citizens = [c for c in self.sn.agents_active.values()
                           if c.political_exposure == "neither"]
        self.assertGreater(len(neither_citizens), 0, "Test needs at least one 'neither' citizen")
        for citizen in neither_citizens:
            self.assertEqual(len(citizen.reflections), 0,
                           f"Agent {citizen.id} ('neither') should have no reflections")

    @patch("cag.abm.agent.SurveyedCitizen.get_system_prompt", return_value="Test persona.")
    @patch("cag.abm.agent.send_chat", return_value=_MOCK_REFLECTION)
    def test_both_citizens_get_reflections_from_both_phases(self, mock_send, mock_prompt):
        """Citizens with 'both' exposure get reflections from both P-A and P-B."""
        self.sn.run_political_broadcast("P-A", ClimatePolicyID.CARBON_TAX, day=1)
        self.sn.run_political_broadcast("P-B", ClimatePolicyID.CARBON_TAX, day=1)
        both_citizens = [c for c in self.sn.agents_active.values()
                        if c.political_exposure == "both"]
        self.assertGreater(len(both_citizens), 0, "Test needs at least one 'both' citizen")
        for citizen in both_citizens:
            self.assertEqual(len(citizen.reflections), 2,
                           f"Agent {citizen.id} ('both') should have 2 reflections")
            phases = {r["phase"] for r in citizen.reflections}
            self.assertEqual(phases, {"P-A", "P-B"})

    @patch("cag.abm.agent.SurveyedCitizen.get_system_prompt", return_value="Test persona.")
    @patch("cag.abm.agent.send_chat", return_value=_MOCK_REFLECTION)
    def test_reflection_phase_matches_broadcast(self, mock_send, mock_prompt):
        """Reflections from P-A broadcast all have phase='P-A'."""
        self.sn.run_political_broadcast("P-A", ClimatePolicyID.CARBON_TAX, day=2)
        for citizen in self.sn.political_agent_a.connected_citizens:
            for ref in citizen.reflections:
                self.assertEqual(ref["phase"], "P-A")
                self.assertEqual(ref["day"], 2)

    @patch("cag.abm.agent.SurveyedCitizen.get_system_prompt", return_value="Test persona.")
    @patch("cag.abm.agent.send_chat", return_value=_MOCK_REFLECTION)
    def test_logs_one_delivery_per_connected_citizen(self, mock_send, mock_prompt):
        self.sn.run_political_broadcast("P-A", ClimatePolicyID.CARBON_TAX, day=1)
        self.assertEqual(
            len(self.sn.message_log),
            len(self.sn.political_agent_a.connected_citizens),
        )

    @patch("cag.abm.agent.SurveyedCitizen.get_system_prompt", return_value="Test persona.")
    @patch("cag.abm.agent.send_chat", return_value=_MOCK_REFLECTION)
    def test_message_log_contains_broadcast_metadata(self, mock_send, mock_prompt):
        self.sn.run_political_broadcast("P-B", ClimatePolicyID.CARBON_TAX, day=2)
        log_entry = self.sn.message_log[0]
        self.assertEqual(log_entry["message_type"], "political_broadcast")
        self.assertEqual(log_entry["sender_type"], "political_agent")
        self.assertEqual(log_entry["recipient_scope"], "broadcast")
        self.assertEqual(log_entry["policy_id"], ClimatePolicyID.CARBON_TAX)
        self.assertEqual(log_entry["package_scope"], "")
        self.assertIn(log_entry["recipient_id"], self.sn.agents_active)


class TestRunPackageBroadcastLogging(unittest.TestCase):

    def setUp(self):
        self.sn = _make_nation()

    @patch("cag.abm.agent.SurveyedCitizen.get_system_prompt", return_value="Test persona.")
    @patch("cag.abm.agent.send_chat", return_value=_MOCK_REFLECTION)
    def test_logs_package_delivery_rows(self, mock_send, mock_prompt):
        policy_ids = [ClimatePolicyID.CARBON_TAX, ClimatePolicyID.GREEN_HOUSING]
        self.sn.run_package_broadcast("P-A", policy_ids, day=1)
        self.assertEqual(
            len(self.sn.message_log),
            len(self.sn.political_agent_a.connected_citizens),
        )
        log_entry = self.sn.message_log[0]
        self.assertEqual(log_entry["message_type"], "political_broadcast")
        self.assertEqual(log_entry["package_scope"], PACKAGE_SCOPE)
        self.assertEqual(log_entry["policy_ids"], policy_ids)


if __name__ == "__main__":
    unittest.main()
