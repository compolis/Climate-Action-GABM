"""
Tests for cag.abm.sim — simulation runner.

These tests mock the LLM calls and nation/agent internals so they run
without an API key. They DO require the gabm package (Python 3.12+).
Run with: python -m pytest tests/test_sim.py -v
"""
import json
import os
import sys
import tempfile
import unittest
from itertools import permutations
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../src")))

from cag.abm.attributes.opinion import ClimatePolicyID
from cag.abm.sim import (
    run_simulation,
    save_results,
    _collect_results,
    _serialise_config,
    SIM_CONFIG,
)


# ── Helpers ─────────────────────────────────────────────────────

def _make_mock_agent(agent_id, exposure="A-only"):
    """Create a mock agent with the minimum interface needed by sim.py."""
    agent = MagicMock()
    agent.id = agent_id
    agent.political_exposure = exposure
    agent.network_neighbors = []
    agent.opinion_history = {}
    agent.reflections = []

    def fake_survey(policy_id, day=0, **kwargs):
        history = agent.opinion_history.setdefault(policy_id, [])
        history.append((day, 1))  # always returns opinion=1

    def fake_manage_memory(day, policy, **kwargs):
        pass

    agent.administer_survey = MagicMock(side_effect=fake_survey)
    agent.manage_memory = MagicMock(side_effect=fake_manage_memory)
    return agent


def _make_mock_nation(n_agents=3):
    """Create a mock nation with n agents and fake broadcast/peer methods."""
    nation = MagicMock()
    agents = {}
    exposures = ["A-only", "B-only", "both"]
    for i in range(n_agents):
        exp = exposures[i % len(exposures)]
        agents[float(i)] = _make_mock_agent(float(i), exposure=exp)
    nation.agents_active = agents
    nation.political_agent_a = MagicMock()
    nation.political_agent_b = MagicMock()
    nation.political_agent_a.connected_citizens = []
    nation.political_agent_b.connected_citizens = []

    def fake_broadcast(phase, policy_id, day, **kwargs):
        for agent in agents.values():
            agent.reflections.append({
                "day": day, "phase": phase, "policy_id": policy_id,
                "text": f"Reflection on {phase} day {day}",
                "messages_received": ["msg"],
            })

    def fake_peer_messaging(policy_id, day, **kwargs):
        for agent in agents.values():
            agent.reflections.append({
                "day": day, "phase": "C", "policy_id": policy_id,
                "text": f"Peer reflection day {day}",
                "messages_received": ["peer_msg"],
            })

    def fake_eod_survey(policy_id, day, **kwargs):
        for agent in agents.values():
            history = agent.opinion_history.setdefault(policy_id, [])
            history.append((day, 1))

    nation.run_political_broadcast = MagicMock(side_effect=fake_broadcast)
    nation.run_peer_messaging = MagicMock(side_effect=fake_peer_messaging)
    nation.run_end_of_day_survey = MagicMock(side_effect=fake_eod_survey)
    return nation


# ── _serialise_config ───────────────────────────────────────────

class TestSerialiseConfig(unittest.TestCase):

    def test_enum_converted_to_string(self):
        config = {"target_policy": ClimatePolicyID.CARBON_TAX, "x": 42}
        result = _serialise_config(config)
        self.assertIsInstance(result["target_policy"], str)
        self.assertEqual(result["x"], 42)

    def test_days_list_enums_converted(self):
        config = {
            "days": [
                {"policy": ClimatePolicyID.CARBON_TAX, "phases": ["P-A", "C"]},
                {"policy": ClimatePolicyID.GREEN_HOUSING, "phases": ["P-B"]},
            ]
        }
        result = _serialise_config(config)
        for entry in result["days"]:
            self.assertIsInstance(entry["policy"], str)
            self.assertIsInstance(entry["phases"], list)

    def test_empty_days_list(self):
        config = {"days": []}
        result = _serialise_config(config)
        self.assertEqual(result["days"], [])

    def test_plain_values_unchanged(self):
        config = {"k_peers_per_day": 3, "p_intra": 0.15, "random_seed": 42}
        result = _serialise_config(config)
        self.assertEqual(result, config)

    def test_result_is_json_serialisable(self):
        config = {
            "days": [
                {"policy": ClimatePolicyID.CARBON_TAX, "phases": ["P-A"]},
            ],
            "random_seed": 42,
        }
        result = _serialise_config(config)
        # Should not raise
        json.dumps(result)


# ── _collect_results ────────────────────────────────────────────

class TestCollectResults(unittest.TestCase):

    def test_empty_nation(self):
        nation = MagicMock()
        nation.agents_active = {}
        results = _collect_results(nation, {"days": []})
        self.assertTrue(results["opinion_trajectories"].empty)
        self.assertTrue(results["reflections"].empty)

    def test_trajectories_schema(self):
        nation = _make_mock_nation(2)
        policy = ClimatePolicyID.CARBON_TAX
        for agent in nation.agents_active.values():
            agent.opinion_history = {policy: [(0, 1), (1, 2)]}
        results = _collect_results(nation, {})
        df = results["opinion_trajectories"]
        self.assertEqual(
            sorted(df.columns.tolist()),
            sorted(["agent_id", "day", "policy_id", "numeric"]),
        )
        self.assertEqual(len(df), 4)  # 2 agents * 2 entries

    def test_reflections_schema(self):
        nation = _make_mock_nation(2)
        policy = ClimatePolicyID.CARBON_TAX
        for agent in nation.agents_active.values():
            agent.reflections = [
                {"day": 1, "phase": "P-A", "policy_id": policy, "text": "hello"},
            ]
        results = _collect_results(nation, {})
        df = results["reflections"]
        self.assertEqual(
            sorted(df.columns.tolist()),
            sorted(["agent_id", "day", "phase", "policy_id", "text"]),
        )
        self.assertEqual(len(df), 2)

    def test_missing_policy_id_defaults_to_empty_string(self):
        nation = _make_mock_nation(1)
        agent = list(nation.agents_active.values())[0]
        agent.reflections = [{"day": 1, "phase": "C", "text": "hi"}]
        results = _collect_results(nation, {})
        self.assertEqual(results["reflections"].iloc[0]["policy_id"], "")

    def test_multiple_policies_collected(self):
        nation = _make_mock_nation(1)
        agent = list(nation.agents_active.values())[0]
        agent.opinion_history = {
            ClimatePolicyID.CARBON_TAX: [(0, 1), (1, 2)],
            ClimatePolicyID.GREEN_HOUSING: [(0, -1), (1, 0)],
        }
        results = _collect_results(nation, {})
        df = results["opinion_trajectories"]
        policies = set(df["policy_id"].unique())
        self.assertEqual(len(policies), 2)
        self.assertEqual(len(df), 4)

    def test_config_passed_through(self):
        nation = MagicMock()
        nation.agents_active = {}
        my_config = {"random_seed": 99, "days": []}
        results = _collect_results(nation, my_config)
        self.assertEqual(results["config"]["random_seed"], 99)


# ── save_results ────────────────────────────────────────────────

class TestSaveResults(unittest.TestCase):

    def test_files_created(self):
        import pandas as pd

        results = {
            "opinion_trajectories": pd.DataFrame([
                {"agent_id": 1, "day": 0, "policy_id": "CARBON_TAX", "numeric": 1},
            ]),
            "reflections": pd.DataFrame([
                {"agent_id": 1, "day": 1, "phase": "P-A",
                 "policy_id": "CARBON_TAX", "text": "hi"},
            ]),
            "config": {"days": [], "random_seed": 42},
        }
        with tempfile.TemporaryDirectory() as tmpdir:
            out_path = save_results(results, output_dir=tmpdir)
            self.assertTrue((out_path / "opinion_trajectories.csv").exists())
            self.assertTrue((out_path / "reflections.csv").exists())
            self.assertTrue((out_path / "config.json").exists())

    def test_config_json_valid(self):
        import pandas as pd

        results = {
            "opinion_trajectories": pd.DataFrame(),
            "reflections": pd.DataFrame(),
            "config": {"random_seed": 42, "days": []},
        }
        with tempfile.TemporaryDirectory() as tmpdir:
            out_path = save_results(results, output_dir=tmpdir)
            with open(out_path / "config.json") as f:
                saved = json.load(f)
            self.assertEqual(saved["random_seed"], 42)

    def test_timestamped_directory_created(self):
        import pandas as pd

        results = {
            "opinion_trajectories": pd.DataFrame(),
            "reflections": pd.DataFrame(),
            "config": {"days": []},
        }
        with tempfile.TemporaryDirectory() as tmpdir:
            out_path = save_results(results, output_dir=tmpdir)
            # Should be a subdirectory with a timestamp name
            self.assertNotEqual(str(out_path), tmpdir)
            self.assertTrue(out_path.name.replace("_", "").isdigit())


# ── run_simulation ──────────────────────────────────────────────

class TestRunSimulation(unittest.TestCase):

    @patch("cag.abm.sim.load_api_key", return_value="fake-key")
    def test_empty_days_returns_empty(self, mock_api):
        nation = _make_mock_nation(3)
        results = run_simulation({"days": []}, nation)
        self.assertTrue(results["opinion_trajectories"].empty)
        self.assertTrue(results["reflections"].empty)

    @patch("cag.abm.sim.load_api_key", return_value="fake-key")
    @patch("cag.abm.sim.PoliticalAgent")
    def test_baseline_survey_called(self, mock_pa_cls, mock_api):
        nation = _make_mock_nation(3)
        policy = ClimatePolicyID.CARBON_TAX
        config = {"days": [{"policy": policy, "phases": ["P-A"]}]}
        run_simulation(config, nation)
        for agent in nation.agents_active.values():
            self.assertTrue(agent.administer_survey.called)

    @patch("cag.abm.sim.load_api_key", return_value="fake-key")
    @patch("cag.abm.sim.PoliticalAgent")
    def test_all_three_phases_called(self, mock_pa_cls, mock_api):
        nation = _make_mock_nation(3)
        policy = ClimatePolicyID.CARBON_TAX
        config = {"days": [{"policy": policy, "phases": ["P-A", "P-B", "C"]}]}
        run_simulation(config, nation)

        broadcast_phases = [c[0][0] for c in nation.run_political_broadcast.call_args_list]
        self.assertIn("P-A", broadcast_phases)
        self.assertIn("P-B", broadcast_phases)
        nation.run_peer_messaging.assert_called_once()

    @patch("cag.abm.sim.load_api_key", return_value="fake-key")
    @patch("cag.abm.sim.PoliticalAgent")
    def test_phase_order_respected(self, mock_pa_cls, mock_api):
        """Phases should be called in the order given, not sorted."""
        nation = _make_mock_nation(3)
        policy = ClimatePolicyID.CARBON_TAX
        # C first, then P-B only
        config = {"days": [{"policy": policy, "phases": ["C", "P-B"]}]}
        call_order = []
        nation.run_peer_messaging.side_effect = lambda *a, **kw: call_order.append("C")
        nation.run_political_broadcast.side_effect = lambda phase, *a, **kw: call_order.append(phase)
        nation.run_end_of_day_survey.side_effect = lambda *a, **kw: None

        run_simulation(config, nation)
        self.assertEqual(call_order, ["C", "P-B"])

    @patch("cag.abm.sim.load_api_key", return_value="fake-key")
    @patch("cag.abm.sim.PoliticalAgent")
    def test_multi_day_calls_correct_policies(self, mock_pa_cls, mock_api):
        nation = _make_mock_nation(2)
        config = {
            "days": [
                {"policy": ClimatePolicyID.CARBON_TAX, "phases": ["P-A"]},
                {"policy": ClimatePolicyID.GREEN_HOUSING, "phases": ["P-B"]},
            ],
        }
        run_simulation(config, nation)
        # End-of-day survey called with correct policy each day
        eod_calls = nation.run_end_of_day_survey.call_args_list
        self.assertEqual(len(eod_calls), 2)
        self.assertEqual(eod_calls[0][0][0], ClimatePolicyID.CARBON_TAX)
        self.assertEqual(eod_calls[1][0][0], ClimatePolicyID.GREEN_HOUSING)

    @patch("cag.abm.sim.load_api_key", return_value="fake-key")
    @patch("cag.abm.sim.PoliticalAgent")
    def test_memory_management_called_each_day(self, mock_pa_cls, mock_api):
        nation = _make_mock_nation(2)
        config = {
            "days": [
                {"policy": ClimatePolicyID.CARBON_TAX, "phases": ["P-A"]},
                {"policy": ClimatePolicyID.CARBON_TAX, "phases": ["P-A"]},
                {"policy": ClimatePolicyID.CARBON_TAX, "phases": ["P-A"]},
            ],
        }
        run_simulation(config, nation)
        for agent in nation.agents_active.values():
            self.assertEqual(agent.manage_memory.call_count, 3)

    @patch("cag.abm.sim.load_api_key", return_value="fake-key")
    @patch("cag.abm.sim.PoliticalAgent")
    def test_unknown_phase_does_not_crash(self, mock_pa_cls, mock_api):
        nation = _make_mock_nation(2)
        config = {
            "days": [{"policy": ClimatePolicyID.CARBON_TAX, "phases": ["P-A", "BADPHASE"]}],
        }
        results = run_simulation(config, nation)
        self.assertIsInstance(results, dict)

    @patch("cag.abm.sim.load_api_key", return_value="fake-key")
    @patch("cag.abm.sim.PoliticalAgent")
    def test_network_setup_called(self, mock_pa_cls, mock_api):
        nation = _make_mock_nation(3)
        config = {"days": [{"policy": ClimatePolicyID.CARBON_TAX, "phases": ["C"]}]}
        run_simulation(config, nation)
        nation.assign_political_exposure.assert_called_once()
        nation.create_network.assert_called_once()
        nation.assign_network_blocks.assert_called_once()

    @patch("cag.abm.sim.load_api_key", return_value="fake-key")
    @patch("cag.abm.sim.PoliticalAgent")
    def test_results_contain_config(self, mock_pa_cls, mock_api):
        nation = _make_mock_nation(2)
        config = {
            "days": [{"policy": ClimatePolicyID.CARBON_TAX, "phases": ["P-A"]}],
            "random_seed": 99,
        }
        results = run_simulation(config, nation)
        self.assertEqual(results["config"]["random_seed"], 99)

    @patch("cag.abm.sim.load_api_key", return_value="fake-key")
    @patch("cag.abm.sim.PoliticalAgent")
    def test_day_numbering_starts_at_1(self, mock_pa_cls, mock_api):
        """Daily loop days should be 1-indexed (day 0 = baseline)."""
        nation = _make_mock_nation(2)
        config = {
            "days": [
                {"policy": ClimatePolicyID.CARBON_TAX, "phases": ["P-A"]},
                {"policy": ClimatePolicyID.CARBON_TAX, "phases": ["P-A"]},
            ],
        }
        run_simulation(config, nation)
        broadcast_calls = nation.run_political_broadcast.call_args_list
        days_called = [c[0][2] for c in broadcast_calls]  # 3rd positional arg = day
        self.assertEqual(days_called, [1, 2])


# ── Phase ordering acceptance ─────────────────────────────────

class TestAllPhaseOrderings(unittest.TestCase):
    """All 6 permutations of [P-A, P-B, C] should run without error."""

    ALL_ORDERINGS = list(permutations(["P-A", "P-B", "C"]))

    @patch("cag.abm.sim.load_api_key", return_value="fake-key")
    @patch("cag.abm.sim.PoliticalAgent")
    def test_all_six_orderings_produce_results(self, mock_pa_cls, mock_api):
        policy = ClimatePolicyID.CARBON_TAX
        for phases in self.ALL_ORDERINGS:
            with self.subTest(phases=phases):
                nation = _make_mock_nation(3)
                config = {"days": [{"policy": policy, "phases": list(phases)}]}
                results = run_simulation(config, nation)
                self.assertFalse(results["opinion_trajectories"].empty,
                                 f"No trajectories for ordering {phases}")
                self.assertGreater(len(results["reflections"]), 0,
                                   f"No reflections for ordering {phases}")

    @patch("cag.abm.sim.load_api_key", return_value="fake-key")
    @patch("cag.abm.sim.PoliticalAgent")
    def test_different_orderings_produce_different_call_sequences(self, mock_pa_cls, mock_api):
        """Different phase orderings should execute phases in different orders."""
        policy = ClimatePolicyID.CARBON_TAX
        call_sequences = {}

        for phases in self.ALL_ORDERINGS:
            nation = _make_mock_nation(3)
            call_order = []
            nation.run_peer_messaging.side_effect = lambda *a, **kw: call_order.append("C")
            nation.run_political_broadcast.side_effect = lambda phase, *a, **kw: call_order.append(phase)
            nation.run_end_of_day_survey.side_effect = lambda *a, **kw: None

            config = {"days": [{"policy": policy, "phases": list(phases)}]}
            run_simulation(config, nation)
            call_sequences[phases] = tuple(call_order)

        # All 6 orderings should produce distinct call sequences
        unique_sequences = set(call_sequences.values())
        self.assertEqual(len(unique_sequences), 6,
                         f"Expected 6 distinct call sequences, got {len(unique_sequences)}: "
                         f"{call_sequences}")


# ── SIM_CONFIG defaults ────────────────────────────────────────

class TestSimConfig(unittest.TestCase):

    def test_has_required_keys(self):
        required = [
            "days", "k_peers_per_day", "p_intra", "p_inter",
            "llm_model", "llm_provider", "llm_temperature", "random_seed",
        ]
        for key in required:
            self.assertIn(key, SIM_CONFIG, f"Missing key: {key}")

    def test_days_entries_have_policy_and_phases(self):
        for entry in SIM_CONFIG["days"]:
            self.assertIn("policy", entry)
            self.assertIn("phases", entry)
            self.assertIsInstance(entry["phases"], list)
            for phase in entry["phases"]:
                self.assertIn(phase, ("P-A", "P-B", "C"),
                              f"Unexpected phase in SIM_CONFIG: {phase}")


if __name__ == "__main__":
    unittest.main()
