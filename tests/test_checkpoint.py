"""
Tests for cag.abm.sim checkpoint + resume functionality.

Reuses the mock-nation fixtures from tests/test_sim.py.
Run with: python -m pytest tests/test_checkpoint.py -v
"""
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../src")))
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from cag.abm.attributes.opinion import ClimatePolicyID
from cag.abm.sim import (
    CHECKPOINT_SCHEMA_VERSION,
    _load_checkpoint,
    _load_checkpoint_meta,
    _validate_resume_config,
    _write_checkpoint,
    run_simulation,
)

from test_sim import _make_mock_nation


def _base_config(tmp_dir):
    return {
        "n_citizens": 3,
        "days": [
            {"policy": ClimatePolicyID.CARBON_TAX, "phases": ["P-A", "P-B", "C"]},
            {"policy": ClimatePolicyID.CARBON_TAX, "phases": ["P-A", "P-B", "C"]},
            {"policy": ClimatePolicyID.CARBON_TAX, "phases": ["P-A", "P-B", "C"]},
        ],
        "k_peers_per_day": 1,
        "p_intra": 0.15,
        "p_inter": 0.02,
        "random_seed": 42,
        "communication_mode": "single_policy",
        "llm_model": "mock-model",
        "llm_provider": "openai",
        "output_dir": tmp_dir,
    }


@patch("cag.abm.sim.load_api_key", return_value="mock-key")
@patch("cag.abm.sim.PoliticalAgent")
class TestCheckpointRoundtrip(unittest.TestCase):

    def test_checkpoint_write_and_load_roundtrip(self, _pa, _key):
        with tempfile.TemporaryDirectory() as tmp:
            ckpt = Path(tmp) / "checkpoint"
            cfg = _base_config(tmp)
            cfg["days"] = cfg["days"][:2]

            nation = _make_mock_nation(n_agents=3)
            run_simulation(cfg, nation, checkpoint_dir=ckpt,
                           checkpoint_every_day=True)

            self.assertTrue((ckpt / "checkpoint_meta.json").exists())
            self.assertTrue((ckpt / "opinion_trajectories.csv").exists())
            self.assertTrue((ckpt / "reflections.csv").exists())
            self.assertTrue((ckpt / "messages.csv").exists())

            meta = _load_checkpoint_meta(ckpt)
            self.assertEqual(meta["last_completed_day"], 2)
            self.assertEqual(meta["schema_version"], CHECKPOINT_SCHEMA_VERSION)
            self.assertEqual(set(meta["agent_ids"]),
                             {str(aid) for aid in nation.agents_active.keys()})

            # Load into a fresh mock nation and assert state is restored.
            fresh = _make_mock_nation(n_agents=3)
            last_day = _load_checkpoint(fresh, ckpt)
            self.assertEqual(last_day, 2)

            # Compare the four agent state fields.
            for aid, original in nation.agents_active.items():
                restored = fresh.agents_active[aid]
                self.assertEqual(
                    restored.opinion_history, original.opinion_history,
                    f"opinion_history mismatch for agent {aid}",
                )
                # Reflections list compared by length + (day, phase, text).
                self.assertEqual(
                    len(restored.reflections), len(original.reflections),
                    f"reflections length mismatch for agent {aid}",
                )
                for r_orig, r_new in zip(original.reflections, restored.reflections):
                    self.assertEqual(r_orig["day"], r_new["day"])
                    self.assertEqual(r_orig["phase"], r_new["phase"])
                    self.assertEqual(r_orig["text"], r_new["text"])
                self.assertEqual(
                    restored.daily_summaries, original.daily_summaries,
                    f"daily_summaries mismatch for agent {aid}",
                )
                self.assertEqual(
                    restored.survey_reasoning, original.survey_reasoning,
                    f"survey_reasoning mismatch for agent {aid}",
                )

            # nation.message_log restored.
            self.assertEqual(len(fresh.message_log), len(nation.message_log))


@patch("cag.abm.sim.load_api_key", return_value="mock-key")
@patch("cag.abm.sim.PoliticalAgent")
class TestResume(unittest.TestCase):

    def test_resume_continues_day_numbering(self, _pa, _key):
        with tempfile.TemporaryDirectory() as tmp:
            ckpt = Path(tmp) / "checkpoint"
            cfg = _base_config(tmp)
            cfg["days"] = cfg["days"][:2]

            # Phase 1: run 2 days with checkpointing.
            nation1 = _make_mock_nation(n_agents=3)
            run_simulation(cfg, nation1, checkpoint_dir=ckpt,
                           checkpoint_every_day=True)

            # Phase 2: extend to 3 days, resume from checkpoint.
            cfg2 = _base_config(tmp)  # full 3-day config
            nation2 = _make_mock_nation(n_agents=3)
            results = run_simulation(cfg2, nation2, checkpoint_dir=ckpt,
                                     resume=True, checkpoint_every_day=True)

            traj = results["opinion_trajectories"]
            days_seen = sorted(traj["day"].unique().tolist())
            # Day 0 + 1 + 2 (restored) and 3 (newly run).
            self.assertEqual(days_seen, [0, 1, 2, 3])

    def test_resume_skips_day0(self, _pa, _key):
        with tempfile.TemporaryDirectory() as tmp:
            ckpt = Path(tmp) / "checkpoint"
            cfg = _base_config(tmp)
            cfg["days"] = cfg["days"][:1]

            nation1 = _make_mock_nation(n_agents=3)
            run_simulation(cfg, nation1, checkpoint_dir=ckpt,
                           checkpoint_every_day=True)

            # Resume — track Day 0 LLM calls.
            nation2 = _make_mock_nation(n_agents=3)
            run_simulation(_base_config(tmp), nation2,
                           checkpoint_dir=ckpt, resume=True)

            for agent in nation2.agents_active.values():
                # administer_survey may be called for day>=1 (EOD survey),
                # but never for day=0 on resume.
                day0_calls = [
                    c for c in agent.administer_survey.call_args_list
                    if c.kwargs.get("day", 0) == 0
                ]
                self.assertEqual(
                    day0_calls, [],
                    f"Day 0 survey called on resume for agent {agent.id}",
                )
                self.assertEqual(
                    agent.seed_opinion_from_ground_truth.call_count, 0,
                )

    def test_resume_rejects_incompatible_config(self, _pa, _key):
        with tempfile.TemporaryDirectory() as tmp:
            ckpt = Path(tmp) / "checkpoint"
            cfg = _base_config(tmp)
            cfg["days"] = cfg["days"][:1]

            nation1 = _make_mock_nation(n_agents=3)
            run_simulation(cfg, nation1, checkpoint_dir=ckpt,
                           checkpoint_every_day=True)

            # Change random_seed — must hard-fail.
            cfg_bad = _base_config(tmp)
            cfg_bad["random_seed"] = 999
            nation2 = _make_mock_nation(n_agents=3)
            with self.assertRaises(ValueError) as ctx:
                run_simulation(cfg_bad, nation2, checkpoint_dir=ckpt,
                               resume=True)
            self.assertIn("random_seed", str(ctx.exception))

    def test_resume_warns_on_model_change(self, _pa, _key):
        with tempfile.TemporaryDirectory() as tmp:
            ckpt = Path(tmp) / "checkpoint"
            cfg = _base_config(tmp)
            cfg["days"] = cfg["days"][:1]

            nation1 = _make_mock_nation(n_agents=3)
            run_simulation(cfg, nation1, checkpoint_dir=ckpt,
                           checkpoint_every_day=True)

            cfg2 = _base_config(tmp)
            cfg2["llm_model"] = "different-model"
            nation2 = _make_mock_nation(n_agents=3)
            with self.assertLogs("root", level="WARNING") as logs:
                run_simulation(cfg2, nation2, checkpoint_dir=ckpt,
                               resume=True)
            self.assertTrue(
                any("llm_model" in m for m in logs.output),
                f"Expected llm_model warning, got: {logs.output}",
            )

    def test_resume_with_no_checkpoint_fails(self, _pa, _key):
        with tempfile.TemporaryDirectory() as tmp:
            ckpt = Path(tmp) / "checkpoint_does_not_exist"
            nation = _make_mock_nation(n_agents=3)
            with self.assertRaises(FileNotFoundError):
                run_simulation(_base_config(tmp), nation,
                               checkpoint_dir=ckpt, resume=True)

    def test_resume_rejects_changed_agent_set(self, _pa, _key):
        with tempfile.TemporaryDirectory() as tmp:
            ckpt = Path(tmp) / "checkpoint"
            cfg = _base_config(tmp)
            cfg["days"] = cfg["days"][:1]

            nation1 = _make_mock_nation(n_agents=3)
            run_simulation(cfg, nation1, checkpoint_dir=ckpt,
                           checkpoint_every_day=True)

            # Different number of agents.
            nation2 = _make_mock_nation(n_agents=5)
            with self.assertRaises(ValueError) as ctx:
                run_simulation(_base_config(tmp), nation2,
                               checkpoint_dir=ckpt, resume=True)
            self.assertIn("agent set", str(ctx.exception))


class TestAtomicWrite(unittest.TestCase):

    @patch("cag.abm.sim.load_api_key", return_value="mock-key")
    @patch("cag.abm.sim.PoliticalAgent")
    def test_no_tmp_files_left_after_write(self, _pa, _key):
        with tempfile.TemporaryDirectory() as tmp:
            ckpt = Path(tmp) / "checkpoint"
            cfg = _base_config(tmp)
            cfg["days"] = cfg["days"][:1]

            nation = _make_mock_nation(n_agents=3)
            run_simulation(cfg, nation, checkpoint_dir=ckpt,
                           checkpoint_every_day=True)

            tmp_files = list(ckpt.glob("*.tmp"))
            self.assertEqual(tmp_files, [],
                             f"Found leftover .tmp files: {tmp_files}")


class TestRequiredArgs(unittest.TestCase):

    @patch("cag.abm.sim.load_api_key", return_value="mock-key")
    @patch("cag.abm.sim.PoliticalAgent")
    def test_resume_without_checkpoint_dir_raises(self, _pa, _key):
        nation = _make_mock_nation(n_agents=3)
        with self.assertRaises(ValueError) as ctx:
            run_simulation({"days": []}, nation, resume=True)
        self.assertIn("checkpoint_dir", str(ctx.exception))

    @patch("cag.abm.sim.load_api_key", return_value="mock-key")
    @patch("cag.abm.sim.PoliticalAgent")
    def test_checkpoint_every_day_without_dir_raises(self, _pa, _key):
        nation = _make_mock_nation(n_agents=3)
        with self.assertRaises(ValueError) as ctx:
            run_simulation({"days": []}, nation, checkpoint_every_day=True)
        self.assertIn("checkpoint_dir", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
