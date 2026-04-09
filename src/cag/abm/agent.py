# NOTE: This import must be the very first non-empty line in the file (even before docstrings)
# due to Python syntax rules for __future__ imports.
from __future__ import annotations
"""
Agent module for Climate-Action-GABM.
"""
# Metadata
__author__ = ["Andy Turner <agdturner@gmail.com>","Ajaykumar Manivannan <ashwamanivannan@gmail.com>"]
__version__ = "0.1.0"
__copyright__ = "Copyright (c) 2026 Climate-Action-GABM contributors, University of Leeds"

# Standard library imports
import logging
from datetime import date

class SurveyedCitizen():
    
    def __init__(
        self,
        agent_id,
        environment,
        year_of_birth = None,
        gender_id = None,
        region_id = None,
        education_id = None,
        ethnicity_id = None,
        income_id = None,
        politics_id = None,
        family_id = None,
        ukge2019_vote_id = None,
        brexit_vote_id = None,
        selftransc_id = None,
        selfenh_id = None,
        openness_id = None,
        conformtrad_id = None,
        sdo_id = None,
        edo_id = None,
        rwa_id = None,
        opinions = None
    ):
        
        self.id = agent_id
        self.environment = environment
        self.year_of_birth = year_of_birth
        self.gender_id = gender_id
        self.region_id = region_id
        self.education_id = education_id
        self.ethnicity_id = ethnicity_id
        self.income_id = income_id
        self.politics_id = politics_id
        self.family_id = family_id
        self.ukge2019_vote_id = ukge2019_vote_id
        self.brexit_vote_id = brexit_vote_id
        self.selftransc_id = selftransc_id
        self.selfenh_id = selfenh_id
        self.openness_id = openness_id
        self.conformtrad_id = conformtrad_id
        self.sdo_id = sdo_id
        self.edo_id = edo_id
        self.rwa_id = rwa_id
        self.opinions = opinions or {}

        self.opinion_history = {}

    def __str__(self):
        """
        Returns a string representation of the SurveyedCitizen agent.
        """
        r = super().__str__()
        sn = self.get_surveyed_nation()
        r += f", region={sn.region_map.get(self.region_id).description}"
        r += f", education={sn.education_map.get(self.education_id).description}"
        r += f", ethnicity={sn.ethnicity_map.get(self.ethnicity_id).description}"
        r += f", income={sn.income_map.get(self.income_id).description}"
        r += f", politics={sn.politics_map.get(self.politics_id).description}"
        r += f", family={sn.family_map.get(self.family_id).description}"
        try:
            ukge2019_vote = sn.ukge2019_vote_map.get(self.ukge2019_vote_id)
            ukge2019_vote_str = getattr(ukge2019_vote, 'description', str(ukge2019_vote)) if ukge2019_vote else 'Unknown'
        except TypeError:
            ukge2019_vote_str = 'Unknown'
        try:
            brexit_vote = sn.brexit_vote_map.get(self.brexit_vote_id)
            brexit_vote_str = getattr(brexit_vote, 'description', str(brexit_vote)) if brexit_vote else 'Unknown'
        except TypeError:
            brexit_vote_str = 'Unknown'
        r += f", UKGE2019 vote={ukge2019_vote_str}"
        r += f", Brexit vote={brexit_vote_str}"
        r += f", Selftransc value={sn.selftransc_map.get(self.selftransc_id).description}"
        r += f", Selfenh value={sn.selfenh_map.get(self.selfenh_id).description}"
        r += f", Openness value={sn.openness_map.get(self.openness_id).description}"
        r += f", Conformtrad value={sn.conformtrad_map.get(self.conformtrad_id).description}"
        r += f", SDO value={sn.sdo_map.get(self.sdo_id).description}"
        r += f", EDO value={sn.edo_map.get(self.edo_id).description}"
        r += f", RWA value={sn.rwa_map.get(self.rwa_id).description}"

        return r

    def get_surveyed_nation(self) -> SurveyedNation:
        """
        Returns the SurveyedNation environment that the agent is in.
        """
        return self.environment

    def get_persona(self) -> str:
        """
        Returns a persona based on attributes.

        Returns:
            A string representing the persona.
        """
        sn = self.get_surveyed_nation()
        age = date.today().year - self.year_of_birth
        gender = sn.gender_map.get(self.gender_id).description
        region = sn.region_map.get(self.region_id).description
        ethnicity = sn.ethnicity_map.get(self.ethnicity_id).description
        education = sn.education_map.get(self.education_id).description
        income = sn.income_map.get(self.income_id).description
        politics = sn.politics_map.get(self.politics_id).description
        family = sn.family_map.get(self.family_id).description
        try:
            ukge2019_vote_obj = sn.ukge2019_vote_map.get(self.ukge2019_vote_id)
            ukge2019_vote = getattr(ukge2019_vote_obj, 'description', str(ukge2019_vote_obj)) if ukge2019_vote_obj else 'Unknown'
        except TypeError:
            ukge2019_vote = 'Unknown'
        try:
            brexit_vote_obj = sn.brexit_vote_map.get(self.brexit_vote_id)
            brexit_vote = getattr(brexit_vote_obj, 'description', str(brexit_vote_obj)) if brexit_vote_obj else 'Unknown'
        except TypeError:
            brexit_vote = 'Unknown'
        r: str = f"I am a {age} year old {gender} living in the {region}. "
        if ethnicity != "unknown" and ethnicity != "other":
            r += f"My ethnicity is {ethnicity}. "
        if education != "unknown":
            r += f"I have a {education}. "
        if income != "unknown":
            r += f"My gross household income is {income}. "
        if family != "unknown":
            r += f"I am {family}. "
        if politics != "unknown" and politics != "don't know":
            r += f"I position myself {politics} of the political spectrum. "
        if ukge2019_vote != "unknown" and ukge2019_vote != "another" and ukge2019_vote != "don't know":
            r += f"I voted for the {ukge2019_vote} party candidate in the 2019 General Election. "
        if brexit_vote != "unknown" and brexit_vote != "don't know":
            r += f"I {brexit_vote} in the 2016 EU Referendum."
        return r
 
    def get_narrative(self) -> str:
        """
        Returns a narrative based on attributes.

        Returns:
            A string representing the narrative.
        """
        sn = self.environment
        def safe_get(attr_map, attr_id):
            if attr_id is None:
                return "Unknown"
            try:
                return attr_map.get(attr_id).description
            except Exception:
                return "Unknown"

        selftransc = safe_get(sn.selftransc_map, self.selftransc_id)
        selfenh = safe_get(sn.selfenh_map, self.selfenh_id)
        openness = safe_get(sn.openness_map, self.openness_id)
        conformtrad = safe_get(sn.conformtrad_map, self.conformtrad_id)
        sdo = safe_get(sn.sdo_map, self.sdo_id)
        edo = safe_get(sn.edo_map, self.edo_id)
        rwa = safe_get(sn.rwa_map, self.rwa_id)
        descriptions = [d for d in [selftransc, selfenh, openness, conformtrad, sdo, edo, rwa] if d.lower() != "unknown"]
        if not descriptions:
            return ""
        return "When it comes to my core values and worldview: " + " ".join(descriptions)