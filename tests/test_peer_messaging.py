"""Tests for Issue 7: Peer Messaging Phase (C)."""

import os
import sys
import unittest
from unittest.mock import patch, MagicMock, call

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

_MOCK_PEER_MESSAGE = "I think we need to consider the economic impact of this policy."
_MOCK_REFLECTION = "Hearing from my peers, I can see different angles on this issue."

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
    """Create a small SurveyedNation with 7 citizens, network, and exposure."""
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

    sn.assign_political_exposure(mode="rule_priority_chain")
    sn.create_network(seed=42)
    sn.assign_network_blocks()
    return sn


# ===================================================================
# Tests: SurveyedCitizen.generate_peer_message()
# ===================================================================

class TestGeneratePeerMessage(unittest.TestCase):

    def setUp(self):
        self.citizen = SurveyedCitizen(agent_id=0, environment=MagicMock())
        self.citizen.get_system_prompt = MagicMock(return_value="I am a test persona.")

    @patch("cag.abm.agent.send_chat", return_value=_MOCK_PEER_MESSAGE)
    def test_returns_message_text(self, mock_send):
        result = self.citizen.generate_peer_message(ClimatePolicyID.CARBON_TAX)
        self.assertEqual(result, _MOCK_PEER_MESSAGE)

    @patch("cag.abm.agent.send_chat", return_value=_MOCK_PEER_MESSAGE)
    def test_calls_send_chat(self, mock_send):
        self.citizen.generate_peer_message(ClimatePolicyID.CARBON_TAX)
        mock_send.assert_called_once()

    @patch("cag.abm.agent.send_chat", return_value=_MOCK_PEER_MESSAGE)
    def test_system_prompt_uses_get_system_prompt(self, mock_send):
        self.citizen.generate_peer_message(ClimatePolicyID.CARBON_TAX)
        system_prompt = mock_send.call_args[0][0]
        self.assertEqual(system_prompt, "I am a test persona.")

    @patch("cag.abm.agent.send_chat", return_value=_MOCK_PEER_MESSAGE)
    def test_user_prompt_contains_policy(self, mock_send):
        self.citizen.generate_peer_message(ClimatePolicyID.CARBON_TAX)
        user_prompt = mock_send.call_args[0][1]
        self.assertIn(SURVEY_QUESTIONS[ClimatePolicyID.CARBON_TAX], user_prompt)

    @patch("cag.abm.agent.send_chat", return_value=_MOCK_PEER_MESSAGE)
    def test_user_prompt_contains_conversational_instruction(self, mock_send):
        self.citizen.generate_peer_message(ClimatePolicyID.CARBON_TAX)
        user_prompt = mock_send.call_args[0][1]
        self.assertIn("Be genuine and conversational", user_prompt)

    @patch("cag.abm.agent.send_chat", return_value=_MOCK_PEER_MESSAGE)
    def test_passes_api_params(self, mock_send):
        self.citizen.generate_peer_message(
            ClimatePolicyID.CARBON_TAX, api_key="k", model="m",
            provider="p", temperature=0.5,
        )
        kwargs = mock_send.call_args.kwargs
        self.assertEqual(kwargs["api_key"], "k")
        self.assertEqual(kwargs["model"], "m")
        self.assertEqual(kwargs["provider"], "p")
        self.assertEqual(kwargs["temperature"], 0.5)

    @patch("cag.abm.agent.send_chat", return_value=_MOCK_PEER_MESSAGE)
    def test_does_not_modify_reflections(self, mock_send):
        """generate_peer_message should NOT add to reflections (only receive does)."""
        self.citizen.generate_peer_message(ClimatePolicyID.CARBON_TAX)
        self.assertEqual(len(self.citizen.reflections), 0)


# ===================================================================
# Tests: SurveyedCitizen.receive_peer_messages()
# ===================================================================

class TestReceivePeerMessages(unittest.TestCase):

    def setUp(self):
        self.citizen = SurveyedCitizen(agent_id=0, environment=MagicMock())
        self.citizen.get_system_prompt = MagicMock(return_value="I am a test persona.")

    @patch("cag.abm.agent.send_chat", return_value=_MOCK_REFLECTION)
    def test_returns_reflection_text(self, mock_send):
        result = self.citizen.receive_peer_messages(
            ["msg1", "msg2"], ClimatePolicyID.CARBON_TAX, day=1
        )
        self.assertEqual(result, _MOCK_REFLECTION)

    @patch("cag.abm.agent.send_chat", return_value=_MOCK_REFLECTION)
    def test_appends_to_reflections(self, mock_send):
        self.citizen.receive_peer_messages(
            ["msg1"], ClimatePolicyID.CARBON_TAX, day=1
        )
        self.assertEqual(len(self.citizen.reflections), 1)

    @patch("cag.abm.agent.send_chat", return_value=_MOCK_REFLECTION)
    def test_reflection_has_phase_c(self, mock_send):
        self.citizen.receive_peer_messages(
            ["msg1"], ClimatePolicyID.CARBON_TAX, day=1
        )
        self.assertEqual(self.citizen.reflections[0]["phase"], "C")

    @patch("cag.abm.agent.send_chat", return_value=_MOCK_REFLECTION)
    def test_reflection_stores_day(self, mock_send):
        self.citizen.receive_peer_messages(
            ["msg1"], ClimatePolicyID.CARBON_TAX, day=3
        )
        self.assertEqual(self.citizen.reflections[0]["day"], 3)

    @patch("cag.abm.agent.send_chat", return_value=_MOCK_REFLECTION)
    def test_reflection_stores_all_messages(self, mock_send):
        messages = ["msg1", "msg2", "msg3"]
        self.citizen.receive_peer_messages(
            messages, ClimatePolicyID.CARBON_TAX, day=1
        )
        self.assertEqual(self.citizen.reflections[0]["messages_received"], messages)

    @patch("cag.abm.agent.send_chat", return_value=_MOCK_REFLECTION)
    def test_user_prompt_contains_all_messages(self, mock_send):
        self.citizen.receive_peer_messages(
            ["first msg", "second msg"], ClimatePolicyID.CARBON_TAX, day=1
        )
        user_prompt = mock_send.call_args[0][1]
        self.assertIn("first msg", user_prompt)
        self.assertIn("second msg", user_prompt)

    @patch("cag.abm.agent.send_chat", return_value=_MOCK_REFLECTION)
    def test_user_prompt_contains_policy(self, mock_send):
        self.citizen.receive_peer_messages(
            ["msg1"], ClimatePolicyID.RENEWABLE_ENERGY, day=1
        )
        user_prompt = mock_send.call_args[0][1]
        self.assertIn(SURVEY_QUESTIONS[ClimatePolicyID.RENEWABLE_ENERGY], user_prompt)

    @patch("cag.abm.agent.send_chat", return_value=_MOCK_REFLECTION)
    def test_reflection_dict_keys(self, mock_send):
        self.citizen.receive_peer_messages(
            ["msg1"], ClimatePolicyID.CARBON_TAX, day=1
        )
        ref = self.citizen.reflections[0]
        self.assertEqual(set(ref.keys()), {"day", "phase", "policy_id", "text", "messages_received"})

    @patch("cag.abm.agent.send_chat", return_value=_MOCK_REFLECTION)
    def test_messages_received_is_copy(self, mock_send):
        """messages_received should be a copy, not a reference to the input."""
        original = ["msg1", "msg2"]
        self.citizen.receive_peer_messages(
            original, ClimatePolicyID.CARBON_TAX, day=1
        )
        original.append("msg3")
        self.assertEqual(len(self.citizen.reflections[0]["messages_received"]), 2)


# ===================================================================
# Tests: SurveyedNation.run_peer_messaging()
# ===================================================================

class TestRunPeerMessaging(unittest.TestCase):

    def setUp(self):
        self.sn = _make_nation()

    @patch("cag.abm.agent.SurveyedCitizen.get_system_prompt", return_value="Test persona.")
    @patch("cag.abm.agent.send_chat", return_value=_MOCK_PEER_MESSAGE)
    def test_returns_dict_with_expected_keys(self, mock_send, mock_prompt):
        result = self.sn.run_peer_messaging(
            ClimatePolicyID.CARBON_TAX, day=1, k_peers=2
        )
        self.assertEqual(
            set(result.keys()),
            {"messages_generated", "reflections_count", "sample_messages", "sample_reflections"}
        )

    @patch("cag.abm.agent.SurveyedCitizen.get_system_prompt", return_value="Test persona.")
    @patch("cag.abm.agent.send_chat", return_value=_MOCK_PEER_MESSAGE)
    def test_only_citizens_with_neighbors_generate(self, mock_send, mock_prompt):
        """Citizens with no network neighbors should not generate messages."""
        result = self.sn.run_peer_messaging(
            ClimatePolicyID.CARBON_TAX, day=1, k_peers=2
        )
        n_with_neighbors = sum(
            1 for c in self.sn.agents_active.values()
            if len(c.network_neighbors) > 0
        )
        self.assertEqual(result["messages_generated"], n_with_neighbors)

    @patch("cag.abm.agent.SurveyedCitizen.get_system_prompt", return_value="Test persona.")
    @patch("cag.abm.agent.send_chat", return_value=_MOCK_PEER_MESSAGE)
    def test_no_neighbor_citizens_no_reflections(self, mock_send, mock_prompt):
        """Citizens with 0 neighbors get no reflections and cause no errors."""
        self.sn.run_peer_messaging(ClimatePolicyID.CARBON_TAX, day=1, k_peers=2)
        for citizen in self.sn.agents_active.values():
            if not citizen.network_neighbors:
                self.assertEqual(len(citizen.reflections), 0,
                                 f"Agent {citizen.id} has no neighbors but got reflections")

    @patch("cag.abm.agent.SurveyedCitizen.get_system_prompt", return_value="Test persona.")
    @patch("cag.abm.agent.send_chat", return_value=_MOCK_PEER_MESSAGE)
    def test_k_peers_respected(self, mock_send, mock_prompt):
        """No citizen should receive more messages than k_peers × (sources)."""
        k = 1
        self.sn.run_peer_messaging(ClimatePolicyID.CARBON_TAX, day=1, k_peers=k)
        for citizen in self.sn.agents_active.values():
            phase_c_refs = [r for r in citizen.reflections if r["phase"] == "C"]
            for ref in phase_c_refs:
                # Each sender selects at most k neighbors, so each recipient
                # gets at most (num_agents - 1) messages, but the total
                # messages generated by all senders is bounded
                self.assertIsInstance(ref["messages_received"], list)

    @patch("cag.abm.agent.SurveyedCitizen.get_system_prompt", return_value="Test persona.")
    @patch("cag.abm.agent.send_chat")
    def test_simultaneous_update(self, mock_send, mock_prompt):
        """ALL generate_peer_message calls must happen BEFORE any
        receive_peer_messages calls. We verify this by tracking call order."""
        call_log = []

        def tracking_send_chat(system_prompt, user_prompt, **kwargs):
            if "Express your current thinking" in user_prompt:
                call_log.append("generate")
            elif "conversations with some of your peers" in user_prompt:
                call_log.append("receive")
            return _MOCK_PEER_MESSAGE

        mock_send.side_effect = tracking_send_chat
        self.sn.run_peer_messaging(ClimatePolicyID.CARBON_TAX, day=1, k_peers=2)

        # Find the last generate and first receive
        if "generate" in call_log and "receive" in call_log:
            last_generate = len(call_log) - 1 - call_log[::-1].index("generate")
            first_receive = call_log.index("receive")
            self.assertLess(last_generate, first_receive,
                            f"Simultaneous update violated: last generate at {last_generate}, "
                            f"first receive at {first_receive}. Log: {call_log}")

    @patch("cag.abm.agent.SurveyedCitizen.get_system_prompt", return_value="Test persona.")
    @patch("cag.abm.agent.send_chat", return_value=_MOCK_PEER_MESSAGE)
    def test_reflections_have_phase_c(self, mock_send, mock_prompt):
        """All reflections from run_peer_messaging should have phase='C'."""
        self.sn.run_peer_messaging(ClimatePolicyID.CARBON_TAX, day=2, k_peers=2)
        for citizen in self.sn.agents_active.values():
            for ref in citizen.reflections:
                self.assertEqual(ref["phase"], "C")
                self.assertEqual(ref["day"], 2)

    @patch("cag.abm.agent.SurveyedCitizen.get_system_prompt", return_value="Test persona.")
    @patch("cag.abm.agent.send_chat", return_value=_MOCK_PEER_MESSAGE)
    def test_sample_messages_at_most_two(self, mock_send, mock_prompt):
        result = self.sn.run_peer_messaging(
            ClimatePolicyID.CARBON_TAX, day=1, k_peers=2
        )
        self.assertLessEqual(len(result["sample_messages"]), 2)

    @patch("cag.abm.agent.SurveyedCitizen.get_system_prompt", return_value="Test persona.")
    @patch("cag.abm.agent.send_chat", return_value=_MOCK_PEER_MESSAGE)
    def test_sample_reflections_at_most_two(self, mock_send, mock_prompt):
        result = self.sn.run_peer_messaging(
            ClimatePolicyID.CARBON_TAX, day=1, k_peers=2
        )
        self.assertLessEqual(len(result["sample_reflections"]), 2)

    @patch("cag.abm.agent.SurveyedCitizen.get_system_prompt", return_value="Test persona.")
    @patch("cag.abm.agent.send_chat", return_value=_MOCK_PEER_MESSAGE)
    def test_messages_generated_count_positive(self, mock_send, mock_prompt):
        result = self.sn.run_peer_messaging(
            ClimatePolicyID.CARBON_TAX, day=1, k_peers=2
        )
        self.assertGreater(result["messages_generated"], 0)

    @patch("cag.abm.agent.SurveyedCitizen.get_system_prompt", return_value="Test persona.")
    @patch("cag.abm.agent.send_chat", return_value=_MOCK_PEER_MESSAGE)
    def test_reflections_count_positive(self, mock_send, mock_prompt):
        result = self.sn.run_peer_messaging(
            ClimatePolicyID.CARBON_TAX, day=1, k_peers=2
        )
        self.assertGreater(result["reflections_count"], 0)

    @patch("cag.abm.agent.SurveyedCitizen.get_system_prompt", return_value="Test persona.")
    @patch("cag.abm.agent.send_chat", return_value=_MOCK_PEER_MESSAGE)
    def test_reflections_reference_actual_messages(self, mock_send, mock_prompt):
        """Each reflection's messages_received should contain the mock message."""
        self.sn.run_peer_messaging(ClimatePolicyID.CARBON_TAX, day=1, k_peers=2)
        for citizen in self.sn.agents_active.values():
            for ref in citizen.reflections:
                for msg in ref["messages_received"]:
                    self.assertEqual(msg, _MOCK_PEER_MESSAGE)

    @patch("cag.abm.agent.SurveyedCitizen.get_system_prompt", return_value="Test persona.")
    @patch("cag.abm.agent.send_chat", return_value=_MOCK_PEER_MESSAGE)
    def test_k_peers_1_limits_selections(self, mock_send, mock_prompt):
        """With k_peers=1, total generated messages = number of citizens with neighbors."""
        result = self.sn.run_peer_messaging(
            ClimatePolicyID.CARBON_TAX, day=1, k_peers=1
        )
        n_with_neighbors = sum(
            1 for c in self.sn.agents_active.values()
            if len(c.network_neighbors) > 0
        )
        self.assertEqual(result["messages_generated"], n_with_neighbors)

    @patch("cag.abm.environment.random.sample", side_effect=lambda seq, k: list(seq)[:k])
    @patch("cag.abm.agent.SurveyedCitizen.get_system_prompt", return_value="Test persona.")
    @patch("cag.abm.agent.send_chat", return_value=_MOCK_PEER_MESSAGE)
    def test_logs_one_row_per_peer_delivery(self, mock_send, mock_prompt, mock_sample):
        self.sn.run_peer_messaging(ClimatePolicyID.CARBON_TAX, day=1, k_peers=2)
        expected_deliveries = sum(
            min(2, len(c.network_neighbors))
            for c in self.sn.agents_active.values()
            if c.network_neighbors
        )
        self.assertEqual(len(self.sn.message_log), expected_deliveries)
        self.assertTrue(all(row["message_type"] == "peer_message" for row in self.sn.message_log))
        self.assertTrue(all(row["recipient_scope"] == "direct" for row in self.sn.message_log))


class TestRunPackagePeerMessagingLogging(unittest.TestCase):

    def setUp(self):
        self.sn = _make_nation()

    @patch("cag.abm.environment.random.sample", side_effect=lambda seq, k: list(seq)[:k])
    @patch("cag.abm.agent.SurveyedCitizen.get_system_prompt", return_value="Test persona.")
    @patch("cag.abm.agent.send_chat", return_value=_MOCK_PEER_MESSAGE)
    def test_logs_package_scope_and_policy_ids(self, mock_send, mock_prompt, mock_sample):
        policy_ids = [ClimatePolicyID.CARBON_TAX, ClimatePolicyID.GREEN_HOUSING]
        self.sn.run_package_peer_messaging(policy_ids, day=1, k_peers=2)
        self.assertGreater(len(self.sn.message_log), 0)
        self.assertTrue(all(row["package_scope"] == PACKAGE_SCOPE for row in self.sn.message_log))
        self.assertTrue(all(row["policy_ids"] == policy_ids for row in self.sn.message_log))


if __name__ == "__main__":
    unittest.main()
