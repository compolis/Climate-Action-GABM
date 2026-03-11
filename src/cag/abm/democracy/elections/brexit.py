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
from gabm.abm.attributes import GABMAttributeMap
from gabm.abm.democracy.election import ElectionID
from gabm.abm.democracy.elections.uk import UKReferendum, UKReferendumVote


class BrexitVoteID(VoteID):
    """
    Brexit Referendum VoteID class, inheriting from the GABM VoteID class.
    """
    def __init__(self, value: int):
        """
        Initialize a Brexit Referendum VoteID instance.

        Parameters:
            value:
                The integer value representing the vote ID.
        """
        super().__init__(value)

BrexitVoteID.UNKNOWN = BrexitVoteID(0)
BrexitVoteID.REMAIN = BrexitVoteID(1)
BrexitVoteID.LEAVE = BrexitVoteID(2)
BrexitVoteID.DONT_KNOW = BrexitVoteID(3)

class BrexitVote(BrexitVoteID):
    """
    Brexit Referendum Vote class, inheriting from the UKReferendumVote class.

    .. note::
        Inherits all attributes and methods from :class:`UKReferendumVote`.

    Attributes:
        vote_id (BrexitVoteID):
            The unique identifier for the Brexit referendum vote.
    """
    def __init__(self, vote_id: BrexitVoteID):
        """
        Initialize a Brexit Referendum Vote instance.

        Parameters:
            vote_id:
                Unique identifier for the Brexit referendum vote.
        """
        super().__init__(vote_id)

class BrexitVoteMap(GABMAttributeMap):
    """
    A mapping of BrexitVoteIDs to BrexitVotes.

    By default, the map is initialized as follows::

        items: Dict[BrexitVoteID, BrexitVote] = {
            BrexitVoteID.REMAIN: BrexitVote(BrexitVoteID.REMAIN),
            BrexitVoteID.LEAVE: BrexitVote(BrexitVoteID.LEAVE),
            BrexitVoteID.DONT_KNOW: BrexitVote(BrexitVoteID.DONT_KNOW)
        }
        super().__init__(items)
    """
    def __init__(self):
        """
        Initialize the UK Brexit Referendum Vote Map.
        """
        items: Dict[BrexitVoteID, BrexitVote] = {
            BrexitVoteID.REMAIN: BrexitVote(BrexitVoteID.REMAIN),
            BrexitVoteID.LEAVE: BrexitVote(BrexitVoteID.LEAVE),
            BrexitVoteID.DONT_KNOW: BrexitVote(BrexitVoteID.DONT_KNOW)
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
        super().__init__(election_id, date, question)
        logging.info(f"Initialized Brexit Referendum with ID {election_id} on {date}")