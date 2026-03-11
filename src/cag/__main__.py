#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Entry point for running the Climate-Action-GABM application.
To run: python3 -m gabm
"""
# Metadata
__author__ = ["Andy Turner <agdturner@gmail.com>"]
__version__ = "0.3.0"
__copyright__ = "Copyright (c) 2026 Climate-Action-GABM contributors, University of Leeds"

# Standard library imports
import os
import os
import sys
import logging
from pathlib import Path
import random
# Visualization
import matplotlib.pyplot as plt
# GABM imports
from gabm.abm.environment import Nation
from gabm.abm.attributes.gender import GenderID, Gender, GenderMap
from gabm.abm.attributes.ethnicity import EthnicityID
from gabm.abm.attributes.income import IncomeID
from gabm.abm.attributes.politics import PoliticsID
from gabm.abm.attributes.education import EducationID
from gabm.abm.attributes.region import RegionID

# Local imports
from cag.abm.agent import SurveyedCitizen
from cag.abm.attributes.ethnicity import SurveyEthnicityMap
from cag.abm.attributes.income import SurveyIncomeMap
from cag.abm.attributes.politics import SurveyPoliticsMap
from cag.abm.attributes.education import SurveyEducationMap
from cag.abm.attributes.opinion import OpinionTopicID, OpinionTopic, OpinionValue
from cag.abm.attributes.region import UKRegionMap

def main():
    logging.info("\n--- Climate-Action-GABM ---\n")

    # Set random seed for reproducibility
    random.seed(42)

    # Create environment
    uk = Nation(year=2026)

    # Create attribute maps
    gender_map = GenderMap()
    uk_region_map = UKRegionMap()
    survey_ethnicity_map = SurveyEthnicityMap()
    survey_income_map = SurveyIncomeMap()
    survey_politics_map = SurveyPoliticsMap()
    survey_education_map = SurveyEducationMap()

    # Create a SurveyedCitizen agent
    sc0 = SurveyedCitizen(
        agent_id=0,
        environment=uk,
        year_of_birth=2008,
        gender_id=GenderID.MALE,
        region_id=RegionID.UNKNOWN,
        ethnicity_id=EthnicityID.WHITE,
        income_id=IncomeID.BETWEEN_40000_AND_44999,
        education_id=EducationID.NO_FORMAL_QUALIFICATIONS,
        politics_id=PoliticsID.CENTRE
    )
    logging.info(f"Created SurveyedCitizen: {sc0}")

    
if __name__ == "__main__":
    # Set up logging to file and console
    log_dir = Path("data/logs")
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / "run_main.log"
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[
            logging.FileHandler(log_file, mode="w"),
            logging.StreamHandler(sys.stdout)
        ]
    )
    main()
