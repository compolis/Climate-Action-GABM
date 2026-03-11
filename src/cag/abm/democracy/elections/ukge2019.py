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
from gabm.abm.attributes import GABMAttributeMap
from gabm.abm.democracy.elections.uk.general_election import UKGE, UKGEVoteID, UKGEVote
from gabm.abm.democracy.election import ElectionID

class UKGE2019VoteID(UKGEVoteID):
    """
    UK General Election 2019 VoteID class, inheriting from the UKGEVoteID class.
    """
    def __init__(self, value: int):
        """
        Initialize a UK General Election 2019 VoteID instance.

        Parameters:
            value:
                The integer value representing the vote ID.
        """
        super().__init__(value)

UKGE2019VoteID.UNKNOWN = UKGE2019VoteID(0)
UKGE2019VoteID.CONSERVATIVE = UKGE2019VoteID(1)
UKGE2019VoteID.LABOUR = UKGE2019VoteID(2)
UKGE2019VoteID.LIBERAL_DEMOCRATS = UKGE2019VoteID(3)
UKGE2019VoteID.BREXIT = UKGE2019VoteID(4)
UKGE2019VoteID.GREEN = UKGE2019VoteID(5)
UKGE2019VoteID.OTHER = UKGE2019VoteID(6)
UKGE2019VoteID.DONT_KNOW = UKGE2019VoteID(7)

class UKGE2019Vote(UKGEVote):
    """
    UK General Election 2019 Vote class, inheriting from the UKGEVote class.

    .. note::
        Inherits all attributes and methods from :class:`UKGEVote`.
    Attributes:
        vote_id (UKGEVoteID):
            The unique identifier for the general election vote.
    """
    def __init__(self, vote_id: UKGEVoteID):
        """
        Initialize a UK General Election 2019 Vote instance.

        Parameters:
            vote_id:
                Unique identifier for the general election vote.
        """
        super().__init__(vote_id)

class UKGE2019VoteMap(GABMAttributeMap):
    """
    A mapping of UKGEVoteIDs to UKGE2019Votes.

    By default, the map is initialized as follows::

        items: Dict[UKGEVoteID, UKGE2019Vote] = {
            UKGE2019VoteID.UNKNOWN: UKGE2019Vote(UKGE2019VoteID.UNKNOWN),
            UKGE2019VoteID.CONSERVATIVE: UKGE2019Vote(UKGE2019VoteID.CONSERVATIVE),
            UKGE2019VoteID.LABOUR: UKGE2019Vote(UKGE2019VoteID.LABOUR),
            UKGE2019VoteID.LIBERAL_DEMOCRATS: UKGE2019Vote(UKGE2019VoteID.LIBERAL_DEMOCRATS),
            UKGE2019VoteID.BREXIT: UKGE2019Vote(UKGE2019VoteID.BREXIT),
            UKGE2019VoteID.GREEN: UKGE2019Vote(UKGE2019VoteID.GREEN),
            UKGE2019VoteID.OTHER: UKGE2019Vote(UKGE2019VoteID.OTHER),
            UKGE2019VoteID.DONT_KNOW: UKGE2019Vote(UKGE2019VoteID.DONT_KNOW)
        }
        super().__init__(items)
    """
    def __init__(self):
        """
        Initialize the UK General Election 2019 Vote Map.
        """
        items: Dict[UKGEVoteID, UKGE2019Vote] = {
            UKGE2019VoteID.UNKNOWN: UKGE2019Vote(UKGE2019VoteID.UNKNOWN),
            UKGE2019VoteID.CONSERVATIVE: UKGE2019Vote(UKGE2019VoteID.CONSERVATIVE),
            UKGE2019VoteID.LABOUR: UKGE2019Vote(UKGE2019VoteID.LABOUR),
            UKGE2019VoteID.LIBERAL_DEMOCRATS: UKGE2019Vote(UKGE2019VoteID.LIBERAL_DEMOCRATS),
            UKGE2019VoteID.BREXIT: UKGE2019Vote(UKGE2019VoteID.BREXIT),
            UKGE2019VoteID.GREEN: UKGE2019Vote(UKGE2019VoteID.GREEN),
            UKGE2019VoteID.OTHER: UKGE2019Vote(UKGE2019VoteID.OTHER),
            UKGE2019VoteID.DONT_KNOW: UKGE2019Vote(UKGE2019VoteID.DONT_KNOW)
        }
        super().__init__(items)

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
