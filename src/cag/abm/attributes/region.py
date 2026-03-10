"""
Region module for Climate-Action-GABM.
"""
# Metadata
__author__ = ["Andy Turner <agdturner@gmail.com>"]
__version__ = "0.1.0"
__copyright__ = "Copyright (c) 2026 Climate-Action-GABM contributors, University of Leeds"

# Standard library imports
import logging
# Local imports
from gabm.abm.attributes.region import RegionID, Region
from gabm.abm.attributes.attribute import GABMAttributeMap

RegionID.UNKNOWN = RegionID(0)
RegionID.NORTH_EAST = RegionID(1)
RegionID.NORTH_WEST = RegionID(2)
RegionID.YORKSHIRE_AND_THE_HUMBER = RegionID(3)
RegionID.EAST_MIDLANDS = RegionID(4)
RegionID.WEST_MIDLANDS = RegionID(5)
RegionID.EAST_OF_ENGLAND = RegionID(6)
RegionID.LONDON = RegionID(7)
RegionID.SOUTH_EAST = RegionID(8)
RegionID.SOUTH_WEST = RegionID(9)
RegionID.WALES = RegionID(10)
RegionID.SCOTLAND = RegionID(11)
RegionID.NORTHERN_IRELAND = RegionID(12)
RegionID.NON_UK = RegionID(13)

class UKRegionMap(GABMAttributeMap):
    """
    A mapping of RegionIds to Region.

    By default, the map is initialized as follows::

        items: Dict[RegionID, Region] = {
            RegionID.UNKNOWN: Region(RegionID.UNKNOWN, "unknown"),
            RegionID.NORTH_EAST: Region(RegionID.NORTH_EAST, "North East"),
            RegionID.NORTH_WEST: Region(RegionID.NORTH_WEST, "North West"),
            RegionID.YORKSHIRE_AND_THE_HUMBER: Region(RegionID.YORKSHIRE_AND_THE_HUMBER, "Yorkshire and the Humber"),
            RegionID.EAST_MIDLANDS: Region(RegionID.EAST_MIDLANDS, "East Midlands"),
            RegionID.WEST_MIDLANDS: Region(RegionID.WEST_MIDLANDS, "West Midlands"),
            RegionID.EAST_OF_ENGLAND: Region(RegionID.EAST_OF_ENGLAND, "East of England"),
            RegionID.LONDON: Region(RegionID.LONDON, "London"),
            RegionID.SOUTH_EAST: Region(RegionID.SOUTH_EAST, "South East"),
            RegionID.SOUTH_WEST: Region(RegionID.SOUTH_WEST, "South West"),
            RegionID.WALES: Region(RegionID.WALES, "Wales"),
            RegionID.SCOTLAND: Region(RegionID.SCOTLAND, "Scotland"),
            RegionID.NORTHERN_IRELAND: Region(RegionID.NORTHERN_IRELAND, "Northern Ireland"),
            RegionID.NON_UK: Region(RegionID.NON_UK, "Non UK")
        }
        super().__init__(items)
    """
    def __init__(self):
        """
        Initialize.
        """
        items: Dict[RegionID, Region] = {
            RegionID.UNKNOWN: Region(RegionID.UNKNOWN, "unknown"),
            RegionID.NORTH_EAST: Region(RegionID.NORTH_EAST, "North East"),
            RegionID.NORTH_WEST: Region(RegionID.NORTH_WEST, "North West"),
            RegionID.YORKSHIRE_AND_THE_HUMBER: Region(RegionID.YORKSHIRE_AND_THE_HUMBER, "Yorkshire and the Humber"),
            RegionID.EAST_MIDLANDS: Region(RegionID.EAST_MIDLANDS, "East Midlands"),
            RegionID.WEST_MIDLANDS: Region(RegionID.WEST_MIDLANDS, "West Midlands"),
            RegionID.EAST_OF_ENGLAND: Region(RegionID.EAST_OF_ENGLAND, "East of England"),
            RegionID.LONDON: Region(RegionID.LONDON, "London"),
            RegionID.SOUTH_EAST: Region(RegionID.SOUTH_EAST, "South East"),
            RegionID.SOUTH_WEST: Region(RegionID.SOUTH_WEST, "South West"),
            RegionID.WALES: Region(RegionID.WALES, "Wales"),
            RegionID.SCOTLAND: Region(RegionID.SCOTLAND, "Scotland"),
            RegionID.NORTHERN_IRELAND: Region(RegionID.NORTHERN_IRELAND, "Northern Ireland"),
            RegionID.NON_UK: Region(RegionID.NON_UK, "Non UK")
        }
        super().__init__(items)