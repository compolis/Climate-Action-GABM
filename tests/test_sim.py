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

from cag.abm.attributes.opinion import (
    ALL_CLIMATE_POLICIES,
    ClimatePolicyID,
    PACKAGE_SCOPE,
    PRO_CLIMATE_INDEX_COLUMN,
)
from cag.abm.sim import (
    run_simulation,
    save_results,
    save_result_plots,
    build_opinion_shares,
    build_package_index_shares,
    collect_ground_truth,
    collect_package_ground_truth,
    _collect_results,
    _resolve_day_phases,
    _serialise_config,
    make_phases,
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
    agent.daily_summaries = {}
    agent.survey_reasoning = {}
    agent.survey_raw_response = {}
    agent.get_real_package_index = MagicMock(return_value=0.5)

    def fake_get_real_survey_response(policy_id):
        return 0

    def fake_survey(policy_id, day=0, **kwargs):
        history = agent.opinion_history.setdefault(policy_id, [])
        history.append((day, 1))  # always returns opinion=1
        raw = agent.survey_raw_response.setdefault(policy_id, [])
        raw.append((day, f"raw response for day {day}"))
        if kwargs.get("debias"):
            reasoning = agent.survey_reasoning.setdefault(policy_id, [])
            reasoning.append((day, f"Reasoning for day {day}"))

    def fake_seed_gt(policy_id, day=0):
        history = agent.opinion_history.setdefault(policy_id, [])
        history.append((day, 2))  # GT marker distinct from llm_survey value
        return 2

    def fake_seed_with_rationale(policy_id, day=0, **kwargs):
        history = agent.opinion_history.setdefault(policy_id, [])
        history.append((day, 2))
        reasoning = agent.survey_reasoning.setdefault(policy_id, [])
        reasoning.append((day, f"Rationale for day {day}"))
        return 2, f"Rationale for day {day}"

    def fake_manage_memory(day, policy, **kwargs):
        agent.daily_summaries[(day, policy)] = f"Summary for day {day}"

    agent.administer_survey = MagicMock(side_effect=fake_survey)
    agent.manage_memory = MagicMock(side_effect=fake_manage_memory)
    agent.get_real_survey_response = MagicMock(side_effect=fake_get_real_survey_response)
    agent.seed_opinion_from_ground_truth = MagicMock(side_effect=fake_seed_gt)
    agent.seed_opinion_with_rationale = MagicMock(side_effect=fake_seed_with_rationale)
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
    nation.message_log = []

    def fake_broadcast(phase, policy_id, day, **kwargs):
        for agent in agents.values():
            nation.message_log.append({
                "day": day,
                "phase": phase,
                "message_type": "political_broadcast",
                "sender_type": "political_agent",
                "sender_id": phase,
                "sender_side": "pro_climate" if phase == "P-A" else "anti_climate",
                "recipient_id": agent.id,
                "recipient_scope": "broadcast",
                "policy_id": policy_id,
                "package_scope": "",
                "policy_ids": [],
                "message_text": f"Broadcast {phase} day {day}",
            })
        for agent in agents.values():
            agent.reflections.append({
                "day": day, "phase": phase, "policy_id": policy_id,
                "text": f"Reflection on {phase} day {day}",
                "messages_received": ["msg"],
            })

    def fake_peer_messaging(policy_id, day, **kwargs):
        for agent in agents.values():
            nation.message_log.append({
                "day": day,
                "phase": "C",
                "message_type": "peer_message",
                "sender_type": "citizen",
                "sender_id": agent.id,
                "sender_side": "",
                "recipient_id": agent.id,
                "recipient_scope": "direct",
                "policy_id": policy_id,
                "package_scope": "",
                "policy_ids": [],
                "message_text": f"Peer message day {day}",
            })
            agent.reflections.append({
                "day": day, "phase": "C", "policy_id": policy_id,
                "text": f"Peer reflection day {day}",
                "messages_received": ["peer_msg"],
            })

    def fake_package_broadcast(phase, policy_ids, day, **kwargs):
        for agent in agents.values():
            nation.message_log.append({
                "day": day,
                "phase": phase,
                "message_type": "political_broadcast",
                "sender_type": "political_agent",
                "sender_id": phase,
                "sender_side": "pro_climate" if phase == "P-A" else "anti_climate",
                "recipient_id": agent.id,
                "recipient_scope": "broadcast",
                "policy_id": "",
                "package_scope": PACKAGE_SCOPE,
                "policy_ids": list(policy_ids),
                "message_text": f"Package broadcast {phase} day {day}",
            })
            agent.reflections.append({
                "day": day,
                "phase": phase,
                "policy_id": PACKAGE_SCOPE,
                "policy_ids": list(policy_ids),
                "text": f"Package reflection on {phase} day {day}",
                "messages_received": ["package_msg"],
            })

    def fake_package_peer_messaging(policy_ids, day, **kwargs):
        for agent in agents.values():
            nation.message_log.append({
                "day": day,
                "phase": "C",
                "message_type": "peer_message",
                "sender_type": "citizen",
                "sender_id": agent.id,
                "sender_side": "",
                "recipient_id": agent.id,
                "recipient_scope": "direct",
                "policy_id": "",
                "package_scope": PACKAGE_SCOPE,
                "policy_ids": list(policy_ids),
                "message_text": f"Package peer message day {day}",
            })
            agent.reflections.append({
                "day": day,
                "phase": "C",
                "policy_id": PACKAGE_SCOPE,
                "policy_ids": list(policy_ids),
                "text": f"Package peer reflection day {day}",
                "messages_received": ["package_peer_msg"],
            })

    def fake_eod_survey(policy_id, day, **kwargs):
        for agent in agents.values():
            history = agent.opinion_history.setdefault(policy_id, [])
            history.append((day, 1))

    nation.run_political_broadcast = MagicMock(side_effect=fake_broadcast)
    nation.run_peer_messaging = MagicMock(side_effect=fake_peer_messaging)
    nation.run_package_broadcast = MagicMock(side_effect=fake_package_broadcast)
    nation.run_package_peer_messaging = MagicMock(side_effect=fake_package_peer_messaging)
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

    def test_package_policies_list_enums_converted(self):
        config = {"package_policies": list(ALL_CLIMATE_POLICIES)}
        result = _serialise_config(config)
        self.assertEqual(len(result["package_policies"]), len(ALL_CLIMATE_POLICIES))
        for policy_id in result["package_policies"]:
            self.assertIsInstance(policy_id, str)

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
                {
                    "day": 1,
                    "phase": "P-A",
                    "policy_id": policy,
                    "text": "hello",
                    "messages_received": ["msg"],
                },
            ]
        results = _collect_results(nation, {})
        df = results["reflections"]
        self.assertEqual(
            sorted(df.columns.tolist()),
            sorted([
                "agent_id",
                "day",
                "phase",
                "policy_id",
                "package_scope",
                "policy_ids_json",
                "messages_received_json",
                "messages_received_count",
                "text",
            ]),
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

    def test_package_index_schema(self):
        nation = _make_mock_nation(1)
        agent = list(nation.agents_active.values())[0]
        agent.opinion_history = {
            policy_id: [(0, index), (1, index + 1)]
            for index, policy_id in enumerate(ALL_CLIMATE_POLICIES)
        }
        results = _collect_results(
            nation,
            {"communication_mode": "package", "package_policies": list(ALL_CLIMATE_POLICIES)},
        )
        df = results["package_index_trajectories"]
        self.assertEqual(
            sorted(df.columns.tolist()),
            sorted([
                "agent_id", "day", "index_name", "package_index",
                "package_scope",
            ]),
        )
        self.assertEqual(df.iloc[0]["index_name"], PRO_CLIMATE_INDEX_COLUMN)
        self.assertEqual(df.iloc[0]["package_scope"], PACKAGE_SCOPE)

    def test_collects_messages_reasoning_summaries_and_ground_truth(self):
        nation = _make_mock_nation(1)
        agent = list(nation.agents_active.values())[0]
        policy = ClimatePolicyID.CARBON_TAX
        agent.opinion_history = {policy: [(0, 1)]}
        agent.reflections = [{
            "day": 1,
            "phase": "P-A",
            "policy_id": policy,
            "text": "hello",
            "messages_received": ["msg"],
        }]
        agent.survey_reasoning = {policy: [(0, "reasoning")]}
        agent.survey_raw_response = {policy: [(0, "raw text")]}
        agent.daily_summaries = {(1, policy): "summary"}
        nation.message_log = [{
            "day": 1,
            "phase": "P-A",
            "message_type": "political_broadcast",
            "sender_type": "political_agent",
            "sender_id": "agent_a",
            "sender_side": "pro_climate",
            "recipient_id": agent.id,
            "recipient_scope": "broadcast",
            "policy_id": policy,
            "package_scope": "",
            "policy_ids": [],
            "message_text": "message",
        }]

        results = _collect_results(nation, {})

        self.assertEqual(len(results["messages"]), 1)
        self.assertEqual(len(results["survey_reasoning"]), 1)
        self.assertEqual(len(results["daily_summaries"]), 1)
        self.assertEqual(len(results["ground_truth"]), len(results["ground_truth"]))
        self.assertEqual(len(results["package_ground_truth"]), 1)


class TestBuildOpinionShares(unittest.TestCase):

    def test_bins_and_percentages_correct(self):
        import pandas as pd

        results = {
            "opinion_trajectories": pd.DataFrame([
                {"agent_id": 1, "day": 0, "policy_id": "CARBON_TAX", "numeric": -3},
                {"agent_id": 2, "day": 0, "policy_id": "CARBON_TAX", "numeric": -1},
                {"agent_id": 3, "day": 0, "policy_id": "CARBON_TAX", "numeric": 0},
                {"agent_id": 4, "day": 0, "policy_id": "CARBON_TAX", "numeric": 1},
                {"agent_id": 5, "day": 0, "policy_id": "CARBON_TAX", "numeric": 3},
            ]),
        }

        share_df = build_opinion_shares(results)
        row = share_df.iloc[0]

        self.assertEqual(row["n_support"], 2)
        self.assertEqual(row["n_neutral"], 1)
        self.assertEqual(row["n_against"], 2)
        self.assertEqual(row["support_pct"], 40.0)
        self.assertEqual(row["neutral_pct"], 20.0)
        self.assertEqual(row["against_pct"], 40.0)

    def test_percentages_sum_to_one_hundred(self):
        import pandas as pd
        import numpy as np

        results = {
            "opinion_trajectories": pd.DataFrame([
                {"agent_id": 1, "day": 0, "policy_id": "CARBON_TAX", "numeric": -1},
                {"agent_id": 2, "day": 0, "policy_id": "CARBON_TAX", "numeric": 0},
                {"agent_id": 3, "day": 0, "policy_id": "CARBON_TAX", "numeric": 1},
                {"agent_id": 1, "day": 1, "policy_id": "CARBON_TAX", "numeric": 1},
                {"agent_id": 2, "day": 1, "policy_id": "CARBON_TAX", "numeric": 1},
                {"agent_id": 3, "day": 1, "policy_id": "CARBON_TAX", "numeric": -1},
            ]),
        }

        share_df = build_opinion_shares(results)
        totals = share_df[["support_pct", "neutral_pct", "against_pct"]].sum(axis=1)
        self.assertTrue(np.allclose(totals, 100.0))


class TestBuildPackageIndexShares(unittest.TestCase):

    def test_bins_and_percentages_correct(self):
        import pandas as pd

        results = {
            "package_index_trajectories": pd.DataFrame([
                {
                    "agent_id": 1,
                    "day": 0,
                    "index_name": PRO_CLIMATE_INDEX_COLUMN,
                    "package_scope": PACKAGE_SCOPE,
                    "package_index": -1.0,
                },
                {
                    "agent_id": 2,
                    "day": 0,
                    "index_name": PRO_CLIMATE_INDEX_COLUMN,
                    "package_scope": PACKAGE_SCOPE,
                    "package_index": 0.0,
                },
                {
                    "agent_id": 3,
                    "day": 0,
                    "index_name": PRO_CLIMATE_INDEX_COLUMN,
                    "package_scope": PACKAGE_SCOPE,
                    "package_index": 1.0,
                },
            ]),
        }

        share_df = build_package_index_shares(results)
        row = share_df.iloc[0]

        self.assertEqual(row["n_support"], 1)
        self.assertEqual(row["n_neutral"], 1)
        self.assertEqual(row["n_against"], 1)
        self.assertAlmostEqual(row["support_pct"], 100.0 / 3.0)
        self.assertAlmostEqual(row["neutral_pct"], 100.0 / 3.0)
        self.assertAlmostEqual(row["against_pct"], 100.0 / 3.0)

    def test_percentages_sum_to_one_hundred(self):
        import numpy as np
        import pandas as pd

        results = {
            "package_index_trajectories": pd.DataFrame([
                {
                    "agent_id": 1,
                    "day": 0,
                    "index_name": PRO_CLIMATE_INDEX_COLUMN,
                    "package_scope": PACKAGE_SCOPE,
                    "package_index": -0.5,
                },
                {
                    "agent_id": 2,
                    "day": 0,
                    "index_name": PRO_CLIMATE_INDEX_COLUMN,
                    "package_scope": PACKAGE_SCOPE,
                    "package_index": 0.0,
                },
                {
                    "agent_id": 3,
                    "day": 0,
                    "index_name": PRO_CLIMATE_INDEX_COLUMN,
                    "package_scope": PACKAGE_SCOPE,
                    "package_index": 0.5,
                },
                {
                    "agent_id": 1,
                    "day": 1,
                    "index_name": PRO_CLIMATE_INDEX_COLUMN,
                    "package_scope": PACKAGE_SCOPE,
                    "package_index": 1.0,
                },
                {
                    "agent_id": 2,
                    "day": 1,
                    "index_name": PRO_CLIMATE_INDEX_COLUMN,
                    "package_scope": PACKAGE_SCOPE,
                    "package_index": 1.0,
                },
                {
                    "agent_id": 3,
                    "day": 1,
                    "index_name": PRO_CLIMATE_INDEX_COLUMN,
                    "package_scope": PACKAGE_SCOPE,
                    "package_index": -1.0,
                },
            ]),
        }

        share_df = build_package_index_shares(results)
        totals = share_df[["support_pct", "neutral_pct", "against_pct"]].sum(axis=1)
        self.assertTrue(np.allclose(totals, 100.0))


# ── save_results ────────────────────────────────────────────────

class TestSaveResults(unittest.TestCase):

    def test_files_created(self):
        import pandas as pd

        results = {
            "opinion_trajectories": pd.DataFrame([
                {"agent_id": 1, "day": 0, "policy_id": "CARBON_TAX", "numeric": 1},
            ]),
            "reflections": pd.DataFrame([
                {
                    "agent_id": 1,
                    "day": 1,
                    "phase": "P-A",
                    "policy_id": "CARBON_TAX",
                    "package_scope": "",
                    "policy_ids_json": "[]",
                    "messages_received_json": "[\"msg\"]",
                    "messages_received_count": 1,
                    "text": "hi",
                },
            ]),
            "messages": pd.DataFrame([
                {
                    "day": 1,
                    "phase": "P-A",
                    "message_type": "political_broadcast",
                    "sender_type": "political_agent",
                    "sender_id": "agent_a",
                    "sender_side": "pro_climate",
                    "recipient_id": 1,
                    "recipient_scope": "broadcast",
                    "policy_id": "CARBON_TAX",
                    "package_scope": "",
                    "policy_ids_json": "[]",
                    "message_text": "hello",
                },
            ]),
            "survey_reasoning": pd.DataFrame([
                {"agent_id": 1, "day": 0, "policy_id": "CARBON_TAX", "reasoning": "why"},
            ]),
            "daily_summaries": pd.DataFrame([
                {"agent_id": 1, "day": 1, "policy_id": "CARBON_TAX", "package_scope": "", "summary": "sum"},
            ]),
            "ground_truth": pd.DataFrame([
                {"agent_id": 1, "policy_id": "CARBON_TAX", "ground_truth": 1},
            ]),
            "package_ground_truth": pd.DataFrame([
                {"agent_id": 1, "index_name": PRO_CLIMATE_INDEX_COLUMN, "ground_truth": 0.5},
            ]),
            "package_index_trajectories": pd.DataFrame([
                {
                    "agent_id": 1,
                    "day": 0,
                    "index_name": PRO_CLIMATE_INDEX_COLUMN,
                    "package_scope": PACKAGE_SCOPE,
                    "package_index": 0.5,
                },
            ]),
            "config": {"days": [], "random_seed": 42},
        }
        with tempfile.TemporaryDirectory() as tmpdir:
            out_path = save_results(results, output_dir=tmpdir)
            self.assertTrue((out_path / "opinion_trajectories.csv").exists())
            self.assertTrue((out_path / "opinion_shares.csv").exists())
            self.assertTrue((out_path / "package_index_shares.csv").exists())
            self.assertTrue((out_path / "reflections.csv").exists())
            self.assertTrue((out_path / "messages.csv").exists())
            self.assertTrue((out_path / "survey_reasoning.csv").exists())
            self.assertTrue((out_path / "daily_summaries.csv").exists())
            self.assertTrue((out_path / "ground_truth.csv").exists())
            self.assertTrue((out_path / "package_ground_truth.csv").exists())
            self.assertTrue((out_path / "config.json").exists())


class TestSaveResultPlots(unittest.TestCase):

    def test_plot_files_created(self):
        import matplotlib
        import pandas as pd

        matplotlib.use("Agg")

        results = {
            "opinion_trajectories": pd.DataFrame([
                {"agent_id": 1, "day": 0, "policy_id": str(ClimatePolicyID.CARBON_TAX), "numeric": -1},
                {"agent_id": 2, "day": 0, "policy_id": str(ClimatePolicyID.CARBON_TAX), "numeric": 1},
                {"agent_id": 1, "day": 1, "policy_id": str(ClimatePolicyID.CARBON_TAX), "numeric": 0},
                {"agent_id": 2, "day": 1, "policy_id": str(ClimatePolicyID.CARBON_TAX), "numeric": 2},
            ]),
            "package_index_trajectories": pd.DataFrame([
                {
                    "agent_id": 1,
                    "day": 0,
                    "index_name": PRO_CLIMATE_INDEX_COLUMN,
                    "package_scope": PACKAGE_SCOPE,
                    "package_index": -0.5,
                },
                {
                    "agent_id": 2,
                    "day": 0,
                    "index_name": PRO_CLIMATE_INDEX_COLUMN,
                    "package_scope": PACKAGE_SCOPE,
                    "package_index": 0.5,
                },
                {
                    "agent_id": 1,
                    "day": 1,
                    "index_name": PRO_CLIMATE_INDEX_COLUMN,
                    "package_scope": PACKAGE_SCOPE,
                    "package_index": 0.0,
                },
                {
                    "agent_id": 2,
                    "day": 1,
                    "index_name": PRO_CLIMATE_INDEX_COLUMN,
                    "package_scope": PACKAGE_SCOPE,
                    "package_index": 1.0,
                },
            ]),
            "package_ground_truth": pd.DataFrame([
                {
                    "agent_id": 1,
                    "index_name": PRO_CLIMATE_INDEX_COLUMN,
                    "ground_truth": 0.25,
                },
                {
                    "agent_id": 2,
                    "index_name": PRO_CLIMATE_INDEX_COLUMN,
                    "ground_truth": 0.25,
                },
            ]),
        }

        with tempfile.TemporaryDirectory() as tmpdir:
            out_path = save_results({**results, "config": {"days": []}}, output_dir=tmpdir)
            plot_paths = save_result_plots(results, out_path)
            self.assertTrue((out_path / "opinion_trajectories.png").exists())
            self.assertTrue((out_path / "opinion_shares.png").exists())
            self.assertTrue((out_path / "package_index_trajectories.png").exists())
            self.assertTrue((out_path / "package_index_shares.png").exists())
            self.assertIn("opinion_trajectories", plot_paths)
            self.assertIn("opinion_shares", plot_paths)
            self.assertIn("package_index_trajectories", plot_paths)
            self.assertIn("package_index_shares", plot_paths)

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

    def test_package_index_file_created_when_present(self):
        import pandas as pd

        results = {
            "opinion_trajectories": pd.DataFrame(),
            "package_index_trajectories": pd.DataFrame([
                {
                    "agent_id": 1,
                    "day": 0,
                    "index_name": PRO_CLIMATE_INDEX_COLUMN,
                    "package_scope": PACKAGE_SCOPE,
                    "package_index": 0.5,
                },
            ]),
            "reflections": pd.DataFrame(),
            "config": {"days": []},
        }
        with tempfile.TemporaryDirectory() as tmpdir:
            out_path = save_results(results, output_dir=tmpdir)
            self.assertTrue((out_path / "package_index_trajectories.csv").exists())


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
        config = {
            "communication_mode": "single_policy",
            "day0_anchor": "llm_survey",
            "days": [{"policy": policy, "phases": ["P-A"]}],
        }
        run_simulation(config, nation)
        for agent in nation.agents_active.values():
            self.assertTrue(agent.administer_survey.called)

    @patch("cag.abm.sim.load_api_key", return_value="fake-key")
    @patch("cag.abm.sim.PoliticalAgent")
    def test_all_three_phases_called(self, mock_pa_cls, mock_api):
        nation = _make_mock_nation(3)
        policy = ClimatePolicyID.CARBON_TAX
        config = {
            "communication_mode": "single_policy",
            "day0_anchor": "llm_survey",
            "days": [{"policy": policy, "phases": ["P-A", "P-B", "C"]}],
        }
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
        config = {
            "communication_mode": "single_policy",
            "day0_anchor": "llm_survey",
            "days": [{"policy": policy, "phases": ["C", "P-B"]}],
        }
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
            "communication_mode": "single_policy",
            "day0_anchor": "llm_survey",
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
            "communication_mode": "single_policy",
            "day0_anchor": "llm_survey",
            "days": [
                {"policy": ClimatePolicyID.CARBON_TAX, "phases": ["P-A"]},
                {"policy": ClimatePolicyID.CARBON_TAX, "phases": ["P-A"]},
            ],
        }
        run_simulation(config, nation)
        broadcast_calls = nation.run_political_broadcast.call_args_list
        days_called = [c[0][2] for c in broadcast_calls]  # 3rd positional arg = day
        self.assertEqual(days_called, [1, 2])

    @patch("cag.abm.sim.load_api_key", return_value="fake-key")
    @patch("cag.abm.sim.PoliticalAgent")
    def test_package_mode_baseline_surveys_all_policies(self, mock_pa_cls, mock_api):
        nation = _make_mock_nation(2)
        config = {
            "communication_mode": "package",
            "day0_anchor": "llm_survey",
            "package_policies": list(ALL_CLIMATE_POLICIES),
            "days": [{"phases": []}],
        }
        run_simulation(config, nation)
        for agent in nation.agents_active.values():
            self.assertEqual(agent.administer_survey.call_count, len(ALL_CLIMATE_POLICIES))

    @patch("cag.abm.sim.load_api_key", return_value="fake-key")
    @patch("cag.abm.sim.PoliticalAgent")
    def test_package_mode_uses_bundled_phase_methods(self, mock_pa_cls, mock_api):
        nation = _make_mock_nation(2)
        config = {
            "communication_mode": "package",
            "package_policies": list(ALL_CLIMATE_POLICIES),
            "days": [{"phases": ["P-A", "P-B", "C"]}],
        }
        run_simulation(config, nation)
        self.assertEqual(nation.run_package_broadcast.call_count, 2)
        nation.run_package_peer_messaging.assert_called_once()
        nation.run_political_broadcast.assert_not_called()
        nation.run_peer_messaging.assert_not_called()

    @patch("cag.abm.sim.load_api_key", return_value="fake-key")
    @patch("cag.abm.sim.PoliticalAgent")
    def test_package_mode_surveys_all_policies_each_day(self, mock_pa_cls, mock_api):
        nation = _make_mock_nation(2)
        config = {
            "communication_mode": "package",
            "package_policies": list(ALL_CLIMATE_POLICIES),
            "days": [{"phases": []}],
        }
        run_simulation(config, nation)
        self.assertEqual(nation.run_end_of_day_survey.call_count, len(ALL_CLIMATE_POLICIES))
        called_policies = {call.args[0] for call in nation.run_end_of_day_survey.call_args_list}
        self.assertEqual(called_policies, set(ALL_CLIMATE_POLICIES))

    @patch("cag.abm.sim.load_api_key", return_value="fake-key")
    @patch("cag.abm.sim.PoliticalAgent")
    def test_package_mode_memory_uses_package_scope(self, mock_pa_cls, mock_api):
        nation = _make_mock_nation(2)
        config = {
            "communication_mode": "package",
            "package_policies": list(ALL_CLIMATE_POLICIES),
            "days": [{"phases": []}],
        }
        run_simulation(config, nation)
        for agent in nation.agents_active.values():
            self.assertEqual(agent.manage_memory.call_args[0][1], PACKAGE_SCOPE)

    @patch("cag.abm.sim.load_api_key", return_value="fake-key")
    @patch("cag.abm.sim.PoliticalAgent")
    def test_package_mode_results_include_index_trajectories(self, mock_pa_cls, mock_api):
        nation = _make_mock_nation(2)
        config = {
            "communication_mode": "package",
            "package_policies": list(ALL_CLIMATE_POLICIES),
            "days": [{"phases": []}],
        }
        results = run_simulation(config, nation)
        self.assertIn("package_index_trajectories", results)
        self.assertFalse(results["package_index_trajectories"].empty)

    @patch("cag.abm.sim.load_api_key", return_value="fake-key")
    @patch("cag.abm.sim.PoliticalAgent")
    def test_results_include_research_artifacts(self, mock_pa_cls, mock_api):
        nation = _make_mock_nation(2)
        config = {
            "days": [{"policy": ClimatePolicyID.CARBON_TAX, "phases": ["P-A", "C"]}],
            "debias": True,
        }
        results = run_simulation(config, nation)
        self.assertIn("messages", results)
        self.assertIn("survey_reasoning", results)
        self.assertIn("daily_summaries", results)
        self.assertIn("ground_truth", results)
        self.assertIn("package_ground_truth", results)
        self.assertFalse(results["messages"].empty)
        self.assertFalse(results["survey_reasoning"].empty)
        self.assertFalse(results["daily_summaries"].empty)
        self.assertFalse(results["ground_truth"].empty)


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

            config = {
                "communication_mode": "single_policy",
                "day0_anchor": "llm_survey",
                "days": [{"policy": policy, "phases": list(phases)}],
            }
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

    def test_days_entries_have_phases(self):
        # Default day plan is package-mode: no per-day ``policy`` key.
        for entry in SIM_CONFIG["days"]:
            self.assertIn("phases", entry)
            self.assertIsInstance(entry["phases"], list)
            for phase in entry["phases"]:
                self.assertIn(phase, ("P-A", "P-B", "C"),
                              f"Unexpected phase in SIM_CONFIG: {phase}")

    def test_debias_default_true(self):
        # Research canon since v0.3 (NB15 / Run 4).
        self.assertIn("debias", SIM_CONFIG)
        self.assertIs(SIM_CONFIG["debias"], True)

    def test_thinking_default_false(self):
        self.assertIn("thinking", SIM_CONFIG)
        self.assertIs(SIM_CONFIG["thinking"], False)

    def test_survey_model_default_none(self):
        self.assertIn("survey_model", SIM_CONFIG)
        self.assertIsNone(SIM_CONFIG["survey_model"])

    def test_survey_provider_default_none(self):
        self.assertIn("survey_provider", SIM_CONFIG)
        self.assertIsNone(SIM_CONFIG["survey_provider"])

    def test_communication_mode_default_package(self):
        self.assertEqual(SIM_CONFIG["communication_mode"], "package")

    def test_package_policies_default_all_climate_policies(self):
        self.assertEqual(SIM_CONFIG["package_policies"], ALL_CLIMATE_POLICIES)


# ── Survey model override ───────────────────────────────────────

class TestSurveyModelOverride(unittest.TestCase):
    """Verify that survey_model/survey_provider are used for survey calls only."""

    @patch("cag.abm.sim.load_api_key", return_value="fake-key")
    @patch("cag.abm.sim.PoliticalAgent")
    def test_baseline_uses_survey_model(self, mock_pa_cls, mock_api):
        nation = _make_mock_nation(2)
        config = {
            "communication_mode": "single_policy",
            "day0_anchor": "llm_survey",
            "days": [{"policy": ClimatePolicyID.CARBON_TAX, "phases": []}],
            "survey_model": "gpt-4o",
            "survey_provider": "openai",
        }
        run_simulation(config, nation)
        for agent in nation.agents_active.values():
            call_kw = agent.administer_survey.call_args_list[0][1]
            self.assertEqual(call_kw["model"], "gpt-4o")

    @patch("cag.abm.sim.load_api_key", return_value="fake-key")
    @patch("cag.abm.sim.PoliticalAgent")
    def test_eod_survey_uses_survey_model(self, mock_pa_cls, mock_api):
        nation = _make_mock_nation(2)
        config = {
            "communication_mode": "single_policy",
            "day0_anchor": "llm_survey",
            "days": [{"policy": ClimatePolicyID.CARBON_TAX, "phases": ["P-A"]}],
            "survey_model": "gpt-4o",
            "survey_provider": "openai",
        }
        run_simulation(config, nation)
        eod_kw = nation.run_end_of_day_survey.call_args[1]
        self.assertEqual(eod_kw["model"], "gpt-4o")

    @patch("cag.abm.sim.load_api_key", return_value="fake-key")
    @patch("cag.abm.sim.PoliticalAgent")
    def test_fallback_to_main_model_when_none(self, mock_pa_cls, mock_api):
        nation = _make_mock_nation(2)
        config = {
            "communication_mode": "single_policy",
            "day0_anchor": "llm_survey",
            "days": [{"policy": ClimatePolicyID.CARBON_TAX, "phases": []}],
            "survey_model": None,
        }
        run_simulation(config, nation)
        for agent in nation.agents_active.values():
            call_kw = agent.administer_survey.call_args_list[0][1]
            self.assertEqual(call_kw["model"], SIM_CONFIG["llm_model"])

    @patch("cag.abm.sim.load_api_key", return_value="fake-key")
    @patch("cag.abm.sim.PoliticalAgent")
    def test_broadcast_uses_main_model(self, mock_pa_cls, mock_api):
        nation = _make_mock_nation(2)
        config = {
            "communication_mode": "single_policy",
            "day0_anchor": "llm_survey",
            "days": [{"policy": ClimatePolicyID.CARBON_TAX, "phases": ["P-A"]}],
            "survey_model": "gpt-4o",
            "survey_provider": "openai",
        }
        run_simulation(config, nation)
        bc_kw = nation.run_political_broadcast.call_args[1]
        self.assertEqual(bc_kw["model"], SIM_CONFIG["llm_model"])

    @patch("cag.abm.sim.load_api_key", return_value="fake-key")
    @patch("cag.abm.sim.PoliticalAgent")
    def test_different_provider_loads_separate_key(self, mock_pa_cls, mock_api):
        nation = _make_mock_nation(2)
        config = {
            "communication_mode": "single_policy",
            "day0_anchor": "llm_survey",
            "days": [{"policy": ClimatePolicyID.CARBON_TAX, "phases": []}],
            "survey_model": "claude-sonnet-4-20250514",
            "survey_provider": "anthropic",
        }
        run_simulation(config, nation)
        # load_api_key called once per distinct provider: the main provider
        # (research-canon default: "local") and the survey provider ("anthropic").
        providers_called = [c[0][0] for c in mock_api.call_args_list]
        self.assertIn(SIM_CONFIG["llm_provider"], providers_called)
        self.assertIn("anthropic", providers_called)


# ── collect_ground_truth ────────────────────────────────────────

class TestCollectGroundTruth(unittest.TestCase):

    @staticmethod
    def _make_gt_agent(agent_id, gt_values):
        """Mock agent with get_real_survey_response returning gt_values dict."""
        agent = MagicMock()
        agent.id = agent_id
        agent.get_real_survey_response = lambda pid: gt_values[pid]
        return agent

    def test_returns_correct_columns(self):
        agent = self._make_gt_agent(1, {ClimatePolicyID.CARBON_TAX: 2})
        df = collect_ground_truth([agent], policy_ids=[ClimatePolicyID.CARBON_TAX])
        self.assertEqual(sorted(df.columns.tolist()),
                         sorted(["agent_id", "policy_id", "ground_truth"]))

    def test_correct_ground_truth_values(self):
        gt = {ClimatePolicyID.CARBON_TAX: -1, ClimatePolicyID.GREEN_HOUSING: 3}
        agent = self._make_gt_agent(42, gt)
        df = collect_ground_truth([agent], policy_ids=list(gt.keys()))
        row_ct = df[df["policy_id"] == str(ClimatePolicyID.CARBON_TAX)]
        row_gh = df[df["policy_id"] == str(ClimatePolicyID.GREEN_HOUSING)]
        self.assertEqual(row_ct.iloc[0]["ground_truth"], -1)
        self.assertEqual(row_gh.iloc[0]["ground_truth"], 3)

    def test_defaults_to_all_policies(self):
        from cag.abm.attributes.opinion import SURVEY_COLUMN_MAP
        all_gt = {pid: 0 for pid in SURVEY_COLUMN_MAP}
        agent = self._make_gt_agent(1, all_gt)
        df = collect_ground_truth([agent])
        self.assertEqual(len(df), len(SURVEY_COLUMN_MAP))

    def test_filters_to_specified_policies(self):
        from cag.abm.attributes.opinion import SURVEY_COLUMN_MAP
        all_gt = {pid: 0 for pid in SURVEY_COLUMN_MAP}
        agent = self._make_gt_agent(1, all_gt)
        subset = [ClimatePolicyID.CARBON_TAX]
        df = collect_ground_truth([agent], policy_ids=subset)
        self.assertEqual(len(df), 1)
        self.assertEqual(df.iloc[0]["policy_id"], str(ClimatePolicyID.CARBON_TAX))

    def test_empty_agents_returns_empty_dataframe(self):
        df = collect_ground_truth([])
        self.assertTrue(df.empty)

    def test_policy_id_uses_str(self):
        agent = self._make_gt_agent(1, {ClimatePolicyID.CARBON_TAX: 0})
        df = collect_ground_truth([agent], policy_ids=[ClimatePolicyID.CARBON_TAX])
        self.assertIsInstance(df.iloc[0]["policy_id"], str)

    def test_collect_package_ground_truth(self):
        agent = MagicMock()
        agent.id = 1
        agent.get_real_package_index.return_value = 0.5
        df = collect_package_ground_truth([agent])
        self.assertEqual(sorted(df.columns.tolist()), ["agent_id", "ground_truth", "index_name"])
        self.assertEqual(df.iloc[0]["index_name"], PRO_CLIMATE_INDEX_COLUMN)
        self.assertEqual(df.iloc[0]["ground_truth"], 0.5)


class TestDay0Anchor(unittest.TestCase):
    """Tests for the day0_anchor config switch (llm_survey | ground_truth |
    ground_truth_with_rationale)."""

    @patch("cag.abm.sim.load_api_key", return_value="fake-key")
    @patch("cag.abm.sim.PoliticalAgent")
    def test_default_is_ground_truth_with_rationale(self, mock_pa_cls, mock_api):
        # Research-canon default: seed Day-0 numeric opinion from YouGov
        # ground truth and have the LLM write only the rationale.
        nation = _make_mock_nation(2)
        config = {
            "communication_mode": "single_policy",
            "days": [{"policy": ClimatePolicyID.CARBON_TAX, "phases": []}],
        }
        run_simulation(config, nation)
        for agent in nation.agents_active.values():
            agent.administer_survey.assert_not_called()
            agent.seed_opinion_from_ground_truth.assert_not_called()
            agent.seed_opinion_with_rationale.assert_called_once()

    @patch("cag.abm.sim.load_api_key", return_value="fake-key")
    @patch("cag.abm.sim.PoliticalAgent")
    def test_ground_truth_seeds_no_llm_survey(self, mock_pa_cls, mock_api):
        nation = _make_mock_nation(2)
        config = {
            "communication_mode": "single_policy",
            "day0_anchor": "ground_truth",
            "days": [{"policy": ClimatePolicyID.CARBON_TAX, "phases": []}],
        }
        run_simulation(config, nation)
        for agent in nation.agents_active.values():
            agent.administer_survey.assert_not_called()
            agent.seed_opinion_from_ground_truth.assert_called_once_with(
                ClimatePolicyID.CARBON_TAX, day=0,
            )
            agent.seed_opinion_with_rationale.assert_not_called()

    @patch("cag.abm.sim.load_api_key", return_value="fake-key")
    @patch("cag.abm.sim.PoliticalAgent")
    def test_ground_truth_with_rationale_calls_seed_with_rationale(self, mock_pa_cls, mock_api):
        nation = _make_mock_nation(2)
        config = {
            "communication_mode": "single_policy",
            "day0_anchor": "ground_truth_with_rationale",
            "days": [{"policy": ClimatePolicyID.CARBON_TAX, "phases": []}],
        }
        run_simulation(config, nation)
        for agent in nation.agents_active.values():
            agent.administer_survey.assert_not_called()
            agent.seed_opinion_from_ground_truth.assert_not_called()
            agent.seed_opinion_with_rationale.assert_called_once()
            kwargs = agent.seed_opinion_with_rationale.call_args.kwargs
            self.assertIn("api_key", kwargs)
            self.assertIn("model", kwargs)
            self.assertIn("provider", kwargs)

    @patch("cag.abm.sim.load_api_key", return_value="fake-key")
    @patch("cag.abm.sim.PoliticalAgent")
    def test_ground_truth_writes_opinion_history(self, mock_pa_cls, mock_api):
        nation = _make_mock_nation(2)
        config = {
            "day0_anchor": "ground_truth",
            "days": [{"policy": ClimatePolicyID.CARBON_TAX, "phases": []}],
        }
        run_simulation(config, nation)
        for agent in nation.agents_active.values():
            history = agent.opinion_history[ClimatePolicyID.CARBON_TAX]
            # First entry is the GT seed (value 2 in fake), second is end-of-day=1
            self.assertEqual(history[0], (0, 2))

    @patch("cag.abm.sim.load_api_key", return_value="fake-key")
    @patch("cag.abm.sim.PoliticalAgent")
    def test_invalid_anchor_raises(self, mock_pa_cls, mock_api):
        nation = _make_mock_nation(1)
        config = {
            "day0_anchor": "nonsense_mode",
            "days": [{"policy": ClimatePolicyID.CARBON_TAX, "phases": []}],
        }
        with self.assertRaises(ValueError) as ctx:
            run_simulation(config, nation)
        self.assertIn("day0_anchor", str(ctx.exception))

    @patch("cag.abm.sim.load_api_key", return_value="fake-key")
    @patch("cag.abm.sim.PoliticalAgent")
    def test_debias_with_anchored_mode_logs_override(self, mock_pa_cls, mock_api):
        nation = _make_mock_nation(1)
        config = {
            "day0_anchor": "ground_truth",
            "debias": True,
            "days": [{"policy": ClimatePolicyID.CARBON_TAX, "phases": []}],
        }
        with self.assertLogs(level="INFO") as captured:
            run_simulation(config, nation)
        self.assertTrue(
            any("debias flag is ignored on Day 0" in msg for msg in captured.output),
            f"Expected debias-ignored INFO log, got: {captured.output}",
        )

    @patch("cag.abm.sim.load_api_key", return_value="fake-key")
    @patch("cag.abm.sim.PoliticalAgent")
    def test_package_mode_with_ground_truth_seeds_all_policies(self, mock_pa_cls, mock_api):
        nation = _make_mock_nation(2)
        config = {
            "communication_mode": "package",
            "package_policies": list(ALL_CLIMATE_POLICIES),
            "day0_anchor": "ground_truth",
            "days": [{"phases": []}],
        }
        run_simulation(config, nation)
        for agent in nation.agents_active.values():
            agent.administer_survey.assert_not_called()
            self.assertEqual(
                agent.seed_opinion_from_ground_truth.call_count,
                len(ALL_CLIMATE_POLICIES),
            )


# ── make_phases / per-day phase sugar ───────────────────────────


class TestMakePhases(unittest.TestCase):
    def test_default_matches_canonical_three_phase_day(self):
        self.assertEqual(make_phases(), ["P-A", "P-B", "C"])

    def test_repeat_a_only(self):
        self.assertEqual(
            make_phases(broadcasts_a=3),
            ["P-A", "P-A", "P-A", "P-B", "C"],
        )

    def test_repeat_b_only(self):
        self.assertEqual(
            make_phases(broadcasts_a=1, broadcasts_b=2),
            ["P-A", "P-B", "P-B", "C"],
        )

    def test_b_first_no_interleave(self):
        self.assertEqual(
            make_phases(broadcasts_a=2, broadcasts_b=1, a_first=False),
            ["P-B", "P-A", "P-A", "C"],
        )

    def test_interleave_balanced(self):
        self.assertEqual(
            make_phases(broadcasts_a=2, broadcasts_b=2, interleave=True),
            ["P-A", "P-B", "P-A", "P-B", "C"],
        )

    def test_interleave_unbalanced_a_leads(self):
        self.assertEqual(
            make_phases(broadcasts_a=3, broadcasts_b=1, interleave=True),
            ["P-A", "P-B", "P-A", "P-A", "C"],
        )

    def test_interleave_b_leads(self):
        self.assertEqual(
            make_phases(broadcasts_a=1, broadcasts_b=2, interleave=True,
                        a_first=False),
            ["P-B", "P-A", "P-B", "C"],
        )

    def test_no_peer(self):
        self.assertEqual(
            make_phases(broadcasts_a=1, broadcasts_b=0, peer=False),
            ["P-A"],
        )

    def test_zero_broadcasts_zero_peer(self):
        self.assertEqual(make_phases(0, 0, peer=False), [])

    def test_negative_broadcast_count_rejected(self):
        with self.assertRaises(ValueError):
            make_phases(broadcasts_a=-1)
        with self.assertRaises(ValueError):
            make_phases(broadcasts_b=-2)

    def test_non_int_broadcast_count_rejected(self):
        with self.assertRaises(ValueError):
            make_phases(broadcasts_a=1.5)
        # bools are sneaky ints; explicitly reject them.
        with self.assertRaises(ValueError):
            make_phases(broadcasts_a=True)

    def test_non_bool_flag_rejected(self):
        with self.assertRaises(ValueError):
            make_phases(peer="yes")
        with self.assertRaises(ValueError):
            make_phases(interleave=1)


class TestResolveDayPhases(unittest.TestCase):
    def test_explicit_phases_passthrough(self):
        cfg = {"policy": ClimatePolicyID.CARBON_TAX,
               "phases": ["P-A", "P-A", "P-B", "C"]}
        self.assertEqual(
            _resolve_day_phases(cfg),
            ["P-A", "P-A", "P-B", "C"],
        )

    def test_explicit_phases_returns_copy(self):
        original = ["P-A", "P-B", "C"]
        cfg = {"policy": ClimatePolicyID.CARBON_TAX, "phases": original}
        out = _resolve_day_phases(cfg)
        out.append("XXX")
        self.assertEqual(original, ["P-A", "P-B", "C"])

    def test_sugar_keys_expand(self):
        cfg = {
            "policy": ClimatePolicyID.CARBON_TAX,
            "broadcasts_a": 2,
            "broadcasts_b": 1,
        }
        self.assertEqual(
            _resolve_day_phases(cfg),
            ["P-A", "P-A", "P-B", "C"],
        )

    def test_sugar_no_peer(self):
        cfg = {"policy": ClimatePolicyID.CARBON_TAX,
               "broadcasts_a": 1, "broadcasts_b": 0, "peer": False}
        self.assertEqual(_resolve_day_phases(cfg), ["P-A"])

    def test_no_phases_no_sugar_uses_defaults(self):
        cfg = {"policy": ClimatePolicyID.CARBON_TAX}
        self.assertEqual(_resolve_day_phases(cfg), ["P-A", "P-B", "C"])

    def test_mixing_phases_and_sugar_raises(self):
        cfg = {
            "policy": ClimatePolicyID.CARBON_TAX,
            "phases": ["P-A", "C"],
            "broadcasts_a": 2,
        }
        with self.assertRaises(ValueError):
            _resolve_day_phases(cfg)


class TestPerDayPhaseSugarInRunSimulation(unittest.TestCase):
    """End-to-end: sugar in days expands into the right broadcast calls."""

    @patch("cag.abm.sim.load_api_key", return_value="fake-key")
    @patch("cag.abm.sim.PoliticalAgent")
    def test_sugar_drives_repeated_broadcasts(self, mock_pa_cls, mock_api):
        nation = _make_mock_nation(2)
        config = {
            "communication_mode": "single_policy",
            "day0_anchor": "llm_survey",
            "days": [{
                "policy": ClimatePolicyID.CARBON_TAX,
                "broadcasts_a": 3,
                "broadcasts_b": 1,
                "peer": False,
            }],
        }
        run_simulation(config, nation)
        broadcast_phases = [
            c[0][0] for c in nation.run_political_broadcast.call_args_list
        ]
        self.assertEqual(broadcast_phases, ["P-A", "P-A", "P-A", "P-B"])
        nation.run_peer_messaging.assert_not_called()

    @patch("cag.abm.sim.load_api_key", return_value="fake-key")
    @patch("cag.abm.sim.PoliticalAgent")
    def test_explicit_phases_duplicates_not_deduped(
        self, mock_pa_cls, mock_api
    ):
        """Locks in the canonical 'phases is a literal sequence' behaviour."""
        nation = _make_mock_nation(2)
        config = {
            "communication_mode": "single_policy",
            "day0_anchor": "llm_survey",
            "days": [{
                "policy": ClimatePolicyID.CARBON_TAX,
                "phases": ["P-A", "P-A", "P-B", "C"],
            }],
        }
        run_simulation(config, nation)
        self.assertEqual(nation.run_political_broadcast.call_count, 3)
        self.assertEqual(nation.run_peer_messaging.call_count, 1)

    @patch("cag.abm.sim.load_api_key", return_value="fake-key")
    @patch("cag.abm.sim.PoliticalAgent")
    def test_mixing_phases_and_sugar_raises(self, mock_pa_cls, mock_api):
        nation = _make_mock_nation(2)
        config = {
            "days": [{
                "policy": ClimatePolicyID.CARBON_TAX,
                "phases": ["P-A", "C"],
                "broadcasts_a": 2,
            }],
        }
        with self.assertRaises(ValueError):
            run_simulation(config, nation)


class TestPoliticalMessageSourceWiring(unittest.TestCase):
    """Wiring of the offline political-message pool into the runtime."""

    def test_sim_config_defaults_offline(self):
        self.assertEqual(SIM_CONFIG["political_message_source"], "offline")
        self.assertEqual(SIM_CONFIG["political_message_set"], "v1")

    def test_resume_hard_keys_include_message_source(self):
        from cag.abm.sim import _RESUME_HARD_KEYS
        self.assertIn("political_message_source", _RESUME_HARD_KEYS)
        self.assertIn("political_message_set", _RESUME_HARD_KEYS)

    def test_resolve_runtime_offline_loads_pool(self):
        from cag.abm.sim import _resolve_runtime
        cfg = dict(SIM_CONFIG)
        cfg["llm_provider"] = "openai"
        cfg["days"] = [
            {"policy": ClimatePolicyID.RENEWABLE_ENERGY, "phases": ["P-A"]},
            {"policy": ClimatePolicyID.CARBON_TAX, "phases": ["P-A"]},
        ]
        with patch("cag.abm.sim.load_api_key", return_value="k"):
            rt = _resolve_runtime(cfg)
        self.assertIsNotNone(rt["message_pool"])
        # Should be usable for the policies in the days list.
        mid, txt = rt["message_pool"].next("A", ClimatePolicyID.RENEWABLE_ENERGY)
        self.assertTrue(mid.startswith("A_"))
        self.assertTrue(txt)

    def test_resolve_runtime_llm_source_returns_none_pool(self):
        from cag.abm.sim import _resolve_runtime
        cfg = dict(SIM_CONFIG)
        cfg["llm_provider"] = "openai"
        cfg["political_message_source"] = "llm"
        cfg["days"] = [{"policy": ClimatePolicyID.CARBON_TAX, "phases": ["P-A"]}]
        with patch("cag.abm.sim.load_api_key", return_value="k"):
            rt = _resolve_runtime(cfg)
        self.assertIsNone(rt["message_pool"])

    def test_resolve_runtime_invalid_source_raises(self):
        from cag.abm.sim import _resolve_runtime
        cfg = dict(SIM_CONFIG)
        cfg["llm_provider"] = "openai"
        cfg["political_message_source"] = "bogus"
        cfg["days"] = [{"policy": ClimatePolicyID.CARBON_TAX, "phases": ["P-A"]}]
        with patch("cag.abm.sim.load_api_key", return_value="k"):
            with self.assertRaises(ValueError):
                _resolve_runtime(cfg)

    def test_resolve_runtime_missing_set_raises(self):
        from cag.abm.sim import _resolve_runtime
        from cag.abm.political_messages import MessagePoolError
        cfg = dict(SIM_CONFIG)
        cfg["llm_provider"] = "openai"
        cfg["political_message_set"] = "does_not_exist"
        cfg["days"] = [{"policy": ClimatePolicyID.CARBON_TAX, "phases": ["P-A"]}]
        with patch("cag.abm.sim.load_api_key", return_value="k"):
            with self.assertRaises(MessagePoolError):
                _resolve_runtime(cfg)

    def test_resolve_runtime_package_mode_requires_package_cells(self):
        from cag.abm.sim import _resolve_runtime
        cfg = dict(SIM_CONFIG)
        cfg["llm_provider"] = "openai"
        cfg["communication_mode"] = "package"
        cfg["days"] = [{"phases": ["P-A"]}]
        with patch("cag.abm.sim.load_api_key", return_value="k"):
            rt = _resolve_runtime(cfg)
        # v1 ships with PACKAGE cells for both sides → should load fine
        mid, txt = rt["message_pool"].next("A", "PACKAGE")
        self.assertTrue(mid.startswith("A_PKG"))
        self.assertTrue(txt)


class TestBroadcastUsesOfflinePool(unittest.TestCase):
    """run_political_broadcast / run_package_broadcast pool integration."""

    def test_political_broadcast_uses_pool(self):
        # Real environment method called against a tiny fake setup.
        from cag.abm.environment import SurveyedNation
        from cag.abm.political_messages import load_message_pool

        nation = SurveyedNation.__new__(SurveyedNation)
        nation.message_log = []

        pol_agent = MagicMock()
        pol_agent.id = "pa_A"
        pol_agent.side = "A"
        pol_agent.generate_message = MagicMock(
            side_effect=AssertionError("LLM must not be called in offline mode")
        )
        recipient = MagicMock()
        recipient.id = "c1"
        recipient.receive_political_message = MagicMock(return_value="reflection")
        pol_agent.connected_citizens = [recipient]

        nation.political_agent_a = pol_agent
        nation.political_agent_b = MagicMock()

        pool = load_message_pool("v1", seed=0)
        result = nation.run_political_broadcast(
            "P-A", ClimatePolicyID.CARBON_TAX, day=1, message_pool=pool,
        )

        # Message text came from the pool, not the LLM.
        self.assertTrue(result["message"])
        pol_agent.generate_message.assert_not_called()
        # Logged event carries political_message_id.
        self.assertEqual(len(nation.message_log), 1)
        ev = nation.message_log[0]
        self.assertTrue(ev["political_message_id"].startswith("A_"))
        self.assertEqual(ev["message_text"], result["message"])

    def test_political_broadcast_llm_path_logs_empty_id(self):
        from cag.abm.environment import SurveyedNation

        nation = SurveyedNation.__new__(SurveyedNation)
        nation.message_log = []

        pol_agent = MagicMock()
        pol_agent.id = "pa_A"
        pol_agent.side = "A"
        pol_agent.generate_message = MagicMock(return_value="live llm text")
        recipient = MagicMock()
        recipient.id = "c1"
        recipient.receive_political_message = MagicMock(return_value="reflection")
        pol_agent.connected_citizens = [recipient]

        nation.political_agent_a = pol_agent
        nation.political_agent_b = MagicMock()

        nation.run_political_broadcast(
            "P-A", ClimatePolicyID.CARBON_TAX, day=1, message_pool=None,
        )
        ev = nation.message_log[0]
        self.assertEqual(ev["political_message_id"], "")
        self.assertEqual(ev["message_text"], "live llm text")

    def test_package_broadcast_uses_pool(self):
        from cag.abm.environment import SurveyedNation
        from cag.abm.political_messages import load_message_pool

        nation = SurveyedNation.__new__(SurveyedNation)
        nation.message_log = []

        pol_agent = MagicMock()
        pol_agent.id = "pa_B"
        pol_agent.side = "B"
        pol_agent.generate_package_message = MagicMock(
            side_effect=AssertionError("LLM must not be called in offline mode")
        )
        recipient = MagicMock()
        recipient.id = "c1"
        recipient.receive_package_political_message = MagicMock(return_value="r")
        pol_agent.connected_citizens = [recipient]

        nation.political_agent_a = MagicMock()
        nation.political_agent_b = pol_agent

        pool = load_message_pool("v1", seed=0)
        result = nation.run_package_broadcast(
            "P-B", list(ALL_CLIMATE_POLICIES), day=1, message_pool=pool,
        )
        self.assertTrue(result["message"])
        pol_agent.generate_package_message.assert_not_called()
        ev = nation.message_log[0]
        self.assertTrue(ev["political_message_id"].startswith("B_PKG"))


class TestCollectResultsIncludesMessageId(unittest.TestCase):

    def test_political_message_id_in_messages_frame(self):
        nation = _make_mock_nation(1)
        agent = list(nation.agents_active.values())[0]
        policy = ClimatePolicyID.CARBON_TAX
        agent.opinion_history = {policy: [(0, 1)]}
        agent.reflections = []
        agent.survey_reasoning = {}
        agent.survey_raw_response = {}
        agent.daily_summaries = {}
        nation.message_log = [{
            "day": 1,
            "phase": "P-A",
            "message_type": "political_broadcast",
            "sender_type": "political_agent",
            "sender_id": "pa_A",
            "sender_side": "A",
            "recipient_id": agent.id,
            "recipient_scope": "broadcast",
            "policy_id": policy,
            "package_scope": "",
            "policy_ids": [],
            "message_text": "msg",
            "political_message_id": "A_02_01",
        }]
        results = _collect_results(nation, {})
        df = results["messages"]
        self.assertIn("political_message_id", df.columns)
        self.assertEqual(df.iloc[0]["political_message_id"], "A_02_01")


if __name__ == "__main__":
    unittest.main()
