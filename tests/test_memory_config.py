"""Tests for the agent memory / prompt-assembly configuration.

Covers:
- Default config shape reproduces the v0.5 hard-wired behaviour.
- Preset resolution (name -> full config) and the partial-override contract.
- Dict override deep-merge (nested sections + stages).
- Validation rejects unknown keys, bad types, and out-of-range values.
- Per-stage resolution (``resolve_stage_memory``).
- Verbatim-window helpers (the shared W coupling), incl. unbounded (None).
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from cag.abm.config.memory import (
    DEFAULT_MEMORY_CONFIG,
    MEMORY_PRESETS,
    MEMORY_SECTIONS,
    MEMORY_STAGES,
    resolve_memory_config,
    validate_memory_config,
    resolve_stage_memory,
    verbatim_days,
    summary_upper_exclusive,
    compression_target_day,
)


class TestDefaultConfig(unittest.TestCase):
    def test_default_is_valid(self):
        validate_memory_config(DEFAULT_MEMORY_CONFIG)

    def test_default_reproduces_v05_behaviour(self):
        # Six original sections on, opinion_trajectory off, W=2, anchor never
        # expires, no per-stage overrides.
        cfg = resolve_memory_config(None)
        self.assertTrue(cfg["persona"]["enabled"])
        self.assertTrue(cfg["day0_anchor"]["enabled"])
        self.assertIsNone(cfg["day0_anchor"]["ttl_days"])
        self.assertTrue(cfg["daily_summaries"]["enabled"])
        self.assertTrue(cfg["recent_reflections"]["enabled"])
        self.assertTrue(cfg["own_reasoning"]["enabled"])
        self.assertTrue(cfg["today_so_far"]["enabled"])
        self.assertFalse(cfg["opinion_trajectory"]["enabled"])
        self.assertEqual(cfg["verbatim_window_days"], 2)
        self.assertEqual(cfg["stages"], {s: {} for s in MEMORY_STAGES})

    def test_resolve_none_returns_fresh_copy(self):
        a = resolve_memory_config(None)
        a["persona"]["enabled"] = False
        b = resolve_memory_config(None)
        self.assertTrue(b["persona"]["enabled"])
        # And the module-level default is untouched.
        self.assertTrue(DEFAULT_MEMORY_CONFIG["persona"]["enabled"])


class TestPresets(unittest.TestCase):
    def test_all_presets_resolve_and_validate(self):
        for name in MEMORY_PRESETS:
            cfg = resolve_memory_config(name)
            validate_memory_config(cfg)

    def test_default_preset_matches_none(self):
        self.assertEqual(resolve_memory_config("default"), resolve_memory_config(None))

    def test_window_presets(self):
        self.assertEqual(resolve_memory_config("short_memory")["verbatim_window_days"], 1)
        self.assertEqual(resolve_memory_config("wide_memory")["verbatim_window_days"], 4)
        self.assertIsNone(resolve_memory_config("no_compression")["verbatim_window_days"])

    def test_no_anchor_preset(self):
        cfg = resolve_memory_config("no_anchor")
        self.assertFalse(cfg["day0_anchor"]["enabled"])
        # Other sections untouched.
        self.assertTrue(cfg["persona"]["enabled"])

    def test_anchor_ttl2_preset(self):
        cfg = resolve_memory_config("anchor_ttl2")
        self.assertTrue(cfg["day0_anchor"]["enabled"])
        self.assertEqual(cfg["day0_anchor"]["ttl_days"], 2)

    def test_persona_only_preset(self):
        cfg = resolve_memory_config("persona_only")
        self.assertTrue(cfg["persona"]["enabled"])
        for name in MEMORY_SECTIONS:
            if name != "persona":
                self.assertFalse(cfg[name]["enabled"], name)

    def test_unknown_preset_raises(self):
        with self.assertRaises(ValueError):
            resolve_memory_config("does_not_exist")


class TestDictOverride(unittest.TestCase):
    def test_deep_merge_preserves_siblings(self):
        cfg = resolve_memory_config({"day0_anchor": {"ttl_days": 3}})
        # Sibling param inside day0_anchor is preserved.
        self.assertTrue(cfg["day0_anchor"]["enabled"])
        self.assertEqual(cfg["day0_anchor"]["ttl_days"], 3)
        # Other sections preserved.
        self.assertTrue(cfg["own_reasoning"]["enabled"])

    def test_stage_override_merge(self):
        cfg = resolve_memory_config(
            {"stages": {"survey": {"own_reasoning": {"enabled": False}}}}
        )
        self.assertEqual(cfg["stages"]["survey"]["own_reasoning"]["enabled"], False)
        # Global still on.
        self.assertTrue(cfg["own_reasoning"]["enabled"])
        # Other stages untouched.
        self.assertEqual(cfg["stages"]["reflection"], {})

    def test_bad_spec_type_raises(self):
        with self.assertRaises(ValueError):
            resolve_memory_config(42)


class TestValidation(unittest.TestCase):
    def test_unknown_top_level_key(self):
        with self.assertRaises(ValueError):
            validate_memory_config({"persona": {"enabled": True}, "bogus": 1})

    def test_unknown_section_param(self):
        with self.assertRaises(ValueError):
            validate_memory_config({"persona": {"weight": 2}})

    def test_enabled_must_be_bool(self):
        with self.assertRaises(ValueError):
            validate_memory_config({"persona": {"enabled": 1}})

    def test_window_zero_rejected(self):
        with self.assertRaises(ValueError):
            validate_memory_config({"verbatim_window_days": 0})

    def test_window_bool_rejected(self):
        with self.assertRaises(ValueError):
            validate_memory_config({"verbatim_window_days": True})

    def test_window_none_ok(self):
        validate_memory_config({"verbatim_window_days": None})

    def test_ttl_negative_rejected(self):
        with self.assertRaises(ValueError):
            validate_memory_config({"day0_anchor": {"ttl_days": -1}})

    def test_ttl_zero_ok(self):
        validate_memory_config({"day0_anchor": {"ttl_days": 0}})

    def test_ttl_on_non_anchor_section_rejected(self):
        with self.assertRaises(ValueError):
            validate_memory_config({"persona": {"ttl_days": 2}})

    def test_unknown_stage_rejected(self):
        with self.assertRaises(ValueError):
            validate_memory_config({"stages": {"bogus": {}}})

    def test_unknown_section_in_stage_rejected(self):
        with self.assertRaises(ValueError):
            validate_memory_config({"stages": {"survey": {"bogus": {}}}})


class TestResolveStageMemory(unittest.TestCase):
    def test_no_override_returns_globals_without_stages_key(self):
        cfg = resolve_memory_config(None)
        eff = resolve_stage_memory(cfg, "survey")
        self.assertNotIn("stages", eff)
        self.assertTrue(eff["persona"]["enabled"])
        self.assertEqual(eff["verbatim_window_days"], 2)

    def test_stage_override_applied(self):
        cfg = resolve_memory_config(
            {"stages": {"survey": {"own_reasoning": {"enabled": False}}}}
        )
        eff = resolve_stage_memory(cfg, "survey")
        self.assertFalse(eff["own_reasoning"]["enabled"])
        # A different stage keeps the global value.
        eff_reflect = resolve_stage_memory(cfg, "reflection")
        self.assertTrue(eff_reflect["own_reasoning"]["enabled"])

    def test_none_stage_returns_globals(self):
        cfg = resolve_memory_config(None)
        eff = resolve_stage_memory(cfg, None)
        self.assertTrue(eff["persona"]["enabled"])

    def test_unknown_stage_raises(self):
        cfg = resolve_memory_config(None)
        with self.assertRaises(ValueError):
            resolve_stage_memory(cfg, "bogus")

    def test_does_not_mutate_source(self):
        cfg = resolve_memory_config(
            {"stages": {"survey": {"persona": {"enabled": False}}}}
        )
        eff = resolve_stage_memory(cfg, "survey")
        eff["persona"]["enabled"] = True
        # Source config untouched.
        self.assertFalse(cfg["stages"]["survey"]["persona"]["enabled"])
        self.assertTrue(cfg["persona"]["enabled"])


class TestWindowHelpers(unittest.TestCase):
    def test_verbatim_days_default_window(self):
        # W=2 at day 5 -> {4, 5}.
        self.assertEqual(verbatim_days(2, 5), {4, 5})

    def test_verbatim_days_includes_day0_at_start(self):
        # W=2 at day 1 -> {0, 1}. Day 0 stays in the window so recent
        # reflections keep it (own reasoning drops it via its own d>0 filter).
        self.assertEqual(verbatim_days(2, 1), {0, 1})

    def test_verbatim_days_window_one(self):
        self.assertEqual(verbatim_days(1, 5), {5})

    def test_verbatim_days_unbounded(self):
        self.assertEqual(verbatim_days(None, 4), {0, 1, 2, 3, 4})

    def test_summary_bound_default(self):
        # W=2 at day 5 -> summaries cover d < 4, i.e. d in {1,2,3}.
        self.assertEqual(summary_upper_exclusive(2, 5), 4)

    def test_summary_bound_unbounded_shows_nothing(self):
        self.assertEqual(summary_upper_exclusive(None, 9), 1)

    def test_compression_target_default(self):
        # W=2: nothing to compress until day 3, then compress day-2.
        self.assertIsNone(compression_target_day(2, 2))
        self.assertEqual(compression_target_day(2, 3), 1)
        self.assertEqual(compression_target_day(2, 5), 3)

    def test_compression_target_unbounded_never_fires(self):
        self.assertIsNone(compression_target_day(None, 10))

    def test_tiers_partition_days(self):
        # Property: at any day, every past day 1..day is in exactly one tier
        # (verbatim window OR summarised), with no gap or overlap.
        for window in (1, 2, 3, 4):
            for day in range(1, 8):
                # Restrict to days >= 1 (Day 0 is handled by the anchor, never
                # summarised); those days must partition into verbatim vs summary.
                verb = verbatim_days(window, day) & set(range(1, day + 1))
                summ_bound = summary_upper_exclusive(window, day)
                summarised = {d for d in range(1, day + 1) if d < summ_bound}
                self.assertEqual(verb & summarised, set(), (window, day))
                self.assertEqual(verb | summarised, set(range(1, day + 1)), (window, day))


if __name__ == "__main__":
    unittest.main()
