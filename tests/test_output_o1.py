"""Tests for the O1 output/observability additions:
- full-prompt capture via SurveyedCitizen._chat (gated to sampled agents)
- reached-audience flags + build_bucket_summary / build_targeting_diagnostics.
"""

import os
import sys
import unittest
from unittest.mock import patch

import pandas as pd

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../src")))

from cag.abm.agent import SurveyedCitizen
from cag.abm.environment import SurveyedNation
from cag.io.aggregators import build_bucket_summary, build_targeting_diagnostics


class TestPromptCapture(unittest.TestCase):
    def _citizen(self):
        sn = SurveyedNation()
        return SurveyedCitizen(agent_id=1, environment=sn)

    def test_no_capture_by_default(self):
        sc = self._citizen()
        with patch("cag.abm.agent.send_chat", return_value="RESP") as m:
            out = sc._chat("sys", "usr", stage="reflection_broadcast",
                           day=1, phase="P-A", policy_id="p1")
        self.assertEqual(out, "RESP")
        m.assert_called_once()
        self.assertEqual(sc.prompt_log, [])

    def test_capture_logs_full_triple(self):
        sc = self._citizen()
        sc._capture_prompts = True
        with patch("cag.abm.agent.send_chat", side_effect=["R1", "R2"]):
            sc._chat("sysA", "usrA", stage="survey_answer",
                     day=0, phase="survey", policy_id="p1")
            sc._chat("sysB", "usrB", stage="peer_message",
                     day=2, phase="C", policy_id="p2")
        self.assertEqual(len(sc.prompt_log), 2)
        r0, r1 = sc.prompt_log
        self.assertEqual(r0["prompt_seq"], 0)
        self.assertEqual(r1["prompt_seq"], 1)
        self.assertEqual(r0["stage"], "survey_answer")
        self.assertEqual(r0["system_prompt"], "sysA")
        self.assertEqual(r0["user_prompt"], "usrA")
        self.assertEqual(r0["response"], "R1")
        self.assertEqual(r1["stage"], "peer_message")
        self.assertEqual(r1["policy_id"], "p2")


def _mini_results(mode_a="persuadable", reach_a=0.5):
    """4 agents: 0,1 both; 2 neither; 3 A-only. Day 0 = GT anchor, Day 1 +0.5."""
    gt = {0: 0.0, 1: 1.0, 2: -1.0, 3: 2.0}
    traj_rows = []
    for aid, g in gt.items():
        traj_rows.append({"agent_id": aid, "day": 0, "index_name": "ProClimatePolSupp",
                          "package_scope": "package", "package_index": g})
        traj_rows.append({"agent_id": aid, "day": 1, "index_name": "ProClimatePolSupp",
                          "package_scope": "package", "package_index": g + 0.5})
    traj = pd.DataFrame(traj_rows)
    pkg_gt = pd.DataFrame([
        {"agent_id": aid, "index_name": "ProClimatePolSupp", "ground_truth": g}
        for aid, g in gt.items()
    ])
    attrs = pd.DataFrame([
        {"agent_id": 0, "political_exposure": "both", "reached_by_a": True, "reached_by_b": True},
        {"agent_id": 1, "political_exposure": "both", "reached_by_a": True, "reached_by_b": True},
        {"agent_id": 2, "political_exposure": "neither", "reached_by_a": False, "reached_by_b": False},
        {"agent_id": 3, "political_exposure": "A-only", "reached_by_a": False, "reached_by_b": False},
    ])
    return {
        "package_index_trajectories": traj,
        "package_ground_truth": pkg_gt,
        "agent_attributes": attrs,
        "config": {"reach_targeting_a": mode_a, "reach_a": reach_a,
                   "reach_targeting_b": "random", "reach_b": 1.0,
                   "run_label": "unit"},
    }


class TestBucketSummary(unittest.TestCase):
    def test_shape_and_drift(self):
        df = build_bucket_summary(_mini_results())
        self.assertFalse(df.empty)
        self.assertIn("TOTAL", set(df["political_exposure"]))
        # Every agent moved +0.5 from its Day-0 GT anchor.
        for drift in df["drift"]:
            self.assertAlmostEqual(drift, 0.5, places=6)
        both = df[df["political_exposure"] == "both"].iloc[0]
        self.assertEqual(both["n_agents"], 2)
        self.assertEqual(both["reached_a"], 2)

    def test_empty_inputs(self):
        self.assertTrue(build_bucket_summary({}).empty)


class TestTargetingDiagnostics(unittest.TestCase):
    def test_reached_vs_dropped_absgt(self):
        df = build_targeting_diagnostics(_mini_results())
        a = df[df["side"] == "A"].iloc[0]
        # A audience = both {0,1} + A-only {3}; reached = {0,1}, dropped = {3}.
        self.assertEqual(a["n_audience"], 3)
        self.assertEqual(a["n_reached"], 2)
        self.assertEqual(a["n_dropped"], 1)
        self.assertEqual(a["targeting_mode"], "persuadable")
        # reached |GT| = mean(0,1)=0.5 < dropped |GT| = |2| = 2.0.
        self.assertAlmostEqual(a["reached_mean_absgt"], 0.5, places=6)
        self.assertAlmostEqual(a["dropped_mean_absgt"], 2.0, places=6)

    def test_empty_inputs(self):
        self.assertTrue(build_targeting_diagnostics({}).empty)


class TestO2Plots(unittest.TestCase):
    """The new O2 figures render (produce files) on a full results dict."""

    def _full_results(self):
        import numpy as np
        buckets = {0: "both", 1: "both", 2: "neither", 3: "A-only"}
        gt = {0: 0.0, 1: 1.0, 2: -1.0, 3: 2.0}
        days = [0, 1, 2]
        pkg_rows, op_rows = [], []
        for aid in buckets:
            for day in days:
                val = gt[aid] + 0.3 * day
                pkg_rows.append({"agent_id": aid, "day": day,
                                 "index_name": "ProClimatePolSupp",
                                 "package_scope": "package", "package_index": val})
                for pid in ("ClimatePolicyID(1)", "ClimatePolicyID(2)"):
                    op_rows.append({"agent_id": aid, "day": day,
                                    "policy_id": pid, "numeric": val})
        gt_rows = [{"agent_id": a, "index_name": "ProClimatePolSupp",
                    "ground_truth": g} for a, g in gt.items()]
        op_gt = [{"agent_id": a, "policy_id": pid, "ground_truth": g}
                 for a, g in gt.items()
                 for pid in ("ClimatePolicyID(1)", "ClimatePolicyID(2)")]
        attrs = pd.DataFrame([
            {"agent_id": a, "political_exposure": buckets[a],
             "reached_by_a": buckets[a] in ("both", "A-only"),
             "reached_by_b": buckets[a] == "both"}
            for a in buckets
        ])
        snap = {
            "nodes": [{"id": a, "bucket": buckets[a], "degree": 2} for a in buckets],
            "edges": [[0, 1], [1, 2], [2, 3], [3, 0]],
        }
        return {
            "package_index_trajectories": pd.DataFrame(pkg_rows),
            "opinion_trajectories": pd.DataFrame(op_rows),
            "package_ground_truth": pd.DataFrame(gt_rows),
            "ground_truth": pd.DataFrame(op_gt),
            "agent_attributes": attrs,
            "network_snapshot": snap,
            "config": {"day0_anchor": "ground_truth_with_rationale",
                       "reach_targeting_a": "persuadable", "reach_a": 0.5,
                       "reach_targeting_b": "random", "reach_b": 1.0},
        }

    def test_new_plots_render(self):
        import matplotlib
        matplotlib.use("Agg")
        import tempfile
        from pathlib import Path
        from cag.io.plots import save_result_plots

        results = self._full_results()
        with tempfile.TemporaryDirectory() as tmp:
            paths = save_result_plots(results, Path(tmp))
            for key in (
                "opinion_trajectories_by_bucket", "polarization", "drift_from_gt",
                "opinion_ridgeline", "network_before_after", "targeting_mechanism",
                "reach_qc", "calibration_before_after",
            ):
                self.assertIn(key, paths, f"missing plot: {key}")
                self.assertTrue(Path(paths[key]).exists())


if __name__ == "__main__":
    unittest.main()
