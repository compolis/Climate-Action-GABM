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

# Standard library imports
import logging
from typing import TYPE_CHECKING, Set
# To avoid circular imports, TYPE_CHECKING is used.
if TYPE_CHECKING:
    from gabm.abm.environment import Environment
    from gabm.abm.agents.agent import Agent
    from gabm.abm.agents.group import Group

class Citizen(Person):
    """
    A Person who belongs to the Nation.
    """
    def __init__(self, agent_id: int, environment: Nation,
        """
        Args:
            agent_id: Unique identifier for the agent.
            environment: The environment the agent belongs to.
            opinion: The agent's opinion value.
            year_of_birth: Year of birth (int).
        """
        super().__init__(agent_id, environment, opinion, year_of_birth)


class Non-Resident(Person):
    """
    A Non-Resident is a Person who does not reside in the nation of the environment.
    """
    def __init__(self, agent_id: int, environment: Environment,
        opinion: float = 0.0, year_of_birth: int = None,  
        

class Brit(Resident):
    """
    A Brit is a Person with British nationality.
    """
    def __init__(self, agent_id: int, environment: Environment,
        opinion: float = 0.0, year_of_birth: int = None, 
        gender: int = None):
        """
        Initialize a Person.
        Args:
            agent_id: Unique identifier for the agent.
            environment: The environment the agent belongs to.
            opinion: The agent's opinion value.
            year_of_birth: Year of birth (int).
            gender: Gender, 0 is female, 1 is male, 2 is non-binary, None is not set.
        """
        super().__init__(agent_id, environment, opinion)
        """
        If year of birth is none, then the person is initialised with a 
        year of birth that would make them 18 years old in the current 
        year of the environment. This is just a default assumption to 
        give them an age, but it can be overridden by providing a 
        specific year_of_birth.
        """
        if year_of_birth is None:
            self.year_of_birth = self.environment.year - 18
        else:
            self.year_of_birth = year_of_birth
            """
            If year_of_birth is greater than the current year set year 
            of birth to be the current year from the environment.
            """
            if self.year_of_birth > self.environment.year:
                logging.warning(f"year_of_birth ({self.year_of_birth}) cannot be greater than the current year ({self.environment.year}). Setting year_of_birth to {self.environment.year}.")
                self.year_of_birth = self.environment.year
            """
            If year_of_birth is less than 1900, set it to 1900 to avoid unrealistic ages.
            """
            if self.year_of_birth < 1900:
                logging.warning(f"year_of_birth ({self.year_of_birth}) is less than 1900. Setting year_of_birth to 1900.")


    get_Age(self) -> int:
        """
        Get the age of the person based on the current year in the environment and their year of birth.
        :return: Age in years, or None if year_of_birth is not set.
        """
        if self.year_of_birth is None:
            return None
        return self.environment.year - self.year_of_birth

    def get_Gender(self) -> str:
        """
        Get the gender of the person as a string.
        :return: Gender as a string.
        """
        gender_map = {0: "female", 1: "male", 2: "non-binary"}
        return gender_map[self.gender]

    def __str__(self):
        """
        String representation of the Person.
        """ 
        return f"Person(id={self.agent_id}, opinion={self.opinion}, year_of_birth={self.year_of_birth}, gender={self.get_Gender()})"

    def __repr__(self):
        """
        Official string representation of the Person.
        """
        return self.__str__()

    def get_self_description(self) -> str:
        """
        Get a self-description of the person.
        :return: A string describing the person.
        """
        age = self.get_Age()
        desc = f"I am {age} years old. "
        if self.gender is not None:
            desc += f"I am {self.get_Gender()}. "
        return desc