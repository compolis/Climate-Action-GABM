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
# Local imports
from gabm.abm.agent import Citizen
from gabm.abm.attributes.gender import GenderID, Gender, GenderMap
from gabm.abm.environment import Nation

def main():
    logging.info("\n--- Climate-Action-GABM ---\n")

    # Set random seed for reproducibility
    random.seed(42)

    # Create environment
    uk = Nation(year=2026)

    # Create gender_map
    gender_map = GenderMap()

    # Create opinions
    opinions = {"climate_change": 0.5}

    # Create a person agent
    person = Citizen(
        agent_id=0,
        environment=uk,
        year_of_birth=2008,
        gender_map=gender_map,
        gender=GenderID.MALE,
        opinions={"climate_change": 0.5}
    )

    logging.info(f"Created agent: {person}")

    
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
