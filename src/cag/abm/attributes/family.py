"""
Income module for Climate-Action-GABM.
"""
# Metadata
__author__ = ["Andy Turner <agdturner@gmail.com>"]
__version__ = "0.9.0"
__copyright__ = "Copyright (c) 2026 Climate-Action-GABM contributors, University of Leeds"

# Standard library imports
import logging
# Local imports
from gabm.abm.attributes.family import FamilyID, Family
from gabm.abm.attribute import GABMAttributeMap

FamilyID.UNKNOWN = FamilyID(0)
FamilyID.NOT_PARENT = FamilyID(1)
FamilyID.PARENT = FamilyID(2)

class SurveyFamilyMap(GABMAttributeMap):
    """
    A mapping of FamilyIds to Families.

    By default, the map is initialized as follows::

        items: Dict[FamilyID, Family] = {
            FamilyID.UNKNOWN: Family(FamilyID.UNKNOWN, "unknown"),
            FamilyID.NOT_PARENT: Family(FamilyID.NOT_PARENT, "not a parent"),
            FamilyID.PARENT: Family(FamilyID.PARENT, "a parent")
        }
        super().__init__(items)
    """
    def __init__(self):
        """
        Initialize.
        """
        items: Dict[FamilyID, Family] = {
            FamilyID.UNKNOWN: Family(FamilyID.UNKNOWN, "unknown"),
            FamilyID.NOT_PARENT: Family(FamilyID.NOT_PARENT, "not a parent"),
            FamilyID.PARENT: Family(FamilyID.PARENT, "a parent")
        }
        super().__init__(items)