"""
UK General Election 2019 module for Climate-Action-GABM.
"""
# Metadata
__author__ = ["Andy Turner <agdturner@gmail.com>"]
__version__ = "0.7.0"
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
    UK General Election 2019 VoteID.
    """
    def __init__(self, vote_id: int):
        """
        Initialize.
        
        Args:
            vote_id:
                The integer value representing the vote ID.
        """
        super().__init__(vote_id)

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
    UK General Election 2019 Vote.
    
    .. note::
        Inherits all attributes and methods from :class:`UKGEVote`.

    Attributes:
        description (str):
            A description of the vote.
    """
    def __init__(self, vote_id: UKGE2019VoteID, description: str, election_id: ElectionID, voter_id: str = None, candidate_id: str = None):
        """
        Initialize a UK General Election 2019 Vote instance.

        Args:
            vote_id:
                Unique identifier for the vote.
            description:
                A description of the vote.
            election_id:
                Identifier for the associated election.
            voter_id:
                Identifier for the voter.
            candidate_id:
                Identifier for the candidate being voted for.
        """
        super().__init__(vote_id, election_id, voter_id, candidate_id)
        self.description = description

class UKGE2019VoteMap(GABMAttributeMap):
    """
    A mapping of UKGE2019VoteIDs to UKGE2019Votes.

    By default, the map is initialized as follows::

        items: Dict[UKGEVoteID, UKGE2019Vote] = {
            UKGE2019VoteID.UNKNOWN: UKGE2019Vote(UKGE2019VoteID.UNKNOWN, "Unknown vote", election_id),
            UKGE2019VoteID.CONSERVATIVE: UKGE2019Vote(UKGE2019VoteID.CONSERVATIVE, "Conservative", election_id),
            UKGE2019VoteID.LABOUR: UKGE2019Vote(UKGE2019VoteID.LABOUR, "Labour", election_id),
            UKGE2019VoteID.LIBERAL_DEMOCRATS: UKGE2019Vote(UKGE2019VoteID.LIBERAL_DEMOCRATS, "Liberal Democrats", election_id),
            UKGE2019VoteID.BREXIT: UKGE2019Vote(UKGE2019VoteID.BREXIT, " Brexit", election_id),
            UKGE2019VoteID.GREEN: UKGE2019Vote(UKGE2019VoteID.GREEN, "Green", election_id),
            UKGE2019VoteID.OTHER: UKGE2019Vote(UKGE2019VoteID.OTHER, "Other", election_id),
            UKGE2019VoteID.DONT_KNOW: UKGE2019Vote(UKGE2019VoteID.DONT_KNOW, "Don't know", election_id)
        }
        super().__init__(items)
    """
    def __init__(self, election_id: ElectionID):
        """
        Initialize the UK General Election 2019 Vote Map.

        Args:
            election_id:
                Unique identifier for the associated election.

        """
        items: Dict[UKGEVoteID, UKGE2019Vote] = {
            UKGE2019VoteID.UNKNOWN: UKGE2019Vote(UKGE2019VoteID.UNKNOWN, "unknown", election_id),
            UKGE2019VoteID.CONSERVATIVE: UKGE2019Vote(UKGE2019VoteID.CONSERVATIVE, "Conservative", election_id),
            UKGE2019VoteID.LABOUR: UKGE2019Vote(UKGE2019VoteID.LABOUR, "Labour", election_id),
            UKGE2019VoteID.LIBERAL_DEMOCRATS: UKGE2019Vote(UKGE2019VoteID.LIBERAL_DEMOCRATS, "Liberal Democrat", election_id),
            UKGE2019VoteID.BREXIT: UKGE2019Vote(UKGE2019VoteID.BREXIT, "Brexit", election_id),
            UKGE2019VoteID.GREEN: UKGE2019Vote(UKGE2019VoteID.GREEN, "Green", election_id),
            UKGE2019VoteID.OTHER: UKGE2019Vote(UKGE2019VoteID.OTHER, "another", election_id),
            UKGE2019VoteID.DONT_KNOW: UKGE2019Vote(UKGE2019VoteID.DONT_KNOW, "don't know", election_id)
        }
        super().__init__(items)

class UKGE2019(UKGE):
    """
    UK General Election 2019 class.

    .. note::
        Inherits all attributes and methods from :class:`UKGE`.
    """
    def __init__(self, election_id: ElectionID):
        """
        Initialize a UK General Election 2019 instance.

        Args:
            election_id:
                Unique identifier for the general election.
        
        """
        date_str = "2019-12-12"
        description = "UK General Election " + date_str
        election_date = date.fromisoformat(date_str)
        super().__init__(election_id, election_date, description)
        logging.info(f"Initialized {description} with ID {election_id}")
