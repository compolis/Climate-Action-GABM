#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Entry point for running the Climate-Action-GABM simulation.
Usage: PYTHONPATH=src python3 -m cag
       make run-local
"""
__author__ = [
    "Andy Turner <agdturner@gmail.com>",
    "Ajaykumar Manivannan <ashwamanivannan@gmail.com>",
    "Charlie Pilgrim <pilgrimcharlie2@gmail.com>",
]
__version__ = "0.3.0"
__copyright__ = "Copyright (c) 2026 Climate-Action-GABM contributors, University of Leeds"

import logging
import random
import sys
from pathlib import Path

from gabm.abm.attributes.gender import GenderID, GenderMap
from gabm.abm.attributes.politics import PoliticsID
from gabm.abm.attributes.ethnicity import EthnicityID
from gabm.abm.attributes.income import IncomeID
from gabm.abm.attributes.education import EducationID
from gabm.abm.attributes.region import RegionID
from gabm.abm.attributes.family import FamilyID
from gabm.abm.democracy.election import ElectionID

from cag.io.survey import load
from cag.abm.environment import SurveyedNation
from cag.abm.agent import SurveyedCitizen
from cag.abm.attributes.opinion import ClimatePolicyID
from cag.abm.attributes.ethnicity import SurveyEthnicityMap
from cag.abm.attributes.income import SurveyIncomeMap
from cag.abm.attributes.politics import SurveyPoliticsMap
from cag.abm.attributes.education import SurveyEducationMap
from cag.abm.attributes.region import UKRegionMap
from cag.abm.attributes.family import SurveyFamilyMap
from cag.abm.democracy.elections.ukge2019 import UKGE2019VoteID, UKGE2019VoteMap
from cag.abm.democracy.elections.brexit import BrexitVoteID, BrexitVoteMap
from cag.abm.attributes.narratives import (
    SelftranscMap, SelfenhMap, OpennessMap, ConformTradMap,
    SDOMap, EDOMap, RWAMap, rescale_1_6, rescale_1_7,
)
from cag.abm.sim import run_simulation, save_results, plot_opinion_trajectories, SIM_CONFIG


# ── Small-run config for `make run-local` ─────────────────────
# Override SIM_CONFIG defaults with a quick 10-agent, 3-day run.
LOCAL_CONFIG = {
    "n_citizens": 10,
    "days": [
        {"policy": ClimatePolicyID.CARBON_TAX, "phases": ["P-A", "P-B", "C"]},
        {"policy": ClimatePolicyID.RENEWABLE_ENERGY, "phases": ["P-A", "P-B", "C"]},
        {"policy": ClimatePolicyID.CARBON_TAX, "phases": ["P-B", "P-A", "C"]},
    ],
    "k_peers_per_day": 3,
    "p_intra": 0.3,       # denser network for small N
    "p_inter": 0.05,
    "random_seed": 42,
}


def build_nation(data, year=2026):
    """Create a SurveyedNation and populate it with citizens from survey data."""
    UKGE2019_ELECTION_ID = ElectionID(0)
    BREXIT_REFERENDUM_ID = ElectionID(1)

    sn = SurveyedNation(
        year=year, place="UK",
        gender_map=GenderMap(),
        region_map=UKRegionMap(),
        education_map=SurveyEducationMap(),
        ethnicity_map=SurveyEthnicityMap(),
        income_map=SurveyIncomeMap(),
        politics_map=SurveyPoliticsMap(),
        family_map=SurveyFamilyMap(),
        ukge2019_vote_map=UKGE2019VoteMap(UKGE2019_ELECTION_ID),
        brexit_vote_map=BrexitVoteMap(BREXIT_REFERENDUM_ID),
        selftransc_map=SelftranscMap,
        selfenh_map=SelfenhMap,
        openness_map=OpennessMap,
        conformtrad_map=ConformTradMap,
        sdo_map=SDOMap,
        edo_map=EDOMap,
        rwa_map=RWAMap,
    )

    for i in range(len(data)):
        row = data.iloc[i]
        sc = SurveyedCitizen(
            agent_id=row.get("ID", None),
            original_survey_data=row,
            environment=sn,
            year_of_birth=year - int(row.get("age", 0)),
            gender_id=GenderID.MALE if int(row.get("male_dummy", 0)) == 1 else GenderID.FEMALE,
            region_id=RegionID(int(row.get("tprofile_GOR", 0))),
            education_id=EducationID(int(row.get("profile_education_level", 0))),
            income_id=IncomeID(int(row.get("tprofile_gross_household", 0))),
            ethnicity_id=EthnicityID(int(row.get("ethnicity_R", 0))),
            family_id=FamilyID.PARENT if int(row.get("parent_dummy", 0)) == 1 else FamilyID.NOT_PARENT,
            ukge2019_vote_id=UKGE2019VoteID(int(row.get("Vote2019R", 0))),
            brexit_vote_id=BrexitVoteID(int(row.get("pastvote_EURef", 0))),
            politics_id=PoliticsID(int(row.get("Political_Left_Right", 0))),
            selftransc_id=rescale_1_6(int(row.get("Selftransc_Val", 0))),
            selfenh_id=rescale_1_6(int(row.get("Selfenh_Values", 0))),
            openness_id=rescale_1_6(int(row.get("Openness", 0))),
            conformtrad_id=rescale_1_6(int(row.get("ConformTrad", 0))),
            sdo_id=rescale_1_7(int(row.get("SDO", 0))),
            edo_id=rescale_1_7(int(row.get("EDO", 0))),
            rwa_id=rescale_1_6(int(row.get("RWA", 0))),
        )
        sn.agents_active[sc.id] = sc

    return sn


def main():
    logging.info("--- Climate-Action-GABM ---")

    random.seed(LOCAL_CONFIG["random_seed"])
    n_citizens = LOCAL_CONFIG["n_citizens"]

    # Load and subsample survey data
    logging.info("Loading survey data...")
    data = load("data/yougov_survey_data/YouGovProcessedData.csv")
    data = data.sample(n=n_citizens, random_state=LOCAL_CONFIG["random_seed"])
    logging.info(f"Sampled {len(data)} citizens")

    # Build nation
    logging.info("Building SurveyedNation...")
    nation = build_nation(data)
    logging.info(f"Nation ready: {len(nation.agents_active)} agents")

    # Run simulation
    logging.info("Starting simulation...")
    results = run_simulation(LOCAL_CONFIG, nation)
    logging.info("Simulation complete.")

    # Save results
    out_path = save_results(results)
    logging.info(f"Results saved to {out_path}")

    # Plot and save
    plot_path = out_path / "opinion_trajectories.png"
    plot_opinion_trajectories(results, output_path=plot_path)
    logging.info(f"Plot saved to {plot_path}")

    # Summary
    df = results["opinion_trajectories"]
    logging.info(f"Trajectories: {len(df)} rows, {df['agent_id'].nunique()} agents, "
                 f"{df['day'].nunique()} days, {df['policy_id'].nunique()} policies")


if __name__ == "__main__":
    log_dir = Path("data/logs")
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / "run_main.log"
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[
            logging.FileHandler(log_file, mode="w"),
            logging.StreamHandler(sys.stdout),
        ],
    )
    main()
