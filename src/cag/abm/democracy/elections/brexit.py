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
from gabm.abm.agent import CitizenID
from gabm.abm.democracy.election import VoteID
from gabm.abm.attributes import GABMAttributeMap
from gabm.abm.democracy.election import ElectionID
from gabm.abm.democracy.elections.uk import UKReferendum, UKReferendumVote


class BrexitVoteID(VoteID):
    """
    Brexit Referendum VoteID class, inheriting from the GABM VoteID class.
    """
    def __init__(self, vote_id: int):
        """
        Initialize a Brexit Referendum VoteID instance.

        Parameters:
            vote_id:
                The integer value representing the vote ID.
        """
        super().__init__(vote_id)

BrexitVoteID.UNKNOWN = BrexitVoteID(0)
BrexitVoteID.REMAIN = BrexitVoteID(1)
BrexitVoteID.LEAVE = BrexitVoteID(2)
BrexitVoteID.DONT_KNOW = BrexitVoteID(3)

class BrexitVote(UKReferendumVote):
    """
    Brexit Referendum Vote.
    
    .. note::
        Inherits all attributes and methods from :class:`UKReferendumVote`.

    Attributes:
        vote_id (BrexitVoteID):
            The unique identifier for the Brexit referendum vote.
    """
    def __init__(self, vote_id: BrexitVoteID, election_id: ElectionID, voter_id: CitizenID = None, description: str = None):
        """
        Initialize a Brexit Referendum Vote instance.

        Parameters:
            vote_id:
                Unique identifier for the Brexit referendum vote.
                description:
                    Human-readable description of the vote.
        """
        super().__init__(vote_id, election_id, voter_id=voter_id)
        self.description = description if description is not None else str(vote_id)

class BrexitVoteMap(GABMAttributeMap):
    """
    A mapping of BrexitVoteIDs to BrexitVotes.

    By default, the map is initialized as follows::

        items: Dict[BrexitVoteID, BrexitVote] = {
            BrexitVoteID.UNKNOWN: BrexitVote(BrexitVoteID.UNKNOWN, election_id),
            BrexitVoteID.REMAIN: BrexitVote(BrexitVoteID.REMAIN, election_id),
            BrexitVoteID.LEAVE: BrexitVote(BrexitVoteID.LEAVE, election_id),
            BrexitVoteID.DONT_KNOW: BrexitVote(BrexitVoteID.DONT_KNOW, election_id)
        }
        super().__init__(items)
    """
    def __init__(self, election_id: ElectionID):
        """
        Initialize the UK Brexit Referendum Vote Map.
        """
        items = {
            BrexitVoteID.UNKNOWN: BrexitVote(BrexitVoteID.UNKNOWN, election_id, description="unknown"),
            BrexitVoteID.REMAIN: BrexitVote(BrexitVoteID.REMAIN, election_id, description="voted to remain"),
            BrexitVoteID.LEAVE: BrexitVote(BrexitVoteID.LEAVE, election_id, description="voted to leave"),
            BrexitVoteID.DONT_KNOW: BrexitVote(BrexitVoteID.DONT_KNOW, election_id, description="don't know what I voted")
        }
        super().__init__(items)

class Brexit(UKReferendum):
    """
    Brexit class, inheriting from the UK class.

    .. note::
        Inherits all attributes and methods from :class:`UKReferendum`.

    Attributes:
        question (str):
            The question posed in the Brexit referendum.

    """
    def __init__(self, election_id: ElectionID, date="2016-06-23", question="Should the United Kingdom remain a member of the European Union?"):
        """
        Initialize.

        Parameters:
            election_id:
                Unique identifier for the Brexit referendum.
            date:
                Date of the Brexit referendum.
            question:
                The question posed in the Brexit referendum.
        """
        choices = ["Remain", "Leave"]
        description = f"Brexit Referendum on {date}: {question}"
        super().__init__(election_id,  date, description, question, choices)
        logging.info(f"Initialized Brexit Referendum {date} with ID {election_id}")