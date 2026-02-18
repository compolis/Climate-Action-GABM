# NOTE: This import must be the very first non-empty line in the file (even before docstrings)
# due to Python syntax rules for __future__ imports.
from __future__ import annotations
"""
Defines the generic Person class.
"""
# Metadata
__author__ = ["Andy Turner <agdturner@gmail.com>"]
__version__ = "0.1.0"
__copyright__ = "Copyright (c) 2026 Climate-Action-GABM contributors, University of Leeds"

# To avoid circular imports, TYPE_CHECKING is used to import Environment only for type hints.
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from gabm.abm.environment import Environment


from typing import Set
import logging
from gabm.abm.agents.agent import Agent
if TYPE_CHECKING:
    from gabm.abm.agents.group import Group

class Person(Agent):

    """
    A Person is a type of Agent with a persona.
    """
    def __init__(self, agent_id: int, environment: Environment, opinion: float = 0.0, year_of_birth: int = None, gender: str = "Other"):
        """
        Initialize a Person.
        :param agent_id: Unique identifier for the agent.
        :param environment: The environment the agent belongs to.
        :param opinion: The agent's opinion value.
        :param year_of_birth: Year of birth (int).
        :param gender: Gender, one of "Male", "Female", "Other".
        """
        super().__init__(agent_id, environment, opinion)
        self.year_of_birth = year_of_birth
        if gender not in ("Male", "Female", "Other"):
            raise ValueError("gender must be 'Male', 'Female', or 'Other'")
        self.gender = gender
