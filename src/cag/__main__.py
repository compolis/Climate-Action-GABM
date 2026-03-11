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
from gabm.abm.attributes.family import FamilyID
from gabm.abm.democracy.elections.uk.general_election import UKGEVoteID
from gabm.abm.democracy.elections.uk.referendum import UKReferendumVoteID
# Local imports
from cag.abm.environment import SurveyedNation
from cag.abm.agent import SurveyedCitizen
from cag.abm.attributes.ethnicity import SurveyEthnicityMap
from cag.abm.attributes.income import SurveyIncomeMap
from cag.abm.attributes.politics import SurveyPoliticsMap
from cag.abm.attributes.education import SurveyEducationMap
from cag.abm.attributes.region import UKRegionMap
from cag.abm.attributes.family import SurveyFamilyMap
from cag.abm.democracy.elections.ukge2019 import UKGE2019VoteMap
from cag.abm.democracy.elections.brexit import BrexitVoteMap

from cag.abm.attributes.opinion import OpinionTopicID, OpinionTopic, OpinionValue

def main():
    logging.info("\n--- Climate-Action-GABM ---\n")

    # Set random seed for reproducibility
    random.seed(42)

    # Create attribute maps
    gender_map = GenderMap()
    uk_region_map = UKRegionMap()
    survey_ethnicity_map = SurveyEthnicityMap()
    survey_income_map = SurveyIncomeMap()
    survey_politics_map = SurveyPoliticsMap()
    survey_education_map = SurveyEducationMap()
    survey_family_map = SurveyFamilyMap()
    ukge2019_vote_map = UKGE2019VoteMap()
    brexit_vote_map = BrexitVoteMap()

    # Create a SurveyedNation environment
    surveyed_nation = SurveyedNation(
        year=2026,
        place="UK",
        gender_map=gender_map,
        region_map=uk_region_map,
        education_map=survey_education_map,
        ethnicity_map=survey_ethnicity_map,
        income_map=survey_income_map,
        politics_map=survey_politics_map,
        family_map=survey_family_map,
        ukge2019_vote_map=ukge2019_vote_map,
        brexit_vote_map=brexit_vote_map
    )

    # Create a SurveyedCitizen agent
    sc0 = SurveyedCitizen(
        agent_id=0,
        environment=surveyed_nation,
        year_of_birth=2008,
        gender_id=GenderID.MALE,
        region_id=RegionID.YORKSHIRE_AND_THE_HUMBER,
        ethnicity_id=EthnicityID.WHITE,
        income_id=IncomeID.BETWEEN_40000_AND_44999,
        education_id=EducationID.NO_FORMAL_QUALIFICATIONS,
        politics_id=PoliticsID.CENTRE,
        family_id=FamilyID.NOT_PARENT,
        ukge2019_vote_id=UKGE2019VoteID.CONSERVATIVE,
        brexit_vote_id=BrexitVoteID.LEAVE
    )
    logging.info(f"Created SurveyedCitizen: {sc0}")
    # Get the SurveyedCitizen persona
    get_persona = sc0.get_persona()
    logging.info(f"Persona: {get_persona}")

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
