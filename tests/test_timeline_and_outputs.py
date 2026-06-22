"""
Tests for the v0.6 output additions:

* ``nation._sim_step`` monotonic counter (environment.py)
* ``collect_agent_attributes`` / ``_safe_network_snapshot`` (sim.py)
* Timeline sampling + ``build_agent_timeline`` (sim.py)
* Bucket-stratified builders (package_index_by_bucket, opinion_shares_by_bucket,
  day0_vs_dayN_shifts, calibration, message_flow)
* ``_write_all_csvs(is_checkpoint=...)`` skip-key semantics
* ``save_results`` emits ``network_snapshot.json``

Run with: pytest -q tests/test_timeline_and_outputs.py
"""
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock

import pandas as pd

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../src")))

from cag.abm.attributes.opinion import ClimatePolicyID
from cag.abm.sim import (
    _CHECKPOINT_SKIP_KEYS,
    _RESULT_CSV_SCHEMAS,
    _resolve_timeline_sample_ids,
    _safe_network_snapshot,
    _safe_step,
    _write_all_csvs,
    build_agent_timeline,
    build_calibration_table,
    build_day0_vs_dayN_shifts,
    build_message_flow,
    build_opinion_shares_by_bucket,
    build_package_index_by_bucket,
    collect_agent_attributes,
    save_results,
)


# ── Helpers ─────────────────────────────────────────────────────

def _bucketed_agents(specs):
    """Build a dict[id -> mock agent] with given (id, bucket) pairs."""
    agents = {}
    for aid, bucket in specs:
        ag = MagicMock()
        ag.id = aid
        ag.political_exposure = bucket
        ag._affinity_score_a = 0.7 if bucket == "A-only" else 0.2
        ag._affinity_score_b = 0.2 if bucket == "A-only" else 0.7
        ag.year_of_birth = 1980
        ag.gender_id = None
        ag.region_id = None
        ag.education_id = None
        ag.ukge2019_vote_id = None
        ag.brexit_vote_id = None
        ag.get_persona = MagicMock(return_value=f"persona for {aid}")
        agents[aid] = ag
    return agents


def _make_nation(specs, with_network=False):
    nation = MagicMock()
    nation.agents_active = _bucketed_agents(specs)
    if with_network:
        import networkx as nx
        G = nx.Graph()
        ids = [s[0] for s in specs]
        G.add_nodes_from(ids)
        # Simple ring so every node has degree 2.
        for i, nid in enumerate(ids):
            G.add_edge(nid, ids[(i + 1) % len(ids)])
        nation.network = G
    else:
        nation.network = None
    return nation


# ── sim_step monotonic counter ──────────────────────────────────

class TestSimStepCounter(unittest.TestCase):
    """The nation-level counter must be monotone and auto-stamp events."""

    def test_next_sim_step_monotone_from_zero(self):
        from cag.abm.environment import SurveyedNation
        n = SurveyedNation.__new__(SurveyedNation)
        # Lazy init: callers via __new__ should still get 1, 2, 3, ...
        self.assertEqual(n._next_sim_step(), 1)
        self.assertEqual(n._next_sim_step(), 2)
        self.assertEqual(n._next_sim_step(), 3)

    def test_log_message_event_auto_stamps_sim_step(self):
        from cag.abm.environment import SurveyedNation
        n = SurveyedNation.__new__(SurveyedNation)
        n.message_log = []
        n._log_message_event(day=1, phase="P-A", message_text="x")
        n._log_message_event(day=1, phase="P-B", message_text="y")
        steps = [e["sim_step"] for e in n.message_log]
        self.assertEqual(steps, [1, 2])

    def test_log_message_event_preserves_explicit_sim_step(self):
        from cag.abm.environment import SurveyedNation
        n = SurveyedNation.__new__(SurveyedNation)
        n.message_log = []
        n._log_message_event(sim_step=42, day=1, phase="P-A", message_text="x")
        self.assertEqual(n.message_log[0]["sim_step"], 42)


# ── _safe_step defensive coercion ───────────────────────────────

class TestSafeStep(unittest.TestCase):
    def test_int_values_passthrough(self):
        self.assertEqual(_safe_step(0), 0)
        self.assertEqual(_safe_step(7), 7)

    def test_none_returns_zero(self):
        self.assertEqual(_safe_step(None), 0)

    def test_str_int_coerced(self):
        self.assertEqual(_safe_step("12"), 12)

    def test_garbage_returns_zero(self):
        self.assertEqual(_safe_step("not a number"), 0)
        # CSV roundtrip of a stray MagicMock lands as its repr; must not crash.
        self.assertEqual(_safe_step("<MagicMock name='mock' id='1234'>"), 0)


# ── agent_attributes ────────────────────────────────────────────

class TestAgentAttributes(unittest.TestCase):
    def test_one_row_per_active_agent_with_full_schema(self):
        nation = _make_nation([(1.0, "A-only"), (2.0, "B-only"), (3.0, "both")])
        df = collect_agent_attributes(nation)
        self.assertEqual(len(df), 3)
        self.assertEqual(
            list(df.columns), _RESULT_CSV_SCHEMAS["agent_attributes"],
        )
        self.assertIn("A-only", df["political_exposure"].tolist())
        # Persona text captured verbatim from get_persona().
        self.assertTrue(df["persona_text"].str.startswith("persona for").all())

    def test_handles_get_persona_exception_without_crashing(self):
        nation = _make_nation([(1.0, "A-only")])
        nation.agents_active[1.0].get_persona = MagicMock(
            side_effect=RuntimeError("boom"),
        )
        df = collect_agent_attributes(nation)
        self.assertEqual(df.loc[0, "persona_text"], "")


# ── _safe_network_snapshot ──────────────────────────────────────

class TestSafeNetworkSnapshot(unittest.TestCase):
    def test_none_when_no_network(self):
        nation = _make_nation([(1.0, "A-only")], with_network=False)
        self.assertIsNone(_safe_network_snapshot(nation))

    def test_serialises_nodes_and_edges(self):
        nation = _make_nation(
            [(1.0, "A-only"), (2.0, "B-only"), (3.0, "both")],
            with_network=True,
        )
        snap = _safe_network_snapshot(nation)
        self.assertEqual(len(snap["nodes"]), 3)
        self.assertEqual(len(snap["edges"]), 3)  # ring of 3
        # Bucket carried through.
        buckets = {n["id"]: n["bucket"] for n in snap["nodes"]}
        self.assertEqual(buckets["1.0"], "A-only")
        self.assertEqual(buckets["3.0"], "both")
        # Edges are JSON-safe strings.
        for u, v in snap["edges"]:
            self.assertIsInstance(u, str)
            self.assertIsInstance(v, str)


# ── timeline sample resolution ──────────────────────────────────

class TestResolveTimelineSampleIds(unittest.TestCase):
    def test_size_zero_returns_empty(self):
        attrs = pd.DataFrame({"agent_id": [1, 2], "political_exposure": ["A-only", "B-only"]})
        self.assertEqual(_resolve_timeline_sample_ids(attrs, sample_size=0), [])

    def test_explicit_ids_win(self):
        attrs = pd.DataFrame({"agent_id": [1, 2, 3], "political_exposure": ["A", "A", "A"]})
        out = _resolve_timeline_sample_ids(attrs, sample_size=3, explicit_ids=[42, 99])
        self.assertEqual(out, [42, 99])

    def test_stratified_picks_one_per_bucket(self):
        attrs = pd.DataFrame({
            "agent_id": [1, 2, 3, 4, 5, 6],
            "political_exposure": ["A-only", "A-only", "A-only",
                                   "B-only", "B-only", "both"],
        })
        out = _resolve_timeline_sample_ids(attrs, sample_size=3)
        self.assertEqual(len(out), 3)
        # One agent from each bucket; ties broken by sorted agent_id.
        self.assertIn(1, out)   # smallest in A-only
        self.assertIn(4, out)   # smallest in B-only
        self.assertIn(6, out)   # only one in both

    def test_falls_back_to_evenly_spaced_when_buckets_short(self):
        attrs = pd.DataFrame({
            "agent_id": [1, 2, 3, 4, 5],
            "political_exposure": ["A-only"] * 5,
        })
        out = _resolve_timeline_sample_ids(attrs, sample_size=3)
        self.assertEqual(len(out), 3)
        self.assertIn(1, out)  # first canonical pick


# ── agent_timeline construction ─────────────────────────────────

class TestBuildAgentTimeline(unittest.TestCase):
    def _fixture(self):
        agent_attrs = pd.DataFrame({
            "agent_id": [1.0, 2.0],
            "political_exposure": ["A-only", "B-only"],
            "affinity_score_a": [0.7, 0.2],
            "affinity_score_b": [0.2, 0.7],
            "year_of_birth": [1980, 1981],
            "gender_id": [None, None],
            "region_id": [None, None],
            "education_id": [None, None],
            "ukge2019_vote_id": [None, None],
            "brexit_vote_id": [None, None],
            "persona_text": ["pa", "pb"],
        })
        messages = pd.DataFrame([{
            "sim_step": 1, "day": 1, "phase": "P-A",
            "message_type": "political_broadcast", "sender_type": "political_agent",
            "sender_id": "P-A", "sender_side": "pro_climate",
            "recipient_id": 1.0, "recipient_scope": "broadcast",
            "policy_id": "carbon_tax", "package_scope": "",
            "policy_ids_json": "[]", "message_text": "vote for tax",
            "political_message_id": "A_001",
        }, {
            "sim_step": 5, "day": 1, "phase": "C",
            "message_type": "peer_message", "sender_type": "citizen",
            "sender_id": 1.0, "sender_side": "",
            "recipient_id": 2.0, "recipient_scope": "direct",
            "policy_id": "carbon_tax", "package_scope": "",
            "policy_ids_json": "[]", "message_text": "I agree",
            "political_message_id": "",
        }])
        reflections = pd.DataFrame([{
            "agent_id": 1.0, "sim_step": 2, "day": 1, "phase": "P-A",
            "policy_id": "carbon_tax", "package_scope": "",
            "policy_ids_json": "[]", "messages_received_json": "[\"vote for tax\"]",
            "messages_received_count": 1, "text": "reflecting",
        }])
        ctx = pd.DataFrame([{
            "agent_id": 1.0, "sim_step": 8, "day": 1,
            "policy_id": "carbon_tax",
            "assembled_context": "full prompt text",
        }])
        sraw = pd.DataFrame([{
            "agent_id": 1.0, "sim_step": 9, "day": 1,
            "policy_id": "carbon_tax", "raw_response": "Strongly agree",
        }])
        sreas = pd.DataFrame(columns=_RESULT_CSV_SCHEMAS["survey_reasoning"])
        summ = pd.DataFrame([{
            "agent_id": 1.0, "sim_step": 11, "day": 1,
            "policy_id": "carbon_tax", "summary": "today I heard...",
        }])
        traj = pd.DataFrame([{
            "agent_id": 1.0, "day": 1, "policy_id": "carbon_tax", "numeric": 2,
        }])
        return {
            "agent_attributes": agent_attrs,
            "messages": messages,
            "reflections": reflections,
            "survey_assembled_context": ctx,
            "survey_raw_response": sraw,
            "survey_reasoning": sreas,
            "daily_summaries": summ,
            "opinion_trajectories": traj,
        }

    def test_empty_sample_returns_empty_frame_with_schema(self):
        df = build_agent_timeline({}, [])
        self.assertEqual(list(df.columns), _RESULT_CSV_SCHEMAS["agent_timeline"])
        self.assertTrue(df.empty)

    def test_emits_all_event_types_for_sampled_agent(self):
        results = self._fixture()
        df = build_agent_timeline(results, [1.0])
        event_types = set(df["event_type"].tolist())
        self.assertIn("broadcast_received", event_types)
        self.assertIn("peer_message_sent", event_types)
        self.assertIn("broadcast_reflection", event_types)
        self.assertIn("survey_assembled_context", event_types)
        self.assertIn("survey_raw_response", event_types)
        self.assertIn("survey_numeric", event_types)
        self.assertIn("daily_summary", event_types)

    def test_sorted_by_agent_id_then_sim_step(self):
        results = self._fixture()
        df = build_agent_timeline(results, [1.0])
        # All rows are for agent 1.0; sim_step must be non-decreasing.
        steps = df["sim_step"].tolist()
        self.assertEqual(steps, sorted(steps))

    def test_political_exposure_joined_from_attributes(self):
        results = self._fixture()
        df = build_agent_timeline(results, [1.0])
        self.assertTrue((df["political_exposure"] == "A-only").all())

    def test_phase_order_does_not_break_sort(self):
        """Reordering the message_log shuffles input but sort is by sim_step."""
        results = self._fixture()
        # Reverse the message_log: same events, opposite order.
        results["messages"] = results["messages"].iloc[::-1].reset_index(drop=True)
        df = build_agent_timeline(results, [1.0])
        steps = df["sim_step"].tolist()
        self.assertEqual(steps, sorted(steps))


# ── bucket-stratified builders ──────────────────────────────────

class TestBucketBuilders(unittest.TestCase):
    def _results(self):
        attrs = pd.DataFrame({
            "agent_id": [1, 2, 3, 4],
            "political_exposure": ["A-only", "A-only", "B-only", "B-only"],
            "affinity_score_a": [0.7, 0.6, 0.2, 0.1],
            "affinity_score_b": [0.2, 0.3, 0.7, 0.8],
            "year_of_birth": [1980, 1981, 1982, 1983],
            "gender_id": [None] * 4,
            "region_id": [None] * 4,
            "education_id": [None] * 4,
            "ukge2019_vote_id": [None] * 4,
            "brexit_vote_id": [None] * 4,
            "persona_text": ["p"] * 4,
        })
        # Two policies, two days each; A-only agents support, B-only oppose.
        rows = []
        for aid in [1, 2]:
            for day in [0, 5]:
                rows.append({"agent_id": aid, "day": day,
                             "policy_id": "carbon_tax", "numeric": 2})
                rows.append({"agent_id": aid, "day": day,
                             "policy_id": "ev_subsidy", "numeric": 1})
        for aid in [3, 4]:
            for day in [0, 5]:
                rows.append({"agent_id": aid, "day": day,
                             "policy_id": "carbon_tax", "numeric": -2})
                rows.append({"agent_id": aid, "day": day,
                             "policy_id": "ev_subsidy", "numeric": -1})
        traj = pd.DataFrame(rows)
        pkg_rows = []
        for aid in [1, 2]:
            for day in [0, 5]:
                pkg_rows.append({"agent_id": aid, "day": day,
                                 "index_name": "pro_climate_index",
                                 "package_scope": "package", "package_index": 1.5})
        for aid in [3, 4]:
            for day in [0, 5]:
                pkg_rows.append({"agent_id": aid, "day": day,
                                 "index_name": "pro_climate_index",
                                 "package_scope": "package", "package_index": -1.5})
        pkg_traj = pd.DataFrame(pkg_rows)
        gt = pd.DataFrame([
            {"agent_id": aid, "policy_id": "carbon_tax",
             "ground_truth": 1 if aid <= 2 else -1}
            for aid in [1, 2, 3, 4]
        ] + [
            {"agent_id": aid, "policy_id": "ev_subsidy",
             "ground_truth": 1 if aid <= 2 else -1}
            for aid in [1, 2, 3, 4]
        ])
        return {
            "agent_attributes": attrs,
            "opinion_trajectories": traj,
            "package_index_trajectories": pkg_traj,
            "ground_truth": gt,
        }

    def test_package_index_by_bucket_aggregates_per_bucket(self):
        df = build_package_index_by_bucket(self._results())
        self.assertEqual(set(df["political_exposure"].unique()), {"A-only", "B-only"})
        a_rows = df[df["political_exposure"] == "A-only"]
        self.assertTrue((a_rows["mean"] == 1.5).all())
        self.assertTrue((a_rows["n_agents"] == 2).all())

    def test_opinion_shares_by_bucket_percentages_sum_to_100(self):
        df = build_opinion_shares_by_bucket(self._results())
        for _, row in df.iterrows():
            total = row["support_pct"] + row["neutral_pct"] + row["against_pct"]
            self.assertAlmostEqual(total, 100.0, places=2)
        # A-only agents always support carbon_tax => 100%.
        a_carbon = df[(df["political_exposure"] == "A-only") & (df["policy_id"] == "carbon_tax")]
        self.assertTrue((a_carbon["support_pct"] == 100.0).all())

    def test_day0_vs_dayN_shifts_zero_when_static(self):
        df = build_day0_vs_dayN_shifts(self._results())
        # The fixture's opinions are constant across days => signed_shift == 0.
        self.assertTrue((df["signed_shift"] == 0).all())
        # One row per (agent, policy).
        self.assertEqual(len(df), 4 * 2)

    def test_calibration_table_has_perfect_correlation(self):
        df = build_calibration_table(self._results())
        # LLM matches GT direction perfectly => Pearson r == 1.
        self.assertTrue((df["pearson_r"] > 0.99).all())


class TestMessageFlow(unittest.TestCase):
    def test_aggregates_per_phase_side_bucket(self):
        attrs = pd.DataFrame({
            "agent_id": ["1", "2"],
            "political_exposure": ["A-only", "B-only"],
            "affinity_score_a": [0.7, 0.2],
            "affinity_score_b": [0.2, 0.7],
            "year_of_birth": [1980, 1981],
            "gender_id": [None, None], "region_id": [None, None],
            "education_id": [None, None],
            "ukge2019_vote_id": [None, None], "brexit_vote_id": [None, None],
            "persona_text": ["a", "b"],
        })
        msgs = pd.DataFrame([{
            "sim_step": 1, "day": 1, "phase": "P-A",
            "message_type": "political_broadcast", "sender_type": "political_agent",
            "sender_id": "P-A", "sender_side": "pro_climate",
            "recipient_id": "1", "recipient_scope": "broadcast",
            "policy_id": "carbon_tax", "package_scope": "",
            "policy_ids_json": "[]", "message_text": "hi there",
            "political_message_id": "A_001",
        }, {
            "sim_step": 2, "day": 1, "phase": "P-A",
            "message_type": "political_broadcast", "sender_type": "political_agent",
            "sender_id": "P-A", "sender_side": "pro_climate",
            "recipient_id": "2", "recipient_scope": "broadcast",
            "policy_id": "carbon_tax", "package_scope": "",
            "policy_ids_json": "[]", "message_text": "another",
            "political_message_id": "A_001",
        }])
        df = build_message_flow({"messages": msgs, "agent_attributes": attrs})
        self.assertEqual(df["n_messages"].sum(), 2)
        # Both buckets present.
        self.assertEqual(set(df["recipient_bucket"]), {"A-only", "B-only"})


# ── checkpoint skip-keys + write semantics ──────────────────────

class TestCheckpointSkipKeys(unittest.TestCase):
    def test_agent_timeline_in_skip_set(self):
        self.assertIn("agent_timeline", _CHECKPOINT_SKIP_KEYS)

    def test_is_checkpoint_skips_timeline_csv(self):
        with tempfile.TemporaryDirectory() as tmp:
            results = {
                "opinion_trajectories": pd.DataFrame(
                    columns=_RESULT_CSV_SCHEMAS["opinion_trajectories"]),
                "agent_timeline": pd.DataFrame(
                    [{"agent_id": 1, "political_exposure": "A-only",
                      "sim_step": 1, "day": 1, "phase": "P-A",
                      "event_type": "broadcast_received",
                      "policy_id": "carbon_tax", "counterparty_id": "P-A",
                      "counterparty_role": "political_agent",
                      "content": "hi", "metadata_json": "{}"}],
                    columns=_RESULT_CSV_SCHEMAS["agent_timeline"]),
            }
            _write_all_csvs(tmp, results, is_checkpoint=True)
            self.assertFalse((Path(tmp) / "agent_timeline.csv").exists())

    def test_final_run_writes_timeline_csv(self):
        with tempfile.TemporaryDirectory() as tmp:
            results = {
                "opinion_trajectories": pd.DataFrame(
                    columns=_RESULT_CSV_SCHEMAS["opinion_trajectories"]),
                "agent_timeline": pd.DataFrame(
                    [{"agent_id": 1, "political_exposure": "A-only",
                      "sim_step": 1, "day": 1, "phase": "P-A",
                      "event_type": "broadcast_received",
                      "policy_id": "carbon_tax", "counterparty_id": "P-A",
                      "counterparty_role": "political_agent",
                      "content": "hi", "metadata_json": "{}"}],
                    columns=_RESULT_CSV_SCHEMAS["agent_timeline"]),
            }
            _write_all_csvs(tmp, results, is_checkpoint=False)
            self.assertTrue((Path(tmp) / "agent_timeline.csv").exists())


# ── save_results emits network_snapshot.json ────────────────────

class TestSaveResultsNetworkSnapshot(unittest.TestCase):
    def test_network_snapshot_written_when_present(self):
        with tempfile.TemporaryDirectory() as tmp:
            results = {
                "config": {"random_seed": 7},
                "opinion_trajectories": pd.DataFrame(
                    columns=_RESULT_CSV_SCHEMAS["opinion_trajectories"]),
                "network_snapshot": {
                    "nodes": [{"id": "1", "bucket": "A-only", "degree": 2}],
                    "edges": [["1", "2"]],
                },
            }
            out = save_results(results, output_dir=tmp)
            snap_path = Path(out) / "network_snapshot.json"
            self.assertTrue(snap_path.exists())
            with open(snap_path) as f:
                loaded = json.load(f)
            self.assertEqual(loaded["edges"], [["1", "2"]])

    def test_network_snapshot_skipped_when_none(self):
        with tempfile.TemporaryDirectory() as tmp:
            results = {
                "config": {},
                "opinion_trajectories": pd.DataFrame(
                    columns=_RESULT_CSV_SCHEMAS["opinion_trajectories"]),
                "network_snapshot": None,
            }
            out = save_results(results, output_dir=tmp)
            self.assertFalse((Path(out) / "network_snapshot.json").exists())


if __name__ == "__main__":
    unittest.main()
