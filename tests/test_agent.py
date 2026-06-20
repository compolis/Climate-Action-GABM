
import sys
import os
import unittest
from unittest import mock
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))
from cag.abm.agent import SurveyedCitizen
from cag.abm.environment import SurveyedNation
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
from cag.abm.attributes.narratives import SelftranscMap, SelfenhMap, OpennessMap, ConformTradMap, SDOMap, EDOMap, RWAMap, NarrativeAttributeID, UNKNOWN, HIGH, LOW, MODERATE

class TestSurveyedCitizen(unittest.TestCase):
    def setUp(self):
        self.gender_map = GenderMap()
        self.region_map = UKRegionMap()
        self.education_map = SurveyEducationMap()
        self.ethnicity_map = SurveyEthnicityMap()
        self.income_map = SurveyIncomeMap()
        self.politics_map = SurveyPoliticsMap()
        self.family_map = SurveyFamilyMap()
        self.ukge2019_vote_map = UKGE2019VoteMap(0)
        self.brexit_vote_map = BrexitVoteMap(1)
        self.selftransc_map = SelftranscMap
        self.selfenh_map = SelfenhMap
        self.openness_map = OpennessMap
        self.conformtrad_map = ConformTradMap
        self.sdo_map = SDOMap
        self.edo_map = EDOMap
        self.rwa_map = RWAMap
        self.env = SurveyedNation(
            year=2026,
            place="UK",
            gender_map=self.gender_map,
            region_map=self.region_map,
            education_map=self.education_map,
            ethnicity_map=self.ethnicity_map,
            income_map=self.income_map,
            politics_map=self.politics_map,
            family_map=self.family_map,
            ukge2019_vote_map=self.ukge2019_vote_map,
            brexit_vote_map=self.brexit_vote_map,
            selftransc_map=self.selftransc_map,
            selfenh_map=self.selfenh_map,
            openness_map=self.openness_map,
            conformtrad_map=self.conformtrad_map,
            sdo_map=self.sdo_map,
            edo_map=self.edo_map,
            rwa_map=self.rwa_map
        )

    def test_agent_str_and_persona(self):
        agent = SurveyedCitizen(
            agent_id=1,
            environment=self.env,
            year_of_birth=2000,
            gender_id=GenderID.MALE,
            region_id=RegionID.LONDON,
            ethnicity_id=EthnicityID.WHITE,
            income_id=IncomeID.BETWEEN_40000_AND_44999,
            education_id=EducationID.NO_FORMAL_QUALIFICATIONS,
            politics_id=PoliticsID.CENTRE,
            family_id=FamilyID.NOT_PARENT,
            ukge2019_vote_id=UKGE2019VoteID.CONSERVATIVE,
            brexit_vote_id=BrexitVoteID.LEAVE,
            selftransc_id=HIGH,
            selfenh_id=HIGH,
            openness_id=HIGH,
            conformtrad_id=HIGH,
            sdo_id=HIGH,
            edo_id=HIGH,
            rwa_id=HIGH
        )
        s = str(agent)
        self.assertIn("London", s)
        self.assertIn("Conservative", s)
        self.assertIn("voted to leave", s)
        persona = agent.get_persona()
        self.assertIn("London", persona)
        self.assertIn("Conservative", persona)
        self.assertIn("voted to leave", persona)

    def test_unknown_vote(self):
        agent = SurveyedCitizen(
            agent_id=2,
            environment=self.env,
            year_of_birth=2000,
            gender_id=GenderID.FEMALE,
            region_id=RegionID.LONDON,
            ethnicity_id=EthnicityID.WHITE,
            income_id=IncomeID.BETWEEN_40000_AND_44999,
            education_id=EducationID.NO_FORMAL_QUALIFICATIONS,
            politics_id=PoliticsID.CENTRE,
            family_id=FamilyID.NOT_PARENT,
            ukge2019_vote_id=None,
            brexit_vote_id=None,
            selftransc_id=HIGH,
            selfenh_id=HIGH,
            openness_id=HIGH,
            conformtrad_id=HIGH,
            sdo_id=HIGH,
            edo_id=HIGH,
            rwa_id=HIGH
        )
        # Should not raise, should include 'Unknown' for votes
        try:
            s = str(agent)
            persona = agent.get_persona()
        except TypeError:
            self.fail("SurveyedCitizen.__str__ or get_persona() raised TypeError on None vote IDs")
        self.assertIn("Unknown", s)
        self.assertIn("Unknown", persona)


class TestDebiasedSurvey(unittest.TestCase):
    """Tests for the debias=True path in administer_survey()."""

    def _make_citizen(self):
        env = mock.MagicMock()
        citizen = SurveyedCitizen(
            agent_id=42, environment=env, year_of_birth=1985,
            original_survey_data={"page5posttreatment6_5": 4.0},
        )
        citizen.get_persona = mock.MagicMock(return_value="I am a 41 year old engineer.")
        citizen.get_narrative = mock.MagicMock(return_value="I value independence.")
        return citizen

    @mock.patch("cag.abm.agent.send_chat", return_value="D")
    def test_debias_false_single_call(self, mock_send):
        citizen = self._make_citizen()
        from cag.abm.attributes.opinion import ClimatePolicyID
        citizen.administer_survey(ClimatePolicyID.BAN_PETROL_CARS, day=0, debias=False)
        self.assertEqual(mock_send.call_count, 1)

    @mock.patch("cag.abm.agent.send_chat", side_effect=["Some reasoning about factors.", "D"])
    def test_debias_true_two_calls(self, mock_send):
        citizen = self._make_citizen()
        from cag.abm.attributes.opinion import ClimatePolicyID
        citizen.administer_survey(ClimatePolicyID.BAN_PETROL_CARS, day=0, debias=True)
        self.assertEqual(mock_send.call_count, 2)

    @mock.patch("cag.abm.agent.send_chat", side_effect=["Reasoning text.", "E"])
    def test_debias_step1_has_anti_sycophancy(self, mock_send):
        citizen = self._make_citizen()
        from cag.abm.attributes.opinion import ClimatePolicyID
        citizen.administer_survey(ClimatePolicyID.BAN_PETROL_CARS, day=0, debias=True)
        step1_user_prompt = mock_send.call_args_list[0][1].get("user_prompt",
                            mock_send.call_args_list[0][0][1] if len(mock_send.call_args_list[0][0]) > 1 else "")
        self.assertIn("faithfully simulate", step1_user_prompt)
        self.assertIn("socially desirable", step1_user_prompt)

    @mock.patch("cag.abm.agent.send_chat", side_effect=["Agent reasoning about policy.", "F"])
    def test_debias_step2_has_reasoning(self, mock_send):
        citizen = self._make_citizen()
        from cag.abm.attributes.opinion import ClimatePolicyID
        citizen.administer_survey(ClimatePolicyID.BAN_PETROL_CARS, day=0, debias=True)
        step2_system_prompt = mock_send.call_args_list[1][0][0]
        self.assertIn("Agent reasoning about policy.", step2_system_prompt)
        self.assertIn("Your reasoning about this policy:", step2_system_prompt)

    @mock.patch("cag.abm.agent.send_chat", side_effect=["Reasoning.", "C"])
    def test_debias_returns_same_type(self, mock_send):
        citizen = self._make_citizen()
        from cag.abm.attributes.opinion import ClimatePolicyID
        result = citizen.administer_survey(ClimatePolicyID.BAN_PETROL_CARS, day=0, debias=True)
        self.assertIsInstance(result, tuple)
        self.assertEqual(len(result), 2)
        self.assertIsInstance(result[0], str)
        self.assertIsInstance(result[1], int)
        self.assertEqual(result[0], "C")
        self.assertEqual(result[1], -1)

    @mock.patch("cag.abm.agent.send_chat", side_effect=["Reasoning.", "B"])
    def test_debias_appends_history(self, mock_send):
        citizen = self._make_citizen()
        from cag.abm.attributes.opinion import ClimatePolicyID
        policy = ClimatePolicyID.BAN_PETROL_CARS
        citizen.administer_survey(policy, day=0, debias=True)
        self.assertIn(policy, citizen.opinion_history)
        self.assertEqual(citizen.opinion_history[policy], [(0, -2)])

    @mock.patch("cag.abm.agent.send_chat", side_effect=["My reasoning text.", "G"])
    def test_debias_stores_reasoning(self, mock_send):
        citizen = self._make_citizen()
        from cag.abm.attributes.opinion import ClimatePolicyID
        policy = ClimatePolicyID.BAN_PETROL_CARS
        citizen.administer_survey(policy, day=0, debias=True)
        self.assertIn(policy, citizen.survey_reasoning)
        self.assertEqual(len(citizen.survey_reasoning[policy]), 1)
        self.assertEqual(citizen.survey_reasoning[policy][0], (0, "My reasoning text."))

    @mock.patch("cag.abm.agent.send_chat", side_effect=["Some reasoning.", "G. Strongly support"])
    def test_debias_stores_raw_response(self, mock_send):
        citizen = self._make_citizen()
        from cag.abm.attributes.opinion import ClimatePolicyID
        policy = ClimatePolicyID.BAN_PETROL_CARS
        citizen.administer_survey(policy, day=2, debias=True)
        self.assertIn(policy, citizen.survey_raw_response)
        self.assertEqual(citizen.survey_raw_response[policy], [(2, "G. Strongly support")])

    @mock.patch("cag.abm.agent.send_chat", return_value="D")
    def test_debias_false_no_reasoning_stored(self, mock_send):
        citizen = self._make_citizen()
        from cag.abm.attributes.opinion import ClimatePolicyID
        policy = ClimatePolicyID.BAN_PETROL_CARS
        citizen.administer_survey(policy, day=0, debias=False)
        self.assertEqual(citizen.survey_reasoning, {})

    @mock.patch("cag.abm.agent.send_chat", return_value="A nuanced view; the answer is B.")
    def test_no_debias_stores_raw_response(self, mock_send):
        citizen = self._make_citizen()
        from cag.abm.attributes.opinion import ClimatePolicyID
        policy = ClimatePolicyID.BAN_PETROL_CARS
        citizen.administer_survey(policy, day=1, debias=False)
        self.assertIn(policy, citizen.survey_raw_response)
        self.assertEqual(
            citizen.survey_raw_response[policy],
            [(1, "A nuanced view; the answer is B.")],
        )


class TestDay0Seeding(unittest.TestCase):
    """Tests for seed_opinion_from_ground_truth and seed_opinion_with_rationale."""

    def _make_citizen(self, raw_value=6.0):
        env = mock.MagicMock()
        citizen = SurveyedCitizen(
            agent_id=42, environment=env, year_of_birth=1985,
            original_survey_data={"page5posttreatment6_5": raw_value},
        )
        citizen.get_persona = mock.MagicMock(return_value="I am a 41 year old engineer.")
        citizen.get_narrative = mock.MagicMock(return_value="I value independence.")
        return citizen

    @mock.patch("cag.abm.agent.send_chat")
    def test_seed_from_ground_truth_no_llm_call(self, mock_send):
        from cag.abm.attributes.opinion import ClimatePolicyID
        citizen = self._make_citizen(raw_value=6.0)
        gt = citizen.seed_opinion_from_ground_truth(ClimatePolicyID.BAN_PETROL_CARS, day=0)
        self.assertEqual(mock_send.call_count, 0)
        self.assertEqual(gt, 2)

    def test_seed_from_ground_truth_writes_history(self):
        from cag.abm.attributes.opinion import ClimatePolicyID
        policy = ClimatePolicyID.BAN_PETROL_CARS
        citizen = self._make_citizen(raw_value=2.0)
        citizen.seed_opinion_from_ground_truth(policy, day=0)
        self.assertEqual(citizen.opinion_history[policy], [(0, -2)])

    def test_seed_from_ground_truth_appends_no_overwrite(self):
        from cag.abm.attributes.opinion import ClimatePolicyID
        policy = ClimatePolicyID.BAN_PETROL_CARS
        citizen = self._make_citizen(raw_value=5.0)
        citizen.opinion_history[policy] = [(-1, 0)]  # pretend prior entry
        citizen.seed_opinion_from_ground_truth(policy, day=0)
        self.assertEqual(citizen.opinion_history[policy], [(-1, 0), (0, 1)])

    @mock.patch("cag.abm.agent.send_chat", return_value="My reasoning.")
    def test_seed_with_rationale_one_llm_call(self, mock_send):
        from cag.abm.attributes.opinion import ClimatePolicyID
        citizen = self._make_citizen(raw_value=6.0)
        gt, rationale = citizen.seed_opinion_with_rationale(
            ClimatePolicyID.BAN_PETROL_CARS, day=0,
        )
        self.assertEqual(mock_send.call_count, 1)
        self.assertEqual(gt, 2)
        self.assertEqual(rationale, "My reasoning.")

    @mock.patch("cag.abm.agent.send_chat", return_value="My reasoning.")
    def test_seed_with_rationale_writes_history_and_reasoning(self, mock_send):
        from cag.abm.attributes.opinion import ClimatePolicyID
        policy = ClimatePolicyID.BAN_PETROL_CARS
        citizen = self._make_citizen(raw_value=7.0)
        citizen.seed_opinion_with_rationale(policy, day=0)
        self.assertEqual(citizen.opinion_history[policy], [(0, 3)])
        self.assertEqual(citizen.survey_reasoning[policy], [(0, "My reasoning.")])

    @mock.patch("cag.abm.agent.send_chat", return_value="Reasoning text.")
    def test_seed_with_rationale_prompt_mentions_response_label(self, mock_send):
        from cag.abm.attributes.opinion import ClimatePolicyID
        policy = ClimatePolicyID.BAN_PETROL_CARS
        citizen = self._make_citizen(raw_value=6.0)  # numeric +2 → "Somewhat support"
        citizen.seed_opinion_with_rationale(policy, day=0)
        user_prompt = mock_send.call_args_list[0][0][1]
        self.assertIn("Somewhat support", user_prompt)
        self.assertIn("your background", user_prompt)


if __name__ == "__main__":
    unittest.main()
