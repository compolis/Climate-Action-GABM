"""
Environment module for Climate-Action-GABM.
"""
# Metadata
__author__ = ["Andy Turner <agdturner@gmail.com>", "Charlie Pilgrim <pilgrimcharlie2@gmail.com>"]
__version__ = "0.2.0"
__copyright__ = "Copyright (c) 2026 GABM contributors, University of Leeds"

# Standard library imports
import logging
import pandas as pd
from typing import Dict
# GABM imports
from gabm.abm.environment import Nation
from gabm.abm.attributes.gender import GenderMap
# Local imports
from gabm.abm.attributes.opinion import OpinionTopicID, Opinion
from cag.abm.attributes.region import UKRegionMap
from cag.abm.attributes.education import SurveyEducationMap
from cag.abm.attributes.ethnicity import SurveyEthnicityMap
from cag.abm.attributes.income import SurveyIncomeMap
from cag.abm.attributes.politics import SurveyPoliticsMap
from cag.abm.attributes.family import SurveyFamilyMap
from cag.abm.democracy.elections.ukge2019 import UKGE2019VoteMap
from cag.abm.democracy.elections.brexit import BrexitVoteMap
from cag.abm.attributes.narratives import SelftranscMap, SelfenhMap, OpennessMap, ConformTradMap, SDOMap, EDOMap, RWAMap

class SurveyedNation(Nation):
    """
    A Surveyed Nation environment class for Climate-Action-GABM, inheriting from the GABM Nation class.

    .. note::
            Inherits all attributes from :class:`Nation`.

    Attributes:
        region_map (UKRegionMap):
            A UKRegionMap instance for region attribute lookups.
        education_map (SurveyEducationMap):
            A SurveyEducationMap instance for education attribute lookups.
        ethnicity_map (SurveyEthnicityMap):
            A SurveyEthnicityMap instance for ethnicity attribute lookups.
        income_map (SurveyIncomeMap):
            A SurveyIncomeMap instance for income attribute lookups.
        politics_map (SurveyPoliticsMap):
            A SurveyPoliticsMap instance for politics attribute lookups.
        family_map (SurveyFamilyMap):
            A SurveyFamilyMap instance for family attribute lookups.
        ukge2019_vote_map (UKGE2019VoteMap):
            A UKGE2019VoteMap instance for UK General Election 2019 vote attribute lookups.
        brexit_vote_map (BrexitVoteMap):
            A BrexitVoteMap instance for Brexit referendum vote attribute lookups.
        selftransc_map (SelftranscMap):
            A SelftranscMap instance for self-transcendence value attribute lookups.
        selfenh_map (SelfenhMap):
            A SelfenhMap instance for self-enhancement value attribute lookups.
        openness_map (OpennessMap):
            An OpennessMap instance for openness attribute lookups.
        conformtrad_map (ConformTradMap):
            A ConformTradMap instance for conformity-tradition attribute lookups.
        sdo_map (SDOMap):
            An SDOMap instance for social dominance orientation attribute lookups.
        edo_map (EDOMap):
            An EDOMap instance for environmental dominance orientation attribute lookups.
        rwa_map (RWAMap):
            An RWAMap instance for right-wing authoritarianism attribute lookups.
    """
    def __init__(self, year: int = 2026, place: str = "UK", 
        gender_map: GenderMap = None,
        opinions: Dict[OpinionTopicID, Opinion] = None,
        region_map: UKRegionMap = None,
        education_map: SurveyEducationMap = None,
        ethnicity_map: SurveyEthnicityMap = None,
        income_map: SurveyIncomeMap = None,
        politics_map: SurveyPoliticsMap = None,
        family_map: SurveyFamilyMap = None,
        ukge2019_vote_map: UKGE2019VoteMap = None,
        brexit_vote_map: BrexitVoteMap = None,
        selftransc_map: SelftranscMap = None,
        selfenh_map: SelfenhMap = None,
        openness_map: OpennessMap = None,
        conformtrad_map: ConformTradMap = None,
        sdo_map: SDOMap = None,
        edo_map: EDOMap = None,
        rwa_map: RWAMap = None):
        """
        Initialize.
        Args:
            year (int):
                The current year in the simulation.
            place (str):
                The name of the nation.
            gender_map (GenderMap):
                A GenderMap instance for gender attribute lookups.
            opinions (Dict[OpinionTopicID, Opinion]):
                A dictionary of opinions, where the key is an OpinionTopicID and the value is an Opinion object.
                This allows the environment to have an overview of opinions of Persons and OpinionatedGroups.
            region_map (UKRegionMap):
                A UKRegionMap instance for region attribute lookups.
            education_map (SurveyEducationMap):
                A SurveyEducationMap instance for education attribute lookups.
            ethnicity_map (SurveyEthnicityMap):
                A SurveyEthnicityMap instance for ethnicity attribute lookups.
            income_map (SurveyIncomeMap):
                A SurveyIncomeMap instance for income attribute lookups.
            politics_map (SurveyPoliticsMap):
                A SurveyPoliticsMap instance for politics attribute lookups.
            family_map (SurveyFamilyMap):
                A SurveyFamilyMap instance for family attribute lookups.
            ukge2019_vote_map (UKGE2019VoteMap):
                A UKGE2019VoteMap instance for UK General Election 2019 vote attribute lookups.
            brexit_vote_map (BrexitVoteMap):
                A BrexitVoteMap instance for Brexit referendum vote attribute lookups.
            selftransc_map (SelftranscMap):
                A SelftranscMap instance for self-transcendence value attribute lookups.
            selfenh_map (SelfenhMap):
                A SelfenhMap instance for self-enhancement value attribute lookups.
            openness_map (OpennessMap):
                An OpennessMap instance for openness attribute lookups.
            conformtrad_map (ConformTradMap):
                A ConformTradMap instance for conformity-tradition attribute lookups.
            sdo_map (SDOMap):
                An SDOMap instance for social dominance orientation attribute lookups.
            edo_map (EDOMap):
                An EDOMap instance for environmental dominance orientation attribute lookups.
            rwa_map (RWAMap):
                An RWAMap instance for right-wing authoritarianism attribute lookups.
        """
        super().__init__(year=year, place=place, gender_map=gender_map, opinions=opinions,
            region_map=region_map, education_map=education_map, ethnicity_map=ethnicity_map,
            income_map=income_map)
        self.politics_map = politics_map
        self.family_map = family_map
        self.ukge2019_vote_map = ukge2019_vote_map
        self.brexit_vote_map = brexit_vote_map
        self.selftransc_map = selftransc_map
        self.selfenh_map = selfenh_map
        self.openness_map = openness_map
        self.conformtrad_map = conformtrad_map
        self.sdo_map = sdo_map
        self.edo_map = edo_map
        self.rwa_map = rwa_map

    def run_baseline(self, api_key=None, model="gpt-4o-mini", provider="openai", max_agents=5):
       
        baseline_rows = []
       
        agents = list(self.agents_active.values())[:max_agents]
        logging.info(f"Running baseline for {len(agents)} agents using model '{model}' and provider '{provider}'. If you want more agents then change max_agents in environment.run_baseline()")

        for agent in agents:
            agent_result = agent.run_baseline(api_key=api_key, model=model, provider=provider)
            for policy_id, (letter, numeric) in agent_result.items():
                real_response = agent.get_real_survey_response(policy_id=policy_id)
                logging.info(f"Agent {agent.id} - Policy {policy_id}: LLM response = {letter} ({numeric}), Real survey response = {real_response}")
                baseline_rows.append({
                    "agent_id": agent.id,
                    "policy_id": str(policy_id),
                    "llm_letter": letter,
                    "llm_numeric": numeric,
                    "real_response": real_response,
                    "match": (numeric == real_response)
                })
        df = pd.DataFrame(baseline_rows)
        # log overall accuracy
        overall_accuracy = df["match"].mean()
        print(f"Overall baseline accuracy: {overall_accuracy:.1%}")

        # log accuracy per policy
        policy_accuracy = df.groupby("policy_id")["match"].mean()
        for policy_id, accuracy in policy_accuracy.items():
            print(f"Policy {policy_id} - Accuracy: {accuracy:.1%}")

        return df
