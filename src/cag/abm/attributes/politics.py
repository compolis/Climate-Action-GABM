"""
Politics module for Climate-Action-GABM.
"""
# Metadata
__author__ = ["Andy Turner <agdturner@gmail.com>"]
__version__ = "0.9.0"
__copyright__ = "Copyright (c) 2026 Climate-Action-GABM contributors, University of Leeds"

# Standard library imports
import logging
# Local imports
from gabm.core.id import GABMID
from gabm.abm.attribute import GABMAttribute, GABMAttributeMap
from gabm.abm.attributes.politics import PoliticsID, Politics

PoliticsID.UNKNOWN = PoliticsID(0)
PoliticsID.VERY_LEFT_WING = PoliticsID(1)
PoliticsID.FAIRLY_LEFT_WING = PoliticsID(2)
PoliticsID.SLIGHTLY_LEFT_OF_CENTRE = PoliticsID(3)
PoliticsID.CENTRE = PoliticsID(4)
PoliticsID.SLIGHTLY_RIGHT_OF_CENTRE = PoliticsID(5)
PoliticsID.FAIRLY_RIGHT_WING = PoliticsID(6)
PoliticsID.VERY_RIGHT_WING = PoliticsID(7)
PoliticsID.DONT_KNOW = PoliticsID(8)

class SurveyPoliticsMap(GABMAttributeMap):
    """
    A mapping of PoliticsIDs to Politics.

    By default, the map is initialized as follows::

        items: Dict[PoliticsID, Politics] = {
            PoliticsID.UNKNOWN: Politics(PoliticsID.UNKNOWN, "unknown"),
            PoliticsID.VERY_LEFT_WING: Politics(PoliticsID.VERY_LEFT_WING, "very left-wing"),
            PoliticsID.FAIRLY_LEFT_WING: Politics(PoliticsID.FAIRLY_LEFT_WING, "fairly left-wing"),
            PoliticsID.SLIGHTLY_LEFT_OF_CENTRE: Politics(PoliticsID.SLIGHTLY_LEFT_OF_CENTRE, "slightly left-of-centre"),
            PoliticsID.CENTRE: Politics(PoliticsID.CENTRE, "centre"),
            PoliticsID.SLIGHTLY_RIGHT_OF_CENTRE: Politics(PoliticsID.SLIGHTLY_RIGHT_OF_CENTRE, "slightly right-of-centre"),
            PoliticsID.FAIRLY_RIGHT_WING: Politics(PoliticsID.FAIRLY_RIGHT_WING, "fairly right-wing"),
            PoliticsID.VERY_RIGHT_WING: Politics(PoliticsID.VERY_RIGHT_WING, "very right-wing"),
            PoliticsID.DONT_KNOW: Politics(PoliticsID.DONT_KNOW, "don't know")
        }
        super().__init__(items)
    """
    def __init__(self):
        """
        Initialize the UKPoliticalSpectrumMap object.
        """
        items: Dict[PoliticsID, Politics] = {
            PoliticsID.UNKNOWN: Politics(PoliticsID.UNKNOWN, "unknown"),
            PoliticsID.VERY_LEFT_WING: Politics(PoliticsID.VERY_LEFT_WING, "very left-wing"),
            PoliticsID.FAIRLY_LEFT_WING: Politics(PoliticsID.FAIRLY_LEFT_WING, "fairly left-wing"),
            PoliticsID.SLIGHTLY_LEFT_OF_CENTRE: Politics(PoliticsID.SLIGHTLY_LEFT_OF_CENTRE, "slightly left-of-centre"),
            PoliticsID.CENTRE: Politics(PoliticsID.CENTRE, "centre"),
            PoliticsID.SLIGHTLY_RIGHT_OF_CENTRE: Politics(PoliticsID.SLIGHTLY_RIGHT_OF_CENTRE, "slightly right-of-centre"),
            PoliticsID.FAIRLY_RIGHT_WING: Politics(PoliticsID.FAIRLY_RIGHT_WING, "fairly right-wing"),
            PoliticsID.VERY_RIGHT_WING: Politics(PoliticsID.VERY_RIGHT_WING, "very right-wing"),
            PoliticsID.DONT_KNOW: Politics(PoliticsID.DONT_KNOW, "don't know")
        }
        super().__init__(items)