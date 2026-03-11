"""
Environment module for Climate-Action-GABM.
"""
# Metadata
__author__ = ["Andy Turner <agdturner@gmail.com>"]
__version__ = "0.1.0"
__copyright__ = "Copyright (c) 2026 GABM contributors, University of Leeds"

# Standard library imports
from typing import Dict
# GABM imports
from gabm.abm.environment import Nation


class SurveyedNation(Nation):
    """
    A Surveyed Nation environment class for Climate-Action-GABM, inheriting from the GABM Nation class.

    .. note::
            Inherits all attributes from :class:`Nation`.

    Attributes:

    """
    def __init__(self, year: int = 2026, place: str = "UK", 
        gender_map: GenderMap = None, opinions: Dict[OpinionTopicID, Opinion] = None,
        region_map: UKRegionMap = None, education_map: SurveyEducationMap = None,
        ethnicity_map: SurveyEthnicityMap = None, income_map: SurveyIncomeMap = None,
        politics_map: SurveyPoliticsMap = None):
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
        
        """
        super().__init__(year, place, gender_map, opinions)