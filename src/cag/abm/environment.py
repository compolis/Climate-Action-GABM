"""
Defines the Political_Environment class.
"""
# Metadata
__author__ = ["Andy Turner <agdturner@gmail.com>"]
__version__ = "0.1.0"
__copyright__ = "Copyright (c) 2026 Climate-Action-GABM contributors, University of Leeds"


# GABM imports
from gabm.abm.environment import Environment

class Nation(Environment):
    """
    A Nation is a type of Environment with a nation attribute.
    """

    def __init__(self, year: int = 2026, nation: str = "United Kingdom"):
        """
        Initialize the environment.
        :param year: The current year in the simulation.
        :param nation: The nation in the simulation.
        """
        super().__init__(year)
        self.nation = nation