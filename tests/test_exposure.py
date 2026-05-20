"""Tests for affinity-based political-exposure assignment.

Covers:
- Module-level scorer monotonicity (`_green_affinity_score`,
  `_reform_affinity_score`)
- `rule_affinity_rank` hits target marginals exactly (modulo rounding)
- Reproducibility under fixed seed
- Dispatcher routing and validation
- Target / weight preset resolution
"""
import os
import sys
import unittest

import numpy as np

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from cag.abm.agent import SurveyedCitizen, PoliticalAgent
from cag.abm.environment import (
    SurveyedNation,
    VALID_EXPOSURE_MODES,
    TARGETS_COMMITTED_MINORITY_SYMMETRIC,
    TARGETS_COMMITTED_MINORITY_UK_2024,
    TARGETS_LEGACY_V05,
    TARGET_PRESETS,
    DEFAULT_AFFINITY_WEIGHTS,
    AFFINITY_WEIGHTS_VOTE_DOMINANT,
    AFFINITY_WEIGHTS_VALUES_DOMINANT,
    AFFINITY_WEIGHT_PRESETS,
    _green_affinity_score,
    _reform_affinity_score,
    _affinity_score,
    _resolve_targets,
    _resolve_weights,
    _safe_int,
)
from cag.abm.democracy.elections.brexit import BrexitVoteID
from cag.abm.democracy.elections.ukge2019 import UKGE2019VoteID
from cag.abm.attributes.region import RegionID
from cag.abm.attributes.education import EducationID
from gabm.abm.attributes.politics import PoliticsID


# ---------------------------------------------------------------------------
# Citizen builders
# ---------------------------------------------------------------------------

def _make_citizen(env, agent_id, **kwargs):
    defaults = dict(
        year_of_birth=1980,
        region_id=RegionID.LONDON,
        education_id=EducationID.UNIVERSITY_OR_CNAA_FIRST_DEGREE,
        politics_id=PoliticsID.CENTRE,
        ukge2019_vote_id=UKGE2019VoteID.LABOUR,
        brexit_vote_id=BrexitVoteID.REMAIN,
        openness_id=3, selftransc_id=3, conformtrad_id=3,
        sdo_id=4, rwa_id=3,
    )
    defaults.update(kwargs)
    c = SurveyedCitizen(agent_id=agent_id, environment=env, **defaults)
    env.agents_active[c.id] = c
    return c


def _make_population(env, n, seed=0):
    """Build a deterministic but varied population of size n."""
    rng = np.random.default_rng(seed)
    regions = [RegionID.LONDON, RegionID.SCOTLAND, RegionID.WALES,
               RegionID.NORTH_EAST, RegionID.NORTH_WEST,
               RegionID.WEST_MIDLANDS, RegionID.EAST_OF_ENGLAND]
    educations = [EducationID.UNIVERSITY_OR_CNAA_FIRST_DEGREE,
                  EducationID.UNIVERSITY_OR_CNAA_HIGHER_DEGREE,
                  EducationID.TEACHING_QUALIFICATION,
                  EducationID.UNKNOWN]
    politics = [PoliticsID.VERY_LEFT_WING, PoliticsID.FAIRLY_LEFT_WING,
                PoliticsID.SLIGHTLY_LEFT_OF_CENTRE, PoliticsID.CENTRE,
                PoliticsID.SLIGHTLY_RIGHT_OF_CENTRE,
                PoliticsID.FAIRLY_RIGHT_WING, PoliticsID.VERY_RIGHT_WING]
    votes = [UKGE2019VoteID.GREEN, UKGE2019VoteID.LIBERAL_DEMOCRATS,
             UKGE2019VoteID.LABOUR, UKGE2019VoteID.CONSERVATIVE,
             UKGE2019VoteID.BREXIT]
    brexits = [BrexitVoteID.REMAIN, BrexitVoteID.LEAVE, BrexitVoteID.UNKNOWN]
    for i in range(n):
        _make_citizen(
            env, i,
            year_of_birth=int(rng.integers(1940, 2005)),
            region_id=regions[int(rng.integers(0, len(regions)))],
            education_id=educations[int(rng.integers(0, len(educations)))],
            politics_id=politics[int(rng.integers(0, len(politics)))],
            ukge2019_vote_id=votes[int(rng.integers(0, len(votes)))],
            brexit_vote_id=brexits[int(rng.integers(0, len(brexits)))],
            openness_id=int(rng.integers(1, 7)),
            selftransc_id=int(rng.integers(1, 7)),
            conformtrad_id=int(rng.integers(1, 7)),
            sdo_id=int(rng.integers(1, 8)),
            rwa_id=int(rng.integers(1, 7)),
        )


def _make_nation(n=200, seed=0):
    sn = SurveyedNation()
    sn.political_agent_a = PoliticalAgent("agent_a", "pro_climate")
    sn.political_agent_b = PoliticalAgent("agent_b", "anti_climate")
    _make_population(sn, n, seed=seed)
    return sn


# ---------------------------------------------------------------------------
# Scorer tests
# ---------------------------------------------------------------------------

class TestScorerMonotonicity(unittest.TestCase):
    def setUp(self):
        self.sn = SurveyedNation()
        self.sn.political_agent_a = PoliticalAgent("a", "pro_climate")
        self.sn.political_agent_b = PoliticalAgent("b", "anti_climate")

    def _score(self, side, **overrides):
        c = _make_citizen(self.sn, agent_id=f"tmp{len(self.sn.agents_active)}", **overrides)
        return _affinity_score(c, 2024, None) if side == "raw" else (
            _green_affinity_score(c, 2024) if side == "A" else _reform_affinity_score(c, 2024)
        )

    def test_green_openness_monotonic(self):
        scores = [self._score("A", openness_id=v) for v in (1, 3, 6)]
        self.assertLess(scores[0], scores[1])
        self.assertLess(scores[1], scores[2])

    def test_green_rwa_monotonic_negative(self):
        scores = [self._score("A", rwa_id=v) for v in (1, 3, 6)]
        self.assertGreater(scores[0], scores[1])
        self.assertGreater(scores[1], scores[2])

    def test_reform_rwa_monotonic_positive(self):
        scores = [self._score("B", rwa_id=v) for v in (1, 3, 6)]
        self.assertLess(scores[0], scores[1])
        self.assertLess(scores[1], scores[2])

    def test_vote_bonus_green(self):
        sg = self._score("A", ukge2019_vote_id=UKGE2019VoteID.GREEN)
        sc = self._score("A", ukge2019_vote_id=UKGE2019VoteID.CONSERVATIVE)
        sb = self._score("A", ukge2019_vote_id=UKGE2019VoteID.BREXIT)
        self.assertGreater(sg, sc)
        self.assertGreater(sc, sb)

    def test_vote_bonus_reform(self):
        sg = self._score("B", ukge2019_vote_id=UKGE2019VoteID.GREEN)
        sc = self._score("B", ukge2019_vote_id=UKGE2019VoteID.CONSERVATIVE)
        sb = self._score("B", ukge2019_vote_id=UKGE2019VoteID.BREXIT)
        self.assertGreater(sb, sc)
        self.assertGreater(sc, sg)

    def test_unknown_attributes_are_neutral(self):
        # All UNKNOWN inputs should give a finite, non-NaN score (the
        # constant offset for that side's free intercept).
        c = _make_citizen(
            self.sn, agent_id="unknown",
            openness_id=0, selftransc_id=0, conformtrad_id=0,
            sdo_id=0, rwa_id=0,
            year_of_birth=None,
            region_id=RegionID.UNKNOWN,
            education_id=EducationID.UNKNOWN,
            politics_id=PoliticsID.UNKNOWN,
            ukge2019_vote_id=UKGE2019VoteID.UNKNOWN,
            brexit_vote_id=BrexitVoteID.UNKNOWN,
        )
        self.assertTrue(np.isfinite(_green_affinity_score(c, 2024)))
        self.assertTrue(np.isfinite(_reform_affinity_score(c, 2024)))

    def test_affinity_score_dispatcher(self):
        c = _make_citizen(self.sn, agent_id="disp")
        self.assertEqual(_affinity_score(c, "A", 2024),
                         _green_affinity_score(c, 2024))
        self.assertEqual(_affinity_score(c, "B", 2024),
                         _reform_affinity_score(c, 2024))
        with self.assertRaises(ValueError):
            _affinity_score(c, "X", 2024)


# ---------------------------------------------------------------------------
# Rank mode
# ---------------------------------------------------------------------------

class TestAffinityRank(unittest.TestCase):
    def test_marginals_hit_exactly(self):
        sn = _make_nation(n=200, seed=1)
        targets = TARGETS_COMMITTED_MINORITY_SYMMETRIC
        sn.assign_political_exposure(mode="rule_affinity_rank", targets=targets)
        counts = {k: 0 for k in ("A-only", "B-only", "both", "neither")}
        for c in sn.agents_active.values():
            counts[c.political_exposure] += 1
        n = sum(counts.values())
        # Each count must equal round(n*target) exactly (with neither
        # absorbing the slack from int rounding).
        self.assertEqual(counts["B-only"], int(round(n * targets["B-only"])))
        self.assertEqual(counts["A-only"], int(round(n * targets["A-only"])))
        self.assertEqual(counts["both"], int(round(n * targets["both"])))
        # neither = remainder
        self.assertEqual(counts["neither"],
                         n - counts["A-only"] - counts["B-only"] - counts["both"])

    def test_audience_lists_populated(self):
        sn = _make_nation(n=100, seed=2)
        sn.assign_political_exposure(mode="rule_affinity_rank")
        a_aud = sn.political_agent_a.connected_citizens
        b_aud = sn.political_agent_b.connected_citizens
        self.assertTrue(len(a_aud) > 0)
        self.assertTrue(len(b_aud) > 0)
        # 'both' citizens appear in both audiences
        both_ids = {c.id for c in sn.agents_active.values()
                    if c.political_exposure == "both"}
        a_ids = {c.id for c in a_aud}
        b_ids = {c.id for c in b_aud}
        self.assertTrue(both_ids.issubset(a_ids))
        self.assertTrue(both_ids.issubset(b_ids))

    def test_reproducible(self):
        sn1 = _make_nation(n=150, seed=3)
        sn2 = _make_nation(n=150, seed=3)
        sn1.assign_political_exposure(mode="rule_affinity_rank")
        sn2.assign_political_exposure(mode="rule_affinity_rank")
        e1 = [sn1.agents_active[i].political_exposure for i in range(150)]
        e2 = [sn2.agents_active[i].political_exposure for i in range(150)]
        self.assertEqual(e1, e2)


# ---------------------------------------------------------------------------
# Dispatcher + presets
# ---------------------------------------------------------------------------

class TestDispatcher(unittest.TestCase):
    def test_unknown_mode_raises(self):
        sn = _make_nation(n=20, seed=0)
        with self.assertRaises(ValueError):
            sn.assign_political_exposure(mode="rule_nonsense")

    def test_priority_chain_still_works(self):
        sn = _make_nation(n=50, seed=0)
        sn.assign_political_exposure(mode="rule_priority_chain")
        # Every citizen has a label
        for c in sn.agents_active.values():
            self.assertIn(c.political_exposure,
                          {"A-only", "B-only", "both", "neither"})

    def test_default_mode_is_affinity_rank(self):
        # mode=None should pick rule_affinity_rank
        sn = _make_nation(n=100, seed=4)
        sn.assign_political_exposure()  # no mode arg
        # Should hit the symmetric committed-minority targets
        counts = {k: 0 for k in ("A-only", "B-only", "both", "neither")}
        for c in sn.agents_active.values():
            counts[c.political_exposure] += 1
        # ~45% neither under symmetric default
        self.assertAlmostEqual(counts["neither"] / 100, 0.45, delta=0.02)


class TestPresetResolution(unittest.TestCase):
    def test_target_preset_name(self):
        self.assertEqual(_resolve_targets("committed_minority_symmetric"),
                         TARGETS_COMMITTED_MINORITY_SYMMETRIC)
        self.assertEqual(_resolve_targets("legacy_v05"),
                         TARGETS_LEGACY_V05)

    def test_target_dict_passthrough(self):
        d = {"A-only": 0.1, "B-only": 0.1, "both": 0.2, "neither": 0.6}
        self.assertEqual(_resolve_targets(d), d)

    def test_target_invalid_keys(self):
        with self.assertRaises(ValueError):
            _resolve_targets({"a": 0.5, "b": 0.5})

    def test_target_invalid_sum(self):
        with self.assertRaises(ValueError):
            _resolve_targets({"A-only": 0.5, "B-only": 0.5,
                              "both": 0.5, "neither": 0.5})

    def test_target_unknown_preset(self):
        with self.assertRaises(ValueError):
            _resolve_targets("bogus_preset")

    def test_weight_preset_name(self):
        self.assertIs(_resolve_weights("balanced"), DEFAULT_AFFINITY_WEIGHTS)
        self.assertIs(_resolve_weights("vote_dominant"),
                      AFFINITY_WEIGHTS_VOTE_DOMINANT)
        self.assertIs(_resolve_weights("values_dominant"),
                      AFFINITY_WEIGHTS_VALUES_DOMINANT)

    def test_weight_none_returns_default(self):
        self.assertIs(_resolve_weights(None), DEFAULT_AFFINITY_WEIGHTS)

    def test_weight_unknown_preset(self):
        with self.assertRaises(ValueError):
            _resolve_weights("bogus")

    def test_weight_invalid_dict(self):
        with self.assertRaises(ValueError):
            _resolve_weights({"X": {}})

    def test_valid_modes_constant(self):
        self.assertIn("rule_affinity_rank", VALID_EXPOSURE_MODES)
        self.assertIn("rule_priority_chain", VALID_EXPOSURE_MODES)

    def test_weight_presets_dict(self):
        self.assertEqual(set(AFFINITY_WEIGHT_PRESETS),
                         {"balanced", "vote_dominant", "values_dominant"})

    def test_target_presets_dict(self):
        self.assertEqual(set(TARGET_PRESETS),
                         {"committed_minority_symmetric",
                          "committed_minority_uk_2024",
                          "legacy_v05"})


# ---------------------------------------------------------------------------
# _safe_int: regression test for the GABM-attribute extraction bug
# (silently returned 0 for every NarrativeAttributeID / PoliticsID because
#  int(GABMAttributeID(n)) raises TypeError, killing all psych-scale and
#  politics signals in the affinity scorer).
# ---------------------------------------------------------------------------

class TestSafeInt(unittest.TestCase):
    def test_safe_int_on_gabm_attribute(self):
        # PoliticsID is a GABMAttributeID subclass exposing .id
        self.assertEqual(_safe_int(PoliticsID.VERY_LEFT_WING), 1)
        self.assertEqual(_safe_int(PoliticsID.CENTRE), 4)
        self.assertEqual(_safe_int(PoliticsID.VERY_RIGHT_WING), 7)

    def test_safe_int_on_raw_int(self):
        self.assertEqual(_safe_int(3), 3)
        self.assertEqual(_safe_int(0), 0)

    def test_safe_int_on_none(self):
        self.assertEqual(_safe_int(None), 0)

    def test_psych_scales_contribute_to_score(self):
        # Build two otherwise-identical citizens differing ONLY on
        # openness; their green-affinity scores must differ. This is
        # the integration-level guard that catches the original bug.
        sn = SurveyedNation()
        sn.political_agent_a = PoliticalAgent("a", "pro_climate")
        sn.political_agent_b = PoliticalAgent("b", "anti_climate")
        c_lo = _make_citizen(sn, agent_id="lo", openness_id=1)
        c_hi = _make_citizen(sn, agent_id="hi", openness_id=6)
        s_lo = _green_affinity_score(c_lo, 2024)
        s_hi = _green_affinity_score(c_hi, 2024)
        self.assertLess(s_lo, s_hi)


if __name__ == "__main__":
    unittest.main()
