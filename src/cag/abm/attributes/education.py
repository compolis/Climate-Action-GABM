"""
Education module for Climate-Action-GABM.
"""
# Metadata
__author__ = ["Andy Turner <agdturner@gmail.com>"]
__version__ = "0.9.0"
__copyright__ = "Copyright (c) 2026 Climate-Action-GABM contributors, University of Leeds"

# Standard library imports
import logging
# Local imports
from gabm.abm.attributes.education import EducationID, Education
from gabm.abm.attribute import GABMAttributeMap

EducationID.UNKNOWN = EducationID(0)
EducationID.NO_FORMAL_QUALIFICATIONS = EducationID(1)
EducationID.YOUTH_TRAINING_CERTIFICATE = EducationID(2)
EducationID.RECOGNISED_TRADE_APPRENTICESHIP = EducationID(3)
EducationID.CLERICAL_AND_COMMERCIAL = EducationID(4)
EducationID.CITY_AND_GUILDS_CERTIFICATE = EducationID(5)
EducationID.CITY_AND_GUILDS_CERTIFICATE_ADVANCED = EducationID(6)
EducationID.ONC = EducationID(7)
EducationID.CSE_GRADES_2_5 = EducationID(8)
EducationID.CSE_GRADE_1_GCE_O_LEVEL_GCSE_SCHOOL_CERTIFICATE = EducationID(9)
EducationID.SCOTTISH_ORDINARY_LOWER_CERTIFICATE = EducationID(10)
EducationID.GCE_A_LEVEL_OR_HIGHER_CERTIFICATE = EducationID(11)
EducationID.SCOTTISH_HIGHER_CERTIFICATE = EducationID(12)
EducationID.NURSING_QUALIFICATION = EducationID(13)
EducationID.TEACHING_QUALIFICATION = EducationID(14)
EducationID.UNIVERSITY_DIPLOMA = EducationID(15)
EducationID.UNIVERSITY_OR_CNAA_FIRST_DEGREE = EducationID(16)
EducationID.UNIVERSITY_OR_CNAA_HIGHER_DEGREE = EducationID(17)
EducationID.OTHER_TECHNICAL_PROFESSIONAL_OR_HIGHER_QUALIFICATION = EducationID(18)

class SurveyEducationMap(GABMAttributeMap):
    """
    A mapping of EducationIds to Education.

    By default, the map is initialized as follows::

        items: Dict[EducationID, Education] = {
            EducationID.UNKNOWN: Education(EducationID.UNKNOWN, "unknown"),
            EducationID.NO_FORMAL_QUALIFICATIONS: Education(EducationID.NO_FORMAL_QUALIFICATIONS, "no formal qualifications"),
            EducationID.YOUTH_TRAINING_CERTIFICATE: Education(EducationID.YOUTH_TRAINING_CERTIFICATE, "youth training certificate/skillseekers"),
            EducationID.RECOGNISED_TRADE_APPRENTICESHIP: Education(EducationID.RECOGNISED_TRADE_APPRENTICESHIP, "recognised trade apprenticeship completed"),
            EducationID.CLERICAL_AND_COMMERCIAL: Education(EducationID.CLERICAL_AND_COMMERCIAL, "clerical and commercial"),
            EducationID.CITY_AND_GUILDS_CERTIFICATE: Education(EducationID.CITY_AND_GUILDS_CERTIFICATE, "city & guilds certificate"),
            EducationID.CITY_AND_GUILDS_CERTIFICATE_ADVANCED: Education(EducationID.CITY_AND_GUILDS_CERTIFICATE_ADVANCED, "city & guilds certificate - advanced"),
            EducationID.ONC: Education(EducationID.ONC, "ONC"),
            EducationID.CSE_GRADES_2_5: Education(EducationID.CSE_GRADES_2_5, "CSE grades 2-5"),
            EducationID.CSE_GRADE_1_GCE_O_LEVEL_GCSE_SCHOOL_CERTIFICATE: Education(EducationID.CSE_GRADE_1_GCE_O_LEVEL_GCSE_SCHOOL_CERTIFICATE, "CSE grade 1, GCE O level, GCSE, School Certificate"),
            EducationID.SCOTTISH_ORDINARY_LOWER_CERTIFICATE: Education(EducationID.SCOTTISH_ORDINARY_LOWER_CERTIFICATE, "Scottish Ordinary/ Lower Certificate"),
            EducationID.GCE_A_LEVEL_OR_HIGHER_CERTIFICATE: Education(EducationID.GCE_A_LEVEL_OR_HIGHER_CERTIFICATE, "GCE A level or Higher Certificate"),
            EducationID.SCOTTISH_HIGHER_CERTIFICATE: Education(EducationID.SCOTTISH_HIGHER_CERTIFICATE, "Scottish Higher Certificate"),
            EducationID.NURSING_QUALIFICATION: Education(EducationID.NURSING_QUALIFICATION, "Nursing qualification (e.g. SEN, SRN, SCM, RGN)"),
            EducationID.TEACHING_QUALIFICATION: Education(EducationID.TEACHING_QUALIFICATION, "Teaching qualification (not degree)"),
            EducationID.UNIVERSITY_DIPLOMA: Education(EducationID.UNIVERSITY_DIPLOMA, "University diploma"),
            EducationID.UNIVERSITY_OR_CNAA_FIRST_DEGREE: Education(EducationID.UNIVERSITY_OR_CNAA_FIRST_DEGREE, "University or CNAA first degree (e.g. BA, B.Sc, B.Ed)"),
            EducationID.UNIVERSITY_OR_CNAA_HIGHER_DEGREE: Education(EducationID.UNIVERSITY_OR_CNAA_HIGHER_DEGREE, "University or CNAA higher degree (e.g. M.Sc, Ph.D)"),
            EducationID.OTHER_TECHNICAL_PROFESSIONAL_OR_HIGHER_QUALIFICATION: Education(EducationID.OTHER_TECHNICAL_PROFESSIONAL_OR_HIGHER_QUALIFICATION, "Other technical, professional or higher qualification")
        }
        super().__init__(items)
    """
    def __init__(self):
        """
        Initialize the UKEducationMap object.
        """
        items: Dict[EducationID, Education] = {
            EducationID.UNKNOWN: Education(EducationID.UNKNOWN, "unknown"),
            EducationID.NO_FORMAL_QUALIFICATIONS: Education(EducationID.NO_FORMAL_QUALIFICATIONS, "no formal qualifications"),
            EducationID.YOUTH_TRAINING_CERTIFICATE: Education(EducationID.YOUTH_TRAINING_CERTIFICATE, "youth training certificate/skillseekers"),
            EducationID.RECOGNISED_TRADE_APPRENTICESHIP: Education(EducationID.RECOGNISED_TRADE_APPRENTICESHIP, "recognised trade apprenticeship completed"),
            EducationID.CLERICAL_AND_COMMERCIAL: Education(EducationID.CLERICAL_AND_COMMERCIAL, "clerical and commercial"),
            EducationID.CITY_AND_GUILDS_CERTIFICATE: Education(EducationID.CITY_AND_GUILDS_CERTIFICATE, "city & guilds certificate"),
            EducationID.CITY_AND_GUILDS_CERTIFICATE_ADVANCED: Education(EducationID.CITY_AND_GUILDS_CERTIFICATE_ADVANCED, "city & guilds certificate - advanced"),
            EducationID.ONC: Education(EducationID.ONC, "ONC"),
            EducationID.CSE_GRADES_2_5: Education(EducationID.CSE_GRADES_2_5, "CSE grades 2-5"),
            EducationID.CSE_GRADE_1_GCE_O_LEVEL_GCSE_SCHOOL_CERTIFICATE: Education(EducationID.CSE_GRADE_1_GCE_O_LEVEL_GCSE_SCHOOL_CERTIFICATE, "CSE grade 1, GCE O level, GCSE, School Certificate"),
            EducationID.SCOTTISH_ORDINARY_LOWER_CERTIFICATE: Education(EducationID.SCOTTISH_ORDINARY_LOWER_CERTIFICATE, "Scottish Ordinary/ Lower Certificate"),
            EducationID.GCE_A_LEVEL_OR_HIGHER_CERTIFICATE: Education(EducationID.GCE_A_LEVEL_OR_HIGHER_CERTIFICATE, "GCE A level or Higher Certificate"),
            EducationID.SCOTTISH_HIGHER_CERTIFICATE: Education(EducationID.SCOTTISH_HIGHER_CERTIFICATE, "Scottish Higher Certificate"),
            EducationID.NURSING_QUALIFICATION: Education(EducationID.NURSING_QUALIFICATION, "Nursing qualification (e.g. SEN, SRN, SCM, RGN)"),
            EducationID.TEACHING_QUALIFICATION: Education(EducationID.TEACHING_QUALIFICATION, "Teaching qualification (not degree)"),
            EducationID.UNIVERSITY_DIPLOMA: Education(EducationID.UNIVERSITY_DIPLOMA, "University diploma"),
            EducationID.UNIVERSITY_OR_CNAA_FIRST_DEGREE: Education(EducationID.UNIVERSITY_OR_CNAA_FIRST_DEGREE, "University or CNAA first degree (e.g. BA, B.Sc, B.Ed)"),
            EducationID.UNIVERSITY_OR_CNAA_HIGHER_DEGREE: Education(EducationID.UNIVERSITY_OR_CNAA_HIGHER_DEGREE, "University or CNAA higher degree (e.g. M.Sc, Ph.D)"),
            EducationID.OTHER_TECHNICAL_PROFESSIONAL_OR_HIGHER_QUALIFICATION: Education(EducationID.OTHER_TECHNICAL_PROFESSIONAL_OR_HIGHER_QUALIFICATION, "Other technical, professional or higher qualification")
        }
        super().__init__(items)