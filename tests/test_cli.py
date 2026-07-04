"""Tests for the cag.__main__ CLI surface (preset/dry-run/JSON parsing)."""
from __future__ import annotations

import io
import json
from contextlib import redirect_stdout
from unittest import TestCase

import cag.__main__ as cli
from cag.presets import RUN_BUNDLE_PRESETS


class TestArgsToSimDict(TestCase):
    """The dest → SIM_CONFIG translation must be lossless and filtering."""

    def test_translates_known_dests(self):
        args = cli.parse_args([
            "--outdir", "/tmp/x",
            "--n-citizens", "5",
            "--days", "2",
            "--seed", "7",
            "--k-peers", "1",
            "--model", "foo",
            "--provider", "openai",
            "--base-url", "http://localhost:9999/v1",
            "--temperature", "0.3",
            "--no-thinking",
        ])
        cfg = cli._args_to_sim_dict(args)
        self.assertEqual(cfg["n_citizens"], 5)
        self.assertEqual(cfg["days"], 2)            # int at this point
        self.assertEqual(cfg["random_seed"], 7)
        self.assertEqual(cfg["k_peers_per_day"], 1)
        self.assertEqual(cfg["llm_model"], "foo")
        self.assertEqual(cfg["llm_provider"], "openai")
        self.assertEqual(cfg["local_base_url"], "http://localhost:9999/v1")
        self.assertEqual(cfg["llm_temperature"], 0.3)
        self.assertFalse(cfg["thinking"])
        # Control-flow dests stripped.
        for forbidden in ("outdir", "data", "preset", "list_presets",
                          "dry_run", "checkpoint_every_day", "resume"):
            self.assertNotIn(forbidden, cfg)

    def test_unset_flags_absent(self):
        args = cli.parse_args(["--outdir", "/tmp/x", "--n-citizens", "5", "--days", "2"])
        cfg = cli._args_to_sim_dict(args)
        # User did not pass --seed; SUPPRESS means it should not appear.
        self.assertNotIn("random_seed", cfg)
        self.assertNotIn("llm_model", cfg)

    def test_checkpoint_default_on(self):
        """Per-day checkpointing must default to ON (resume-safe by default)."""
        args = cli.parse_args(["--outdir", "/tmp/x", "--n-citizens", "5", "--days", "2"])
        self.assertTrue(args.checkpoint_every_day)

    def test_checkpoint_opt_out(self):
        args = cli.parse_args(["--outdir", "/tmp/x", "--n-citizens", "5", "--days", "2",
                               "--no-checkpoint-every-day"])
        self.assertFalse(args.checkpoint_every_day)


class TestBuildConfig(TestCase):
    """Preset + CLI merge precedence and days normalisation."""

    def test_preset_alone(self):
        preset = dict(RUN_BUNDLE_PRESETS["smoke"]["config"])
        cfg = cli.build_config(preset, {})
        self.assertEqual(cfg["n_citizens"], 10)
        # Smoke preset deliberately does NOT pin the model/provider —
        # SIM_CONFIG (Mac) or run.sh (AIRE) supplies those.
        self.assertNotIn("llm_provider", cfg)
        self.assertNotIn("llm_model", cfg)
        # int → list expansion
        self.assertIsInstance(cfg["days"], list)
        self.assertEqual(len(cfg["days"]), 2)
        self.assertEqual(cfg["days"][0]["phases"], ["P-A", "P-B", "C"])

    def test_cli_overrides_preset(self):
        preset = dict(RUN_BUNDLE_PRESETS["smoke"]["config"])
        # CLI supplies model+provider and grows the run.
        cli_dict = {
            "llm_provider": "openai",
            "llm_model": "gpt-5.4-mini",
            "n_citizens": 30,
        }
        cfg = cli.build_config(preset, cli_dict)
        self.assertEqual(cfg["llm_provider"], "openai")
        self.assertEqual(cfg["llm_model"], "gpt-5.4-mini")
        self.assertEqual(cfg["n_citizens"], 30)
        # Preset values untouched where CLI silent:
        self.assertEqual(cfg["k_peers_per_day"], 0)
        self.assertFalse(cfg["thinking"])

    def test_days_list_passthrough(self):
        cfg = cli.build_config({}, {"days": [{"phases": ["P-A"]}]})
        self.assertEqual(cfg["days"], [{"phases": ["P-A"]}])

    def test_tier1_preset_resolves_asymmetry_design(self):
        preset = dict(RUN_BUNDLE_PRESETS["tier1"]["config"])
        cfg = cli.build_config(preset, {})
        # Cohort + schedule bumped for the honest multi-seed run.
        self.assertEqual(cfg["n_citizens"], 100)
        self.assertEqual(cfg["k_peers_per_day"], 2)
        self.assertEqual(cfg["communication_mode"], "package")
        self.assertEqual(cfg["day0_anchor"], "ground_truth_with_rationale")
        # Memory pinned to the v0.9 canon: default sections but anchor ttl=1.
        self.assertEqual(cfg["memory"], {"day0_anchor": {"ttl_days": 1}})
        # 5-day int schedule expands to the alternating P-A/P-B/C plan.
        self.assertIsInstance(cfg["days"], list)
        self.assertEqual(len(cfg["days"]), 5)
        self.assertEqual(cfg["days"][0]["phases"], ["P-A", "P-B", "C"])
        # Does NOT pin a model — AIRE run.sh / SIM_CONFIG supplies it.
        self.assertNotIn("llm_model", cfg)
        self.assertNotIn("llm_provider", cfg)

    def test_tier1_preset_condition_overrides(self):
        preset = dict(RUN_BUNDLE_PRESETS["tier1"]["config"])
        # reform-dominant reach + the no-broadcast placebo exposure.
        cfg = cli.build_config(
            preset,
            {"reach_a": 0.25, "reach_b": 1.0, "political_exposure_targets": "neither"},
        )
        self.assertEqual(cfg["reach_a"], 0.25)
        self.assertEqual(cfg["reach_b"], 1.0)
        self.assertEqual(cfg["political_exposure_targets"], "neither")
        # Preset design keys untouched by the condition flags.
        self.assertEqual(cfg["n_citizens"], 100)
        self.assertEqual(cfg["day0_anchor"], "ground_truth_with_rationale")


class TestArgparseTypeHelpers(TestCase):

    def test_maybe_json_string(self):
        self.assertEqual(cli._maybe_json("split50"), "split50")

    def test_maybe_json_dict(self):
        result = cli._maybe_json('{"A-only": 0.5, "B-only": 0.5, "both": 0, "neither": 0}')
        self.assertEqual(result, {"A-only": 0.5, "B-only": 0.5, "both": 0, "neither": 0})

    def test_maybe_json_bad_json_raises(self):
        import argparse
        with self.assertRaises(argparse.ArgumentTypeError):
            cli._maybe_json("{not valid}")

    def test_json_dict_rejects_non_object(self):
        import argparse
        with self.assertRaises(argparse.ArgumentTypeError):
            cli._json_dict("[1,2,3]")

    def test_int_or_none(self):
        self.assertIsNone(cli._int_or_none("none"))
        self.assertIsNone(cli._int_or_none("null"))
        self.assertIsNone(cli._int_or_none(""))
        self.assertIsNone(cli._int_or_none(None))
        self.assertEqual(cli._int_or_none("42"), 42)

    def test_package_policies_all(self):
        from cag.abm.attributes.opinion import ALL_CLIMATE_POLICIES
        self.assertEqual(cli._package_policies_arg("all"), list(ALL_CLIMATE_POLICIES))

    def test_package_policies_list(self):
        from cag.abm.attributes.opinion import ClimatePolicyID
        result = cli._package_policies_arg("1,3,5")
        self.assertEqual(result, [ClimatePolicyID(1), ClimatePolicyID(3), ClimatePolicyID(5)])

    def test_package_policies_invalid(self):
        import argparse
        with self.assertRaises(argparse.ArgumentTypeError):
            cli._package_policies_arg("not_an_int")


class TestCLIMainEntryPoints(TestCase):
    """End-to-end behaviour of --list-presets / --dry-run (no real run)."""

    def test_list_presets_runs_and_exits_cleanly(self):
        buf = io.StringIO()
        with redirect_stdout(buf):
            cli.main(["--outdir", "/tmp/whatever", "--list-presets"])
        out = buf.getvalue()
        for name in RUN_BUNDLE_PRESETS:
            self.assertIn(name, out)

    def test_dry_run_with_preset(self):
        buf = io.StringIO()
        with redirect_stdout(buf):
            cli.main(["--preset", "smoke", "--dry-run"])
        cfg = json.loads(buf.getvalue())
        self.assertEqual(cfg["n_citizens"], 10)
        # Smoke preset does NOT pin a model/provider — SIM_CONFIG defaults
        # (Mac) or run.sh's hardcoded --model (AIRE) supply them.
        self.assertNotIn("llm_provider", cfg)
        # days int got expanded to list
        self.assertIsInstance(cfg["days"], list)

    def test_dry_run_cli_overrides_preset(self):
        buf = io.StringIO()
        with redirect_stdout(buf):
            cli.main([
                "--preset", "r14_canonical",
                "--exposure-targets", "split50",
                "--k-peers", "2",
                "--dry-run",
            ])
        cfg = json.loads(buf.getvalue())
        self.assertEqual(cfg["political_exposure_targets"], "split50")
        self.assertEqual(cfg["k_peers_per_day"], 2)
        # Preset values that the CLI did NOT override survive.
        self.assertEqual(cfg["day0_anchor"], "ground_truth_with_rationale")
        self.assertEqual(cfg["n_citizens"], 50)

    def test_dry_run_json_exposure_targets(self):
        buf = io.StringIO()
        with redirect_stdout(buf):
            cli.main([
                "--n-citizens", "10",
                "--days", "2",
                "--exposure-targets",
                '{"A-only": 0.5, "B-only": 0.5, "both": 0, "neither": 0}',
                "--dry-run",
            ])
        cfg = json.loads(buf.getvalue())
        self.assertEqual(
            cfg["political_exposure_targets"],
            {"A-only": 0.5, "B-only": 0.5, "both": 0, "neither": 0},
        )

    def test_memory_flag_preset_name(self):
        args = cli.parse_args([
            "--outdir", "/tmp/x", "--n-citizens", "5", "--days", "2",
            "--memory", "short_memory",
        ])
        cfg = cli._args_to_sim_dict(args)
        self.assertEqual(cfg["memory"], "short_memory")

    def test_memory_flag_json_dict(self):
        buf = io.StringIO()
        with redirect_stdout(buf):
            cli.main([
                "--n-citizens", "10",
                "--days", "2",
                "--memory", '{"verbatim_window_days": 3}',
                "--dry-run",
            ])
        cfg = json.loads(buf.getvalue())
        self.assertEqual(cfg["memory"], {"verbatim_window_days": 3})

    def test_memory_flag_absent_when_unset(self):
        args = cli.parse_args(["--outdir", "/tmp/x", "--n-citizens", "5", "--days", "2"])
        cfg = cli._args_to_sim_dict(args)
        self.assertNotIn("memory", cfg)

    def test_missing_n_citizens_without_preset(self):
        with self.assertRaises(SystemExit) as cm:
            cli.main(["--outdir", "/tmp/x", "--days", "2"])
        # SystemExit message mentions the missing key.
        self.assertIn("n_citizens", str(cm.exception))

    def test_missing_days_without_preset(self):
        with self.assertRaises(SystemExit) as cm:
            cli.main(["--outdir", "/tmp/x", "--n-citizens", "5"])
        self.assertIn("days", str(cm.exception))

    def test_unknown_preset_rejected_by_argparse(self):
        # argparse exits with code 2 on choice violation.
        with self.assertRaises(SystemExit):
            cli.main(["--preset", "not_a_real_preset", "--dry-run"])


class TestBroadcastFrequency(TestCase):
    """Frequency-asymmetry CLI: --broadcasts-a/-b + --interleave threading."""

    def test_build_days_symmetric_default_unchanged(self):
        # Golden: 1v1 (the default) is byte-identical to the old canon,
        # regardless of interleave, with a_first alternating by day.
        plan = cli.build_days(2)
        self.assertEqual(plan[0]["phases"], ["P-A", "P-B", "C"])
        self.assertEqual(plan[1]["phases"], ["P-B", "P-A", "C"])

    def test_build_days_symmetric_interleave_flag_irrelevant(self):
        self.assertEqual(
            cli.build_days(1, broadcasts_a=1, broadcasts_b=1, interleave=True),
            cli.build_days(1, broadcasts_a=1, broadcasts_b=1, interleave=False),
        )

    def test_build_days_asymmetric_block(self):
        plan = cli.build_days(1, broadcasts_a=3, broadcasts_b=1, interleave=False)
        self.assertEqual(plan[0]["phases"], ["P-A", "P-A", "P-A", "P-B", "C"])

    def test_build_days_asymmetric_interleave(self):
        plan = cli.build_days(1, broadcasts_a=3, broadcasts_b=1, interleave=True)
        self.assertEqual(plan[0]["phases"], ["P-A", "P-B", "P-A", "P-A", "C"])

    def test_build_config_pops_frequency_knobs(self):
        cfg = cli.build_config({}, {
            "days": 1,
            "broadcasts_a": 3,
            "broadcasts_b": 1,
            "interleave": False,
        })
        # Knobs consumed, never leak into SIM_CONFIG space.
        self.assertNotIn("broadcasts_a", cfg)
        self.assertNotIn("broadcasts_b", cfg)
        self.assertNotIn("interleave", cfg)
        self.assertEqual(cfg["days"][0]["phases"], ["P-A", "P-A", "P-A", "P-B", "C"])

    def test_build_config_default_symmetric(self):
        cfg = cli.build_config({}, {"days": 2})
        self.assertEqual(cfg["days"][0]["phases"], ["P-A", "P-B", "C"])
        self.assertNotIn("broadcasts_a", cfg)

    def test_parse_broadcasts_flags(self):
        args = cli.parse_args([
            "--outdir", "/tmp/x", "--n-citizens", "5", "--days", "2",
            "--broadcasts-a", "3", "--broadcasts-b", "1", "--no-interleave",
        ])
        self.assertEqual(args.broadcasts_a, 3)
        self.assertEqual(args.broadcasts_b, 1)
        self.assertFalse(args.interleave)

    def test_broadcasts_flags_absent_when_unset(self):
        args = cli.parse_args([
            "--outdir", "/tmp/x", "--n-citizens", "5", "--days", "2",
        ])
        self.assertFalse(hasattr(args, "broadcasts_a"))
        self.assertFalse(hasattr(args, "interleave"))

    def test_dry_run_frequency_asymmetry(self):
        buf = io.StringIO()
        with redirect_stdout(buf):
            cli.main([
                "--n-citizens", "10", "--days", "2",
                "--broadcasts-a", "3", "--broadcasts-b", "1", "--no-interleave",
                "--dry-run",
            ])
        cfg = json.loads(buf.getvalue())
        self.assertEqual(cfg["days"][0]["phases"], ["P-A", "P-A", "P-A", "P-B", "C"])
        self.assertNotIn("broadcasts_a", cfg)
