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
    from gabm.abm.environment import Nation
    from gabm.abm.group import Group, OpinionatedGroup
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
    """
    def __init__(
        self,
        agent_id: int,
        environment: Nation,
        year_of_birth: int,
        gender_id: GenderID,
        region_id: RegionID,
        education_id: EducationID,
        ethnicity_id: EthnicityID,
        income_id: IncomeID,
        politics_id: PoliticsID
    ):
        """
        Initializes a SurveyedCitizen agent with the given attributes.

        Args:
            agent_id (int):
                Unique identifier for the agent.
            environment (Nation):
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
        """
        super().__init__(agent_id, environment, year_of_birth, gender_id)
        self.region_id = region_id
        self.education_id = education_id
        self.ethnicity_id = ethnicity_id
        self.income_id = income_id
        self.politics_id = politics_id

    def __str__(self):
        """
        Returns a string representation of the SurveyedCitizen agent.
        """
        str_rep = super().__str__()
        region_str = f", region={environment.region_id}"
        return str_rep + f", region_id={self.region_id}, education_id={self.education_id}, " \
            f"ethnicity_id={self.ethnicity_id}, income_id={self.income_id}, politics_id={self.politics_id}"