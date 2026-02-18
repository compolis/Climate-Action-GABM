"""
Defines the Political_Environment class.
"""
# Metadata
__author__ = ["Andy Turner <agdturner@gmail.com>"]
__version__ = "0.1.0"
__copyright__ = "Copyright (c) 2026 Climate-Action-GABM contributors, University of Leeds"


# GABM imports
from gabm.abm.environment import Environment

class Political_Environment(Environment):

    def __init__(self):
        """
        Initialize the environment.
        """
        super().__init__()