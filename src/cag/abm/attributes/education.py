"""
Education module for Climate-Action-GABM.
"""
# Metadata
__author__ = ["Andy Turner <agdturner@gmail.com>"]
__version__ = "0.1.0"
__copyright__ = "Copyright (c) 2026 Climate-Action-GABM contributors, University of Leeds"

# Standard library imports
import logging
# Local imports
from gabm.abm.attributes.education import EducationID, Education
from gabm.abm.attributes.attribute import GABMAttributeMap

class UKEducationMap(GABMAttributeMap):
    """
    A mapping of EducationIds to Education.

    By default, the map is initialized as follows::

        e0 = EducationID(0)
        e1 = EducationID(1)
        e2 = EducationID(2)
        e3 = EducationID(3)
        e4 = EducationID(4)
        e5 = EducationID(5)
        e6 = EducationID(6)
        e7 = EducationID(7)
        e8 = EducationID(8)
        e9 = EducationID(9)
        e10 = EducationID(10)
        e11 = EducationID(11)
        e12 = EducationID(12)
        e13 = EducationID(13)
        e14 = EducationID(14)
        e15 = EducationID(15)
        e16 = EducationID(16)
        e17 = EducationID(17)
        e18 = EducationID(18)
        items: Dict[EducationID, Education] = {
            e0: Education(e0, "unknown"),
            e1: Education(e1, "no formal qualifications"),
            e2: Education(e2, "youth training certificate/skillseekers"),
            e3: Education(e3, "recognised trade apprenticeship completed"),
            e4: Education(e4, "clerical and commercial"),
            e5: Education(e5, "city & guilds certificate")
            e6: Education(e6, "city & guilds certificate - advanced")
            e7: Education(e7, "ONC"),
            e8: Education(e8, "CSE grades 2-5"),
            e9: Education(e9, "CSE grade 1, GCE O level, GCSE, School Certificate"),
            e10: Education(e10, "Scottish Ordinary/ Lower Certificate"),
            e11: Education(e11, "GCE A level or Higher Certificate"),
            e12: Education(e12, "Scottish Higher Certificate"),
            e13: Education(e13, "Nursing qualification (e.g. SEN, SRN, SCM, RGN)"),
            e14: Education(e14, "Teaching qualification (not degree)"),
            e15: Education(e15, "University diploma"),
            e16: Education(e16, "University or CNAA first degree (e.g. BA, B.Sc, B.Ed)"),
            e17: Education(e17, "University or CNAA higher degree (e.g. M.Sc, Ph.D)"),
            e18: Education(e18, "Other technical, professional or higher qualification")
        }
        super().__init__(items)
    """
    def __init__(self):
        """
        Initialize the UKEducationMap object.
        """
        e0 = EducationID(0)
        e1 = EducationID(1)
        e2 = EducationID(2)
        e3 = EducationID(3)
        e4 = EducationID(4)
        e5 = EducationID(5)
        e6 = EducationID(6)
        e7 = EducationID(7)
        e8 = EducationID(8)
        e9 = EducationID(9)
        e10 = EducationID(10)
        e11 = EducationID(11)
        e12 = EducationID(12)
        e13 = EducationID(13)
        e14 = EducationID(14)
        e15 = EducationID(15)
        e16 = EducationID(16)
        e17 = EducationID(17)
        e18 = EducationID(18)
        items: Dict[EducationID, Education] = {
            e0: Education(e0, "unknown"),
            e1: Education(e1, "no formal qualifications"),
            e2: Education(e2, "youth training certificate/skillseekers"),
            e3: Education(e3, "recognised trade apprenticeship completed"),
            e4: Education(e4, "clerical and commercial"),
            e5: Education(e5, "city & guilds certificate")
            e6: Education(e6, "city & guilds certificate - advanced")
            e7: Education(e7, "ONC"),
            e8: Education(e8, "CSE grades 2-5"),
            e9: Education(e9, "CSE grade 1, GCE O level, GCSE, School Certificate"),
            e10: Education(e10, "Scottish Ordinary/ Lower Certificate"),
            e11: Education(e11, "GCE A level or Higher Certificate"),
            e12: Education(e12, "Scottish Higher Certificate"),
            e13: Education(e13, "Nursing qualification (e.g. SEN, SRN, SCM, RGN)"),
            e14: Education(e14, "Teaching qualification (not degree)"),
            e15: Education(e15, "University diploma"),
            e16: Education(e16, "University or CNAA first degree (e.g. BA, B.Sc, B.Ed)"),
            e17: Education(e17, "University or CNAA higher degree (e.g. M.Sc, Ph.D)"),
            e18: Education(e18, "Other technical, professional or higher qualification")
        }
        super().__init__(items)