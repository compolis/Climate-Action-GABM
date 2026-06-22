"""
Income module for Climate-Action-GABM.
"""
# Metadata
__author__ = ["Andy Turner <agdturner@gmail.com>"]
__version__ = "0.7.0"
__copyright__ = "Copyright (c) 2026 Climate-Action-GABM contributors, University of Leeds"

# Standard library imports
import logging
# Local imports
from gabm.abm.attributes.income import IncomeID, Income
from gabm.abm.attribute import GABMAttributeMap

IncomeID.UNKNOWN = IncomeID(0)
IncomeID.UNDER_5000 = IncomeID(1)
IncomeID.BETWEEN_5000_AND_9999 = IncomeID(2)
IncomeID.BETWEEN_10000_AND_14999 = IncomeID(3)
IncomeID.BETWEEN_15000_AND_19999 = IncomeID(4)
IncomeID.BETWEEN_20000_AND_24999 = IncomeID(5)
IncomeID.BETWEEN_25000_AND_29999 = IncomeID(6)
IncomeID.BETWEEN_30000_AND_34999 = IncomeID(7)
IncomeID.BETWEEN_35000_AND_39999 = IncomeID(8)
IncomeID.BETWEEN_40000_AND_44999 = IncomeID(9)
IncomeID.BETWEEN_45000_AND_49999 = IncomeID(10)
IncomeID.BETWEEN_50000_AND_59999 = IncomeID(11)
IncomeID.BETWEEN_60000_AND_69999 = IncomeID(12)
IncomeID.BETWEEN_70000_AND_99999 = IncomeID(13)
IncomeID.BETWEEN_100000_AND_149999 = IncomeID(14)
IncomeID.OVER_150000 = IncomeID(15)

class SurveyIncomeMap(GABMAttributeMap):
    """
    A mapping of IncomeIds to Income.

    By default, the map is initialized as follows::

        items: Dict[IncomeID, Income] = {
            IncomeID.UNKNOWN: Income(IncomeID.UNKNOWN, "unknown"),
            IncomeID.UNDER_5000: Income(IncomeID.UNDER_5000, "under £5,000 per year"),
            IncomeID.BETWEEN_5000_AND_9999: Income(IncomeID.BETWEEN_5000_AND_9999, "£5,000 - £9,999 per year"),
            IncomeID.BETWEEN_10000_AND_14999: Income(IncomeID.BETWEEN_10000_AND_14999, "£10,000 - £14,999 per year"),
            IncomeID.BETWEEN_15000_AND_19999: Income(IncomeID.BETWEEN_15000_AND_19999, "£15,000 - £19,999 per year"),
            IncomeID.BETWEEN_20000_AND_24999: Income(IncomeID.BETWEEN_20000_AND_24999, "£20,000 - £24,999 per year"),
            IncomeID.BETWEEN_25000_AND_29999: Income(IncomeID.BETWEEN_25000_AND_29999, "£25,000 - £29,999 per year"),
            IncomeID.BETWEEN_30000_AND_34999: Income(IncomeID.BETWEEN_30000_AND_34999, "£30,000 - £34,999 per year"),
            IncomeID.BETWEEN_35000_AND_39999: Income(IncomeID.BETWEEN_35000_AND_39999, "£35,000 - £39,999 per year"),
            IncomeID.BETWEEN_40000_AND_44999: Income(IncomeID.BETWEEN_40000_AND_44999, "£40,000 - £44,999 per year"),
            IncomeID.BETWEEN_45000_AND_49999: Income(IncomeID.BETWEEN_45000_AND_49999, "£45,000 - £49,999 per year"),
            IncomeID.BETWEEN_50000_AND_59999: Income(IncomeID.BETWEEN_50000_AND_59999, "£50,000 - £59,999 per year"),
            IncomeID.BETWEEN_60000_AND_69999: Income(IncomeID.BETWEEN_60000_AND_69999, "£60,000 - £69,999 per year"),
            IncomeID.BETWEEN_70000_AND_99999: Income(IncomeID.BETWEEN_70000_AND_99999, "£70,000 - £99,999 per year"),
            IncomeID.BETWEEN_100000_AND_149999: Income(IncomeID.BETWEEN_100000_AND_149999, "£100,000 - £149,999 per year"),
            IncomeID.OVER_150000: Income(IncomeID.OVER_150000, "£150,000 and over")
        }
        super().__init__(items)
    """
    def __init__(self):
        """
        Initialize.
        """
        items: Dict[IncomeID, Income] = {
            IncomeID.UNKNOWN: Income(IncomeID.UNKNOWN, "unknown"),
            IncomeID.UNDER_5000: Income(IncomeID.UNDER_5000, "under £5,000 per year"),
            IncomeID.BETWEEN_5000_AND_9999: Income(IncomeID.BETWEEN_5000_AND_9999, "£5,000 - £9,999 per year"),
            IncomeID.BETWEEN_10000_AND_14999: Income(IncomeID.BETWEEN_10000_AND_14999, "£10,000 - £14,999 per year"),
            IncomeID.BETWEEN_15000_AND_19999: Income(IncomeID.BETWEEN_15000_AND_19999, "£15,000 - £19,999 per year"),
            IncomeID.BETWEEN_20000_AND_24999: Income(IncomeID.BETWEEN_20000_AND_24999, "£20,000 - £24,999 per year"),
            IncomeID.BETWEEN_25000_AND_29999: Income(IncomeID.BETWEEN_25000_AND_29999, "£25,000 - £29,999 per year"),
            IncomeID.BETWEEN_30000_AND_34999: Income(IncomeID.BETWEEN_30000_AND_34999, "£30,000 - £34,999 per year"),
            IncomeID.BETWEEN_35000_AND_39999: Income(IncomeID.BETWEEN_35000_AND_39999, "£35,000 - £39,999 per year"),
            IncomeID.BETWEEN_40000_AND_44999: Income(IncomeID.BETWEEN_40000_AND_44999, "£40,000 - £44,999 per year"),
            IncomeID.BETWEEN_45000_AND_49999: Income(IncomeID.BETWEEN_45000_AND_49999, "£45,000 - £49,999 per year"),
            IncomeID.BETWEEN_50000_AND_59999: Income(IncomeID.BETWEEN_50000_AND_59999, "£50,000 - £59,999 per year"),
            IncomeID.BETWEEN_60000_AND_69999: Income(IncomeID.BETWEEN_60000_AND_69999, "£60,000 - £69,999 per year"),
            IncomeID.BETWEEN_70000_AND_99999: Income(IncomeID.BETWEEN_70000_AND_99999, "£70,000 - £99,999 per year"),
            IncomeID.BETWEEN_100000_AND_149999: Income(IncomeID.BETWEEN_100000_AND_149999, "£100,000 - £149,999 per year"),
            IncomeID.OVER_150000: Income(IncomeID.OVER_150000, "£150,000 and over")
        }
        super().__init__(items)