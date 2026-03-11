# NOTE: This import must be the very first non-empty line in the file (even before docstrings)
# due to Python syntax rules for __future__ imports.
from __future__ import annotations
"""
Agent module for Climate-Action-GABM.
"""
# Metadata
__author__ = ["Andy Turner <agdturner@gmail.com>"]
__version__ = "0.1.0"
__copyright__ = "Copyright (c) 2026 Climate-Action-GABM contributors, University of Leeds"

# Standard library imports
from typing import TYPE_CHECKING
import logging
from datetime import date
# GABM imports
from gabm.abm.agent import Citizen
from gabm.abm.attributes.gender import GenderID, Gender, GenderMap
# TYPE_CHECKING is used to avoid circular imports.
if TYPE_CHECKING:
    from cag.abm.environment import SurveyedNation
# Local imports
from cag.abm.attributes.education import SurveyEducationMap
from cag.abm.attributes.ethnicity import SurveyEthnicityMap
from cag.abm.attributes.income import SurveyIncomeMap
from cag.abm.attributes.politics import SurveyPoliticsMap
from cag.abm.attributes.region import UKRegionMap

class SurveyedCitizen(Citizen):
    """
    A Surveyed Citizen agent class for Climate-Action-GABM, inheriting from the GABM Citizen class.
        
    .. note::
        Inherits all attributes from :class:`Person`.
    
    Attributes:
        region_id (RegionID):
            The agent's region, represented as a RegionID.
        education_id (EducationID):
            The agent's education level, represented as an EducationID.
        ethnicity_id (EthnicityID):
            The agent's ethnicity, represented as an EthnicityID.
        income_id (IncomeID):
            The agent's income level, represented as an IncomeID.
        politics_id (PoliticsID):
            The agent's political views, represented as a PoliticsID.
        family_id (FamilyID):
            The agent's family status, represented as a FamilyID.
    """
    def __init__(
        self,
        agent_id: int,
        environment: SurveyedNation,
        year_of_birth: int,
        gender_id: GenderID,
        region_id: RegionID,
        education_id: EducationID,
        ethnicity_id: EthnicityID,
        income_id: IncomeID,
        politics_id: PoliticsID,
        family_id: FamilyID,
        ukge2019_vote_id: UKGE2019VoteID = None,
        brexit_vote_id: BrexitVoteID = None
    ):
        """
        Initializes a SurveyedCitizen agent with the given attributes.

        Args:
            agent_id (int):
                Unique identifier for the agent.
            environment (SurveyedNation):
                The environment in which the agent exists.
            year_of_birth (int):
                The year the agent was born.
            gender_id (GenderID):
                The agent's gender, represented as a GenderID.
            region_id (RegionID):
                The agent's region, represented as a RegionID.
            education_id (EducationID):
                The agent's education level, represented as an EducationID.
            ethnicity_id (EthnicityID):
                The agent's ethnicity, represented as an EthnicityID.
            income_id (IncomeID):
                The agent's income level, represented as an IncomeID.
            politics_id (PoliticsID):
                The agent's political views, represented as a PoliticsID.
            family_id (FamilyID):
                The agent's family status, represented as a FamilyID.
            ukge2019_vote_id (UKGE2019VoteID):
                The agent's vote in the 2019 UK General Election, represented as a UKGE2019VoteID.
            brexit_vote_id (BrexitVoteID):
                The agent's vote in the 2016 UK Brexit Referendum, represented as a BrexitVoteID.

        """
        super().__init__(agent_id, environment, year_of_birth, gender_id)
        self.region_id = region_id
        self.education_id = education_id
        self.ethnicity_id = ethnicity_id
        self.income_id = income_id
        self.politics_id = politics_id
        self.family_id = family_id
        self.ukge2019_vote_id = ukge2019_vote_id
        self.brexit_vote_id = brexit_vote_id

    def __str__(self):
        """
        Returns a string representation of the SurveyedCitizen agent.
        """
        r = super().__str__()
        sn = self.get_surveyed_nation()
        r += f", region={sn.region_map.get(self.region_id).description}"
        r += f", education={sn.education_map.get(self.education_id).description}"
        r += f", ethnicity={sn.ethnicity_map.get(self.ethnicity_id).description}"
        r += f", income={sn.income_map.get(self.income_id).description}"
        r += f", politics={sn.politics_map.get(self.politics_id).description}"
        r += f", family={sn.family_map.get(self.family_id).description}"
        r += f", UKGE2019 vote={sn.ukge2019_map.get(self.ukge2019_vote_id).description}"
        r += f", Brexit vote={sn.brexit_map.get(self.brexit_vote_id).description}"
        return r

    def get_surveyed_nation(self) -> SurveyedNation:
        """
        Returns the SurveyedNation environment that the agent is in.
        """
        return self.environment

    def get_persona(self) -> str:
        """
        Returns a persona based on attributes.

        Returns:
            A string representing the persona.
        """
        sn = self.get_surveyed_nation()
        age = self.get_age()
        gender = sn.gender_map.get(self.gender_id).description
        region = sn.region_map.get(self.region_id).description
        ethnicity = sn.ethnicity_map.get(self.ethnicity_id).description
        education = sn.education_map.get(self.education_id).description
        income = sn.income_map.get(self.income_id).description
        politics = sn.politics_map.get(self.politics_id).description
        family = sn.family_map.get(self.family_id).description
        ukge2019_vote = sn.ukge2019_map.get(self.ukge2019_vote_id).description
        brexit_vote = sn.brexit_map.get(self.brexit_vote_id).description

        return (f"Demographically, I am a {age}-year-old {gender} living in the {region}, United Kingdom. "
            f"My ethnic background is {ethnicity}, and I hold a {education}. "
            f"Financially, my gross household income falls into the {income} bracket. "
            f"Regarding my family status, I {family}. "
            f"Politically, I position myself on the {politics} of the spectrum. "
            f"In the 2019 General Election, I cast my vote for the {ukge2019_vote}. "
            f"Looking back at the EU Referendum, {brexit_vote}.")