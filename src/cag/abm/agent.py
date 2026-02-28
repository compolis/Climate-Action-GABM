# NOTE: This import must be the very first non-empty line in the file (even before docstrings)
# due to Python syntax rules for __future__ imports.
from __future__ import annotations
"""
Agent module for Climate-Action-GABM.
"""
# Metadata
__author__ = ["Andy Turner <agdturner@gmail.com>"]
__version__ = "0.2.0"
__copyright__ = "Copyright (c) 2026 Climate-Action-GABM contributors, University of Leeds"


# Standard library imports
import logging
from typing import TYPE_CHECKING, Set
# To avoid circular imports, TYPE_CHECKING is used.
if TYPE_CHECKING:
    from cag.abm.environment import Nation

class Voter(Citizen):
    """
    A Citizen with a vote.
    """
    def __init__(self, agent_id: int, environment: "Nation",
        year_of_birth: int = None, gender: int = None,
        opinions: dict = None):
        """
        Args:
            agent_id: Unique identifier for the agent.
            environment: The Nation the agent belongs to.
            year_of_birth: Year of birth (int).
            gender: Gender, 0 is female, 1 is male, 2 is non-binary, None is not set.
            opinions: A dictionary of opinion values, e.g. {"negative": 10, "
        """
        super().__init__(agent_id, environment, year_of_birth=year_of_birth, gender=gender, opinions=opinions)
