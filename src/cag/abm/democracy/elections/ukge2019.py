"""
UK General Election 2019 module for Climate-Action-GABM.
"""
# Metadata
__author__ = ["Andy Turner <agdturner@gmail.com>"]
__version__ = "0.1.0"
__copyright__ = "Copyright (c) 2026 Climate-Action-GABM contributors, University of Leeds"

# Standard library imports
import logging
from datetime import date
# GABM imports
from gabm.abm.democracy.elections.uk.general_election import UKGE, UKGEVote

class UKGE2019(UKGE):
    """
    UK General Election 2019 class, inheriting from the UKGE class.
    """
    def __init__(self, election_id: ElectionID):
        """
        Initialize a UK General Election 2019 instance.

        Parameters:
        - election_id: Unique identifier for the general election.
        """
        date = date.fromisoformat("2019-12-12")
        super().__init__(election_id, date)
        logging.info(f"Initialized UK General Election 2019 with ID {election_id} on {date}")
