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