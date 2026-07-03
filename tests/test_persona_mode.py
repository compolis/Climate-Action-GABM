"""Tests for the Tier-P persona-ablation mechanism.

Covers:
  * ``SurveyedCitizen.persona_override`` + ``get_persona()`` hook.
  * ``SurveyedNation.apply_persona_mode()`` for real / shuffled / neutral.
  * SIM_CONFIG default and resume-hard-key wiring.

Ground truth is read from ``original_survey_data`` and must never be
touched by any persona mode; several tests assert this explicitly.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from cag.abm.agent import SurveyedCitizen, NEUTRAL_PERSONA_TEXT
from cag.abm.environment import SurveyedNation, VALID_PERSONA_MODES
from cag.abm.attributes.region import UKRegionMap
from cag.abm.attributes.education import SurveyEducationMap
from cag.abm.attributes.ethnicity import SurveyEthnicityMap
from cag.abm.attributes.income import SurveyIncomeMap
from cag.abm.attributes.politics import SurveyPoliticsMap
from cag.abm.attributes.family import SurveyFamilyMap
from cag.abm.democracy.elections.ukge2019 import UKGE2019VoteID, UKGE2019VoteMap
from cag.abm.democracy.elections.brexit import BrexitVoteID, BrexitVoteMap
from gabm.abm.attributes.gender import GenderID, GenderMap
from gabm.abm.attributes.ethnicity import EthnicityID
from gabm.abm.attributes.income import IncomeID
from gabm.abm.attributes.politics import PoliticsID
from gabm.abm.attributes.education import EducationID
from gabm.abm.attributes.region import RegionID
from gabm.abm.attributes.family import FamilyID
from cag.abm.attributes.narratives import (
    SelftranscMap, SelfenhMap, OpennessMap, ConformTradMap,
    SDOMap, EDOMap, RWAMap, HIGH, LOW,
)


# Six distinct persona recipes so that every agent's composed persona text
# is unique (region + politics + vote differ), which lets the shuffle tests
# assert exact provenance.
_RECIPES = [
    dict(region_id=RegionID.LONDON, politics_id=PoliticsID.VERY_LEFT_WING,
         ukge2019_vote_id=UKGE2019VoteID.LABOUR, brexit_vote_id=BrexitVoteID.REMAIN),
    dict(region_id=RegionID.SCOTLAND, politics_id=PoliticsID.FAIRLY_LEFT_WING,
         ukge2019_vote_id=UKGE2019VoteID.GREEN, brexit_vote_id=BrexitVoteID.REMAIN),
    dict(region_id=RegionID.WALES, politics_id=PoliticsID.CENTRE,
         ukge2019_vote_id=UKGE2019VoteID.LIBERAL_DEMOCRATS, brexit_vote_id=BrexitVoteID.REMAIN),
    dict(region_id=RegionID.NORTH_EAST, politics_id=PoliticsID.SLIGHTLY_RIGHT_OF_CENTRE,
         ukge2019_vote_id=UKGE2019VoteID.CONSERVATIVE, brexit_vote_id=BrexitVoteID.LEAVE),
    dict(region_id=RegionID.SOUTH_WEST, politics_id=PoliticsID.FAIRLY_RIGHT_WING,
         ukge2019_vote_id=UKGE2019VoteID.CONSERVATIVE, brexit_vote_id=BrexitVoteID.LEAVE),
    dict(region_id=RegionID.EAST_MIDLANDS, politics_id=PoliticsID.VERY_RIGHT_WING,
         ukge2019_vote_id=UKGE2019VoteID.BREXIT, brexit_vote_id=BrexitVoteID.LEAVE),
]


def _make_env():
    return SurveyedNation(
        year=2026,
        place="UK",
        gender_map=GenderMap(),
        region_map=UKRegionMap(),
        education_map=SurveyEducationMap(),
        ethnicity_map=SurveyEthnicityMap(),
        income_map=SurveyIncomeMap(),
        politics_map=SurveyPoliticsMap(),
        family_map=SurveyFamilyMap(),
        ukge2019_vote_map=UKGE2019VoteMap(0),
        brexit_vote_map=BrexitVoteMap(1),
        selftransc_map=SelftranscMap,
        selfenh_map=SelfenhMap,
        openness_map=OpennessMap,
        conformtrad_map=ConformTradMap,
        sdo_map=SDOMap,
        edo_map=EDOMap,
        rwa_map=RWAMap,
    )


def _make_nation(n=6):
    sn = _make_env()
    for i in range(n):
        recipe = _RECIPES[i % len(_RECIPES)]
        citizen = SurveyedCitizen(
            agent_id=i,
            environment=sn,
            original_survey_data={"sentinel": i},
            year_of_birth=1990 + i,
            gender_id=GenderID.MALE if i % 2 else GenderID.FEMALE,
            ethnicity_id=EthnicityID.WHITE,
            income_id=IncomeID.BETWEEN_40000_AND_44999,
            education_id=EducationID.NO_FORMAL_QUALIFICATIONS,
            family_id=FamilyID.NOT_PARENT,
            selftransc_id=HIGH, selfenh_id=LOW, openness_id=HIGH,
            conformtrad_id=LOW, sdo_id=LOW, edo_id=HIGH, rwa_id=LOW,
            **recipe,
        )
        sn.agents_active[citizen.id] = citizen
    return sn


class TestPersonaOverride(unittest.TestCase):

    def test_default_override_is_none(self):
        sn = _make_nation(1)
        agent = sn.agents_active[0]
        self.assertIsNone(agent.persona_override)

    def test_get_persona_returns_override_verbatim(self):
        sn = _make_nation(1)
        agent = sn.agents_active[0]
        agent.persona_override = "I am a completely different person."
        self.assertEqual(agent.get_persona(), "I am a completely different person.")

    def test_clearing_override_restores_real_persona(self):
        sn = _make_nation(1)
        agent = sn.agents_active[0]
        real = agent.get_persona()
        agent.persona_override = "override"
        agent.persona_override = None
        self.assertEqual(agent.get_persona(), real)


class TestApplyPersonaModeReal(unittest.TestCase):

    def test_real_returns_identity_map(self):
        sn = _make_nation(6)
        mapping = sn.apply_persona_mode("real", seed=42)
        self.assertEqual(mapping, {i: i for i in range(6)})

    def test_real_leaves_personas_unchanged(self):
        sn = _make_nation(6)
        before = {i: sn.agents_active[i].get_persona() for i in range(6)}
        sn.apply_persona_mode("real", seed=42)
        for i in range(6):
            self.assertIsNone(sn.agents_active[i].persona_override)
            self.assertEqual(sn.agents_active[i].get_persona(), before[i])


class TestApplyPersonaModeNeutral(unittest.TestCase):

    def test_neutral_sets_constant_text(self):
        sn = _make_nation(6)
        mapping = sn.apply_persona_mode("neutral", seed=42)
        for i in range(6):
            self.assertEqual(sn.agents_active[i].get_persona(), NEUTRAL_PERSONA_TEXT)
            self.assertEqual(mapping[i], "NEUTRAL")

    def test_neutral_removes_real_demographic_signal(self):
        sn = _make_nation(6)
        sn.apply_persona_mode("neutral", seed=42)
        for i in range(6):
            persona = sn.agents_active[i].get_persona()
            for leak in ("London", "Scotland", "Conservative", "Labour", "Leave", "Remain"):
                self.assertNotIn(leak, persona)

    def test_neutral_leaves_ground_truth_untouched(self):
        sn = _make_nation(6)
        gt_before = {i: sn.agents_active[i].original_survey_data for i in range(6)}
        sn.apply_persona_mode("neutral", seed=42)
        for i in range(6):
            self.assertEqual(sn.agents_active[i].original_survey_data, gt_before[i])


class TestApplyPersonaModeShuffled(unittest.TestCase):

    def test_shuffled_map_is_a_bijection(self):
        sn = _make_nation(6)
        mapping = sn.apply_persona_mode("shuffled", seed=42)
        self.assertEqual(sorted(mapping.keys()), list(range(6)))
        self.assertEqual(sorted(mapping.values()), list(range(6)))

    def test_shuffled_is_a_derangement(self):
        sn = _make_nation(6)
        mapping = sn.apply_persona_mode("shuffled", seed=42)
        for agent_id, source_id in mapping.items():
            self.assertNotEqual(agent_id, source_id)

    def test_shuffled_persona_matches_source_original(self):
        sn = _make_nation(6)
        originals = {i: sn.agents_active[i].get_persona() for i in range(6)}
        mapping = sn.apply_persona_mode("shuffled", seed=42)
        for agent_id, source_id in mapping.items():
            self.assertEqual(
                sn.agents_active[agent_id].get_persona(),
                originals[source_id],
            )

    def test_shuffled_persona_is_someone_elses(self):
        sn = _make_nation(6)
        originals = {i: sn.agents_active[i].get_persona() for i in range(6)}
        sn.apply_persona_mode("shuffled", seed=42)
        for i in range(6):
            self.assertNotEqual(sn.agents_active[i].get_persona(), originals[i])

    def test_shuffled_is_deterministic_given_seed(self):
        map1 = _make_nation(6).apply_persona_mode("shuffled", seed=7)
        map2 = _make_nation(6).apply_persona_mode("shuffled", seed=7)
        self.assertEqual(map1, map2)

    def test_shuffled_leaves_ground_truth_untouched(self):
        sn = _make_nation(6)
        gt_before = {i: sn.agents_active[i].original_survey_data for i in range(6)}
        sn.apply_persona_mode("shuffled", seed=42)
        for i in range(6):
            self.assertEqual(sn.agents_active[i].original_survey_data, gt_before[i])


class TestApplyPersonaModeValidation(unittest.TestCase):

    def test_invalid_mode_raises(self):
        sn = _make_nation(3)
        with self.assertRaises(ValueError):
            sn.apply_persona_mode("bogus", seed=42)

    def test_none_mode_defaults_to_real(self):
        sn = _make_nation(3)
        mapping = sn.apply_persona_mode(None, seed=42)
        self.assertEqual(mapping, {i: i for i in range(3)})

    def test_valid_modes_tuple(self):
        self.assertEqual(VALID_PERSONA_MODES, ("real", "shuffled", "neutral"))


class TestSimConfigWiring(unittest.TestCase):

    def test_sim_config_default_is_real(self):
        from cag.abm.sim import SIM_CONFIG, VALID_PERSONA_MODES as SIM_VALID
        self.assertEqual(SIM_CONFIG["persona_mode"], "real")
        self.assertEqual(SIM_VALID, ("real", "shuffled", "neutral"))

    def test_persona_mode_is_resume_hard_key(self):
        from cag.io.checkpoint import _RESUME_HARD_KEYS
        self.assertIn("persona_mode", _RESUME_HARD_KEYS)

    def test_persona_map_in_result_schema(self):
        from cag.io.results import _RESULT_CSV_SCHEMAS
        self.assertEqual(
            _RESULT_CSV_SCHEMAS["persona_map"],
            ["agent_id", "source_agent_id", "persona_mode"],
        )


if __name__ == "__main__":
    unittest.main()
