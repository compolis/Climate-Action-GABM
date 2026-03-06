"""
Brexit module for Climate-Action-GABM.
"""
# Metadata
__author__ = ["Andy Turner <agdturner@gmail.com>"]
__version__ = "0.1.0"
__copyright__ = "Copyright (c) 2026 Climate-Action-GABM contributors, University of Leeds"

# Standard library imports
import logging
from datetime import date
# GABM imports
from gabm.abm.democracy.election import VoteID
# Local imports
from cag.abm.democracy.elections import ElectionID
from cag.abm.democracy.elections/uk import UKReferendum, UKReferendumVote

class UKBrexitReferendum(UKReferendum):
    """
    UK Brexit Referendum class, inheriting from the UK Referendum class.
    """
    def __init__(self, election_id: ElectionID, date="2016-06-23"):
        """
        Initialize a UK Brexit Referendum instance.

        Parameters:
        - election_id: Unique identifier for the Brexit referendum.
        - date: Date of the Brexit referendum.
        """
        question = "Should the United Kingdom remain a member of the European Union?"
        super().__init__(election_id, date, question)
        logging.info(f"Initialized UK Brexit Referendum with ID {election_id} on {date}")

class UKBrexitReferendumVote(UKReferendumVote):
    """
    UK Brexit Referendum Vote class, inheriting from the UKReferendumVote class.
    """
    def __init__(self, vote_id: VoteID, election_id: ElectionID, voter_id: str, choice: str):
        """
        Initialize a UK Brexit Referendum Vote instance.

        Parameters:
        - vote_id: Unique identifier for the vote.
        - election_id: Identifier for the associated Brexit referendum.
        - voter_id: Identifier for the voter.
        - choice: The choice made by the voter (e.g., "Yes" or "No").
        """
        super().__init__(vote_id, election_id, voter_id, choice)
        logging.info(f"Recorded UK Brexit Referendum vote {vote_id} for referendum {election_id} by voter {voter_id} with choice {choice}")
        Initialize a UK General Election instance.

        Parameters:
        - election_id: Unique identifier for the general election.
        - date: Date of the general election.
        """
        super().__init__(election_id, date)
        logging.info(f"Initialized UK General Election with ID {election_id} on {date}")