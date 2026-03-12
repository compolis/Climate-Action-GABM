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
from gabm.abm.democracy.election import ElectionID
from gabm.abm.democracy.elections.uk.general_election import UKGEVoteID
from gabm.abm.democracy.elections.uk.referendum import UKReferendumVoteID
# Local imports
from cag.io.survey import load
from cag.abm.environment import SurveyedNation
from cag.abm.agent import SurveyedCitizen
from cag.abm.attributes.ethnicity import SurveyEthnicityMap
from cag.abm.attributes.income import SurveyIncomeMap
from cag.abm.attributes.politics import SurveyPoliticsMap
from cag.abm.attributes.education import SurveyEducationMap
from cag.abm.attributes.region import UKRegionMap
from cag.abm.attributes.family import SurveyFamilyMap
from cag.abm.democracy.elections.ukge2019 import UKGE2019VoteID, UKGE2019, UKGE2019VoteMap
from cag.abm.democracy.elections.brexit import BrexitVoteID, Brexit, BrexitVoteMap

from cag.abm.attributes.opinion import OpinionTopicID, OpinionTopic, OpinionValue

def main():
    logging.info("\n--- Climate-Action-GABM ---\n")

    # Set random seed for reproducibility
    random.seed(42)

    # Create election instances
    UKGE2019_ELECTION_ID = ElectionID(0)
    uk_ge2019 = UKGE2019(UKGE2019_ELECTION_ID)
    BREXIT_REFERENDUM_ID = ElectionID(1)
    brexit = Brexit(BREXIT_REFERENDUM_ID)

    # Create attribute maps
    gender_map = GenderMap()
    uk_region_map = UKRegionMap()
    survey_ethnicity_map = SurveyEthnicityMap()
    survey_income_map = SurveyIncomeMap()
    survey_politics_map = SurveyPoliticsMap()
    survey_education_map = SurveyEducationMap()
    survey_family_map = SurveyFamilyMap()
    ukge2019_vote_map = UKGE2019VoteMap(UKGE2019_ELECTION_ID)
    brexit_vote_map = BrexitVoteMap(BREXIT_REFERENDUM_ID)

    # Create a SurveyedNation environment
    logging.info("Creating SurveyedNation...")
    year: int = 2026
    surveyed_nation = SurveyedNation(
        year=year,
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
    logging.info(f"... created SurveyedNation: {surveyed_nation}")

    # Load survey data
    logging.info("Loading survey data...")
    required_columns = [
        'ID',
        'age', # Used to determine year of birth
        'male_dummy', # Used to determine gender 0 = female, 1 = male
        'tprofile_GOR', # Used to determine region
        "profile_education_level", # Used to determine education level
        'tprofile_gross_household', # Used to determine income level
        'ethnicity_R', # Used to determine ethnicity
        'parent_dummy', # Used to determine family status
        'Vote2019R', # Used to determine UK General Election 2019 vote
        'pastvote_EURef', # Used to determine Brexit referendum vote
        'Political_Left_Right', # Used to determine political views
        'Selftransc_Val',
        'Selfenh_Values',
        'Openness',
        'ConformTrad',
        'SDO',
        'EDO',
        'RWA',
        'page5posttreatment6_1',
        'page5posttreatment6_4',
        'page5posttreatment6_5',
        'page5posttreatment6_7',
        'page5posttreatment6_9',
        'page5posttreatment6_11',
        'ProClimatePolSupp'
    ]
    data: pd.DataFrame | None= load("data/yougov_survey_data/YouGovProcessedData.csv", required_columns=required_columns)
    #logging.info(data.head())
    #logging.info(data.columns)
    #logging.info(data.dtypes)
    logging.info("...loaded survey data")
    
    # Create SurveyedCitizens from the survey data
    logging.info("Creating SurveyedCitizens from survey data...")
    scs = []
    for i in range(len(data)):
        agent_id = data.iloc[i].get('ID', None)
        #logging.info(f"Creating SurveyedCitizen {agent_id} from survey data row {i}...")
        #logging.info(data.iloc[i])
        age: int = int(data.iloc[i].get('age', 0))
        #logging.info(f"age: {age}")
        year_of_birth: int = year - age
        #logging.info(f"year_of_birth: {year_of_birth}")
        male_dummy: int = int(data.iloc[i].get('male_dummy', 0))
        #logging.info(f"male_dummy: {male_dummy}")
        gender_id: GenderID = GenderID.MALE if male_dummy == 1 else GenderID.FEMALE
        #logging.info(f"gender: {gender_map[gender_id].description}")
        tprofile_GOR: int = int(data.iloc[i].get('tprofile_GOR', 0))
        #logging.info(f"tprofile_GOR: {tprofile_GOR}")
        region_id: RegionID = RegionID(tprofile_GOR)
        #logging.info(f"region: {uk_region_map[region_id].description}")
        profile_education_level: int = int(data.iloc[i].get('profile_education_level', 0))
        #logging.info(f"profile_education_level: {profile_education_level}")
        education_id: EducationID = EducationID(profile_education_level)
        #logging.info(f"education: {survey_education_map[education_id].description}")
        tprofile_gross_household: int = int(data.iloc[i].get('tprofile_gross_household', 0))
        #logging.info(f"tprofile_gross_household: {tprofile_gross_household}")
        income_id: IncomeID = IncomeID(tprofile_gross_household)
        #logging.info(f"income: {survey_income_map[income_id].description}")
        ethnicity_R: int = int(data.iloc[i].get('ethnicity_R', 0))
        #logging.info(f"ethnicity_R: {ethnicity_R}")
        ethnicity_id: EthnicityID = EthnicityID(ethnicity_R)
        #logging.info(f"ethnicity: {survey_ethnicity_map[ethnicity_id].description}")
        parent_dummy: int = int(data.iloc[i].get('parent_dummy', 0))
        #logging.info(f"parent_dummy: {parent_dummy}")
        family_id: FamilyID = FamilyID.PARENT if parent_dummy == 1 else FamilyID.NOT_PARENT
        #logging.info(f"family status: {survey_family_map[family_id].description}")
        Vote2019R: int = int(data.iloc[i].get('Vote2019R', 0))
        #logging.info(f"Vote2019R: {Vote2019R}")
        ukge2019_vote_id: UKGE2019VoteID = UKGE2019VoteID(Vote2019R)
        #logging.info(f"UKGE2019 vote: {ukge2019_vote_map[ukge2019_vote_id].description}")
        pastvote_EURef: int = int(data.iloc[i].get('pastvote_EURef', 0))
        #logging.info(f"pastvote_EURef: {pastvote_EURef}")
        brexit_vote_id: BrexitVoteID = BrexitVoteID(pastvote_EURef)
        #logging.info(f"Brexit vote: {brexit_vote_map[brexit_vote_id].description}")       
        Political_Left_Right: int = int(data.iloc[i].get('Political_Left_Right', 0))
        #logging.info(f"Political_Left_Right: {Political_Left_Right}")
        politics_id: PoliticsID = PoliticsID(Political_Left_Right)
        #logging.info(f"politics: {survey_politics_map[politics_id].description}")
        scs.append(SurveyedCitizen(
            agent_id=agent_id,
            environment=surveyed_nation,
            year_of_birth=year_of_birth,
            gender_id=gender_id,
            region_id=region_id,
            ethnicity_id=ethnicity_id,
            income_id=income_id,
            education_id=education_id,
            politics_id=politics_id,
            family_id=family_id,
            ukge2019_vote_id=ukge2019_vote_id,
            brexit_vote_id=brexit_vote_id
        ))
        #logging.info(f"...created SurveyedCitizen {agent_id} from survey data row {i}.")       
    logging.info("...created SurveyedCitizens from survey data")

    # For demonstration purposes, log a random sample of the SurveyedCitizens
    n_sample = 2
    logging.info(f"Random sample of {n_sample} SurveyedCitizens...")
    indexes = random.sample(range(len(scs)), min(n_sample, len(scs))) 
    for idx in indexes:
        #logging.info(str(scs[idx]))
        logging.info(f"Persona: {scs[idx].get_persona()}")
    
    # Add SurveyedCitizens to the SurveyedNation environment
    logging.info("Adding SurveyedCitizens to the SurveyedNation environment...")
    for sc in scs:
        surveyed_nation.agents_active[sc.id] = sc
    logging.info("... added SurveyedCitizens to the SurveyedNation environment")

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
