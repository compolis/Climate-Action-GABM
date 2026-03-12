
import sys
import os
import unittest
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
            brexit_vote_map=self.brexit_vote_map
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
            brexit_vote_id=BrexitVoteID.LEAVE
        )
        s = str(agent)
        self.assertIn("London", s)
        self.assertIn("Conservative", s)
        self.assertIn("Leave", s)
        persona = agent.get_persona()
        self.assertIn("London", persona)
        self.assertIn("Conservative", persona)
        self.assertIn("Leave", persona)

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
            brexit_vote_id=None
        )
        # Should not raise, should include 'Unknown' for votes
        try:
            s = str(agent)
            persona = agent.get_persona()
        except TypeError:
            self.fail("SurveyedCitizen.__str__ or get_persona() raised TypeError on None vote IDs")
        self.assertIn("Unknown", s)
        self.assertIn("Unknown", persona)

if __name__ == "__main__":
    unittest.main()
