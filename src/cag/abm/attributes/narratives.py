"""
Narratives module for Climate-Action-GABM.
"""
# Metadata
__author__ = ["Andy Turner <agdturner@gmail.com>"]
__version__ = "0.9.0"
__copyright__ = "Copyright (c) 2026 Climate-Action-GABM contributors, University of Leeds"

# Standard library imports
import logging
# Local imports
from gabm.abm.attribute import GABMAttributeID, GABMAttribute, GABMAttributeMap

class NarrativeAttributeID(GABMAttributeID):
    """
    Identifier for narrative attributes.

    Attributes:
        id (int):
            The unique identifier.
    """
    def __init__(self, narrative_id: int):
        """
        Initialize.

        Args:
            narrative_id:
                The unique identifier for the narrative attribute.
        """
        super().__init__(narrative_id)

# Define specific NarrativeAttributeID instances for the survey data.
UNKNOWN = NarrativeAttributeID(0)
LOW = NarrativeAttributeID(1)
MODERATE = NarrativeAttributeID(2)
HIGH = NarrativeAttributeID(3)

class NarrativeAttribute(GABMAttribute):
    """
    For representing narrative attributes.
    
    Attributes:
        id (NarrativeAttributeID):
            The unique identifier for the narrative attribute.
        description (str):
            A description of the narrative attribute.
    """
    def __init__(self, narrative_id: NarrativeAttributeID, description: str):
        """
        Initialize.

        Args:
            narrative_id:
                The unique identifier for the narrative attribute.
            description:
                A description of the narrative attribute.
        """
        super().__init__(narrative_id, description)

class NarrativeAttributeMap(GABMAttributeMap):
    def __init__(self, items):
        super().__init__(items)

# Selftransc
SELFTRANSC = [
    (UNKNOWN, "unknown"),
    (LOW, "I prioritize my own immediate circle or needs and do not place high importance on protecting the natural environment, promoting global peace, or actively caring for the well-being and equal treatment of others."),
    (MODERATE, "I care about the people close to me and have a basic respect for nature, but I do not actively champion global equality or make environmental protection a primary, driving life focus."),
    (HIGH, "I am deeply committed to caring for nature, protecting the environment, and responding to the needs of others. I strongly believe in global harmony, equal opportunities for everyone, and actively helping those around me.")
]

selftransc_val_items = {id: NarrativeAttribute(id, desc) for id, desc in SELFTRANSC}
SelftranscMap = NarrativeAttributeMap(selftransc_val_items)

# Selfenh
SELFENH = [
    (UNKNOWN, "unknown"),
    (LOW, "I am not strongly driven by the need to get ahead of others, impress people, or hold leadership positions where I tell others what to do."),
    (MODERATE, "I appreciate personal success and am capable of taking charge when necessary, but I do not feel a constant need to dominate decisions or impress others to feel fulfilled."),
    (HIGH, "I am highly motivated by personal success, getting ahead in life, and impressing others. I strongly desire to be in charge, be the primary decision-maker, and have people follow my lead.")
]

selfenh_values_items = {id: NarrativeAttribute(id, desc) for id, desc in SELFENH}
SelfenhMap = NarrativeAttributeMap(selfenh_values_items)

# Openness
OPENNESS = [
    (UNKNOWN, "unknown"),
    (LOW, "I prefer routine and the familiar, showing little interest in taking risks, seeking out new adventures, or coming up with highly original ideas."),
    (MODERATE, "I am moderately curious and will occasionally try new things, but I generally balance this by relying on familiar methods rather than constantly seeking out extreme novelty or risks."),
    (HIGH, "I am highly curious, adventurous, and love trying out new things. I value creativity, originality, and taking risks to fully understand the world around me.")
]

openness_items = {id: NarrativeAttribute(id, desc) for id, desc in OPENNESS}
OpennessMap = NarrativeAttributeMap(openness_items)

# ConformTrad
CONFORMTRAD = [
    (UNKNOWN, "unknown"),
    (LOW, "I do not feel strictly bound by traditional values, customs, or the need to be unconditionally obedient to older generations."),
    (MODERATE, "I maintain a general respect for elders and standard societal norms, but I am flexible in my thinking and do not strictly adhere to all traditional customs."),
    (HIGH, "I place a high value on obedience, showing deep respect for parents and older people. I strongly believe in maintaining traditional ways of thinking, keeping up customs, and always behaving properly according to expectations.")
]

ConformTrad_items = {id: NarrativeAttribute(id, desc) for id, desc in CONFORMTRAD}
ConformTradMap = NarrativeAttributeMap(ConformTrad_items)

# SDO
SDO = [
    (UNKNOWN, "unknown"),
    (LOW, "I strongly believe that all groups should have an equal chance to succeed and that society should actively work to equalize conditions. I firmly reject the idea that any group is inferior or should dominate others."),
    (MODERATE, "I generally support fairness but might implicitly accept that some mild social hierarchies are a natural part of society, without actively pushing for extreme inequality or strict egalitarianism."),
    (HIGH, "I believe that an ideal society requires some groups to be on top and others on the bottom. I view certain groups as inherently inferior and oppose efforts to make all groups equal, feeling that equality should not be a primary goal.")
]

SDO_items = {id: NarrativeAttribute(id, desc) for id, desc in SDO}
SDOMap = NarrativeAttributeMap(SDO_items)

# EDO
EDO = [
    (UNKNOWN, "unknown"),
    (LOW, "I believe that all lifeforms on Earth should be treated equally and that no single species, including humans, should dominate the planet."),
    (MODERATE, "I believe human progress is important but should generally be balanced with environmental respect, avoiding the extreme view that humans must always dominate nature."),
    (HIGH, "I believe humans are inherently superior to other lifeforms and that humanity must sometimes put itself ahead of nature to progress. I firmly support the idea that humans should dominate the natural world.")
]

EDO_items = {id: NarrativeAttribute(id, desc) for id, desc in EDO}
EDOMap = NarrativeAttributeMap(EDO_items)

# RWA
RWA = [
    (UNKNOWN, "unknown"),
    (LOW, "I am highly skeptical of leaders and believe that questioning authority and traditions is necessary for societal progress. I strongly oppose the use of force against others, even if ordered to do so by proper authorities."),
    (MODERATE, "I have a healthy respect for leaders and traditions but maintain some skepticism; I generally believe force should be avoided unless dealing with highly specific, threatening situations."),
    (HIGH, "I believe leaders generally know what is best and tell the truth, and that traditions are the foundation of a healthy society. I view people who challenge traditions as dangerous and strongly support using strong force against threatening groups.")
]

RWA_items = {id: NarrativeAttribute(id, desc) for id, desc in RWA}
RWAMap = NarrativeAttributeMap(RWA_items)

def rescale_1_6(val : int) -> NarrativeAttributeID: 
    """
    Utility function to rescale 1-6 to 1-3 (1-2 -> 1, 3-4 -> 2, 5-6 -> 3)

    Args:
        val (int): The value to rescale, expected to be in the range 1-6.

    Returns:
        NarrativeAttributeID: The rescaled value in the range 1-3, or 0 if the input is outside the expected range.
    """
    if val in [1, 2]:
        return LOW
    elif val in [3, 4]:
        return MODERATE
    elif val in [5, 6]:
        return HIGH
    else:
        return UNKNOWN

def rescale_1_7(val : int) -> NarrativeAttributeID:
    """
    Utility function to rescale 1-7 to 1-3 (1-3 -> 1, 4-5 -> 2, 6-7 -> 3)

    Args:
        val (int): The value to rescale, expected to be in the range 1-7.

    Returns:
        NarrativeAttributeID: The rescaled value in the range 1-3, or NarrativeAttributeID.UNKNOWN if the input is outside the expected range.
    """
    if val in [1, 2, 3]:
        return LOW
    elif val in [4, 5]:
        return MODERATE
    elif val in [6, 7]:
        return HIGH
    else:
        return UNKNOWN