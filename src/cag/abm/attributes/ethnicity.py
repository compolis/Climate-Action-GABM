"""
Ethnicity module for Climate-Action-GABM.
"""
# Metadata
__author__ = ["Andy Turner <agdturner@gmail.com>"]
__version__ = "0.7.0"
__copyright__ = "Copyright (c) 2026 Climate-Action-GABM contributors, University of Leeds"

# Standard library imports
import logging
# Local imports
from gabm.abm.attributes.ethnicity import EthnicityID, Ethnicity
from gabm.abm.attribute import GABMAttributeMap

EthnicityID.UNKNOWN = EthnicityID(0)
EthnicityID.WHITE = EthnicityID(1)
EthnicityID.ASIAN = EthnicityID(2)
EthnicityID.BLACK = EthnicityID(3)
EthnicityID.MIXED = EthnicityID(4)
EthnicityID.OTHER = EthnicityID(5)

class SurveyEthnicityMap(GABMAttributeMap):
    """
    A mapping of EthnicityIds to Ethnicity.

    By default, the map is initialized as follows::

        items: Dict[EthnicityID, Ethnicity] = {
            EthnicityID.UNKNOWN: Ethnicity(EthnicityID.UNKNOWN, "unknown"),
            EthnicityID.WHITE: Ethnicity(EthnicityID.WHITE, "white"),
            EthnicityID.ASIAN: Ethnicity(EthnicityID.ASIAN, "asian"),
            EthnicityID.BLACK: Ethnicity(EthnicityID.BLACK, "black"),
            EthnicityID.MIXED: Ethnicity(EthnicityID.MIXED, "mixed"),
            EthnicityID.OTHER: Ethnicity(EthnicityID.OTHER, "other")
        }
        super().__init__(items)
    """
    def __init__(self):
        """
        Initialize the Ethnicities object.
        """
        items: Dict[EthnicityID, Ethnicity] = {
            EthnicityID.UNKNOWN: Ethnicity(EthnicityID.UNKNOWN, "unknown"),
            EthnicityID.WHITE: Ethnicity(EthnicityID.WHITE, "white"),
            EthnicityID.ASIAN: Ethnicity(EthnicityID.ASIAN, "asian"),
            EthnicityID.BLACK: Ethnicity(EthnicityID.BLACK, "black"),
            EthnicityID.MIXED: Ethnicity(EthnicityID.MIXED, "mixed"),
            EthnicityID.OTHER: Ethnicity(EthnicityID.OTHER, "other")
        }
        super().__init__(items)