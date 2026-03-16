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
        Inherits all attributes from :class:`Citizen`.
    
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
        ukge2019_vote_id (UKGE2019VoteID):
            The agent's vote in the 2019 UK General Election, represented as a UKGE2019VoteID.
        brexit_vote_id (BrexitVoteID):
            The agent's vote in the 2016 UK Brexit Referendum, represented as a BrexitVoteID.
        selftransc_val_id (Selftransc_ValID):
            The agent's self-transcendence value, represented as a Selftransc_ValID.
        selfenh_value_id (Selfenh_ValuesID):
            The agent's self-enhancement value, represented as a Selfenh_ValuesID.
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
        brexit_vote_id: BrexitVoteID = None,
        selftransc_val_id: Selftransc_ValID = None,
        selfenh_value_id: Selfenh_ValuesID = None
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
            selftransc_val_id (Selftransc_ValID):
                The agent's self-transcendence value, represented as a Selftransc_ValID.
            selfenh_value_id (Selfenh_ValuesID):
                The agent's self-enhancement value, represented as a Selfenh_ValuesID.
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
        self.selftransc_val_id = selftransc_val_id
        self.selfenh_value_id = selfenh_value_id

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
        try:
            ukge2019_vote = sn.ukge2019_vote_map.get(self.ukge2019_vote_id)
            ukge2019_vote_str = getattr(ukge2019_vote, 'description', str(ukge2019_vote)) if ukge2019_vote else 'Unknown'
        except TypeError:
            ukge2019_vote_str = 'Unknown'
        try:
            brexit_vote = sn.brexit_vote_map.get(self.brexit_vote_id)
            brexit_vote_str = getattr(brexit_vote, 'description', str(brexit_vote)) if brexit_vote else 'Unknown'
        except TypeError:
            brexit_vote_str = 'Unknown'
        r += f", UKGE2019 vote={ukge2019_vote_str}"
        r += f", Brexit vote={brexit_vote_str}"
        r += f", Self-transcendence value={sn.selftransc_val_map.get(self.selftransc_val_id).description}"
        r += f", Self-enhancement value={sn.selfenh_value_map.get(self.selfenh_value_id).description}"
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
        ukge2019_vote_obj = sn.ukge2019_vote_map.get(self.ukge2019_vote_id)
        ukge2019_vote = getattr(ukge2019_vote_obj, 'description', str(ukge2019_vote_obj)) if ukge2019_vote_obj else 'Unknown'
        brexit_vote_obj = sn.brexit_vote_map.get(self.brexit_vote_id)
        brexit_vote = getattr(brexit_vote_obj, 'description', str(brexit_vote_obj)) if brexit_vote_obj else 'Unknown'
        r: str = f"I am a {age} year old {gender} living in the {region}. "
        if ethnicity != "unknown" and ethnicity != "other":
            r += f"My ethnicity is {ethnicity}. "
        if education != "unknown":
            r += f"I have a {education}. "
        if income != "unknown":
            r += f"My gross household income is {income}. "
        if family != "unknown":
            r += f"I am {family}. "
        if politics != "unknown" and politics != "don't know":
            r += f"I position myself {politics} of the political spectrum. "
        if ukge2019_vote != "unknown" and ukge2019_vote != "another" and ukge2019_vote != "don't know":
            r += f"I voted for the {ukge2019_vote} party candidate in the 2019 General Election. "
        if brexit_vote != "unknown" and brexit_vote != "don't know":
            r += f"I {brexit_vote} in the 2016 EU Referendum."
        return r
 
    def get_narrative(self) -> str:
        """
        Returns a narrative based on attributes.

        Returns:
            A string representing the narrative.
        """
        sn = self.environment
        selftransc = sn.selftransc_map.get(self.selftransc_val_id).description
        selfenh = sn.selfenh_map.get(self.selfenh_value_id).description
        openness = sn.openness_map.get(self.selfenh_value_id).description
        conformtrad = sn.conformtrad_map.get(self.selfenh_value_id).description
        sdo = sn.sdo_map.get(self.selfenh_value_id).description
        edo = sn.edo_map.get(self.selfenh_value_id).description
        rwa = sn.rwa_map.get(self.selfenh_value_id).description
        return f"{selftransc} {selfenh} {openness} {conformtrad} {sdo} {edo} {rwa}"