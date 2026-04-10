"""
Opinion module for Climate-Action-GABM.

Defines the 6 climate policy survey questions, A-G response scale,
numeric mapping, and opinion shift clamping function.
"""
# Metadata
__author__ = ["Ajaykumar Manivannan <ashwamanivannan@gmail.com>", "Andy Turner <agdturner@gmail.com>"]
__version__ = "0.2.0"
__copyright__ = "Copyright (c) 2026 Climate-Action-GABM contributors, University of Leeds"

# Standard library imports
import logging
# Local imports
from gabm.abm.attribute import GABMAttributeID
from gabm.abm.attributes.opinion import OpinionTopicID, OpinionTopic, OpinionValue, OpinionValueMap, Opinion


class ClimatePolicyID(GABMAttributeID):
    """
    Identifier for the 6 climate policies tracked in the simulation.
    Each maps to a specific YouGov survey column.
    """
    def __init__(self, policy_id: int):
        super().__init__(policy_id)


ClimatePolicyID.RENEWABLE_ENERGY = ClimatePolicyID(1)
ClimatePolicyID.BAN_FOSSIL_FUEL = ClimatePolicyID(2)
ClimatePolicyID.BAN_PETROL_CARS = ClimatePolicyID(3)
ClimatePolicyID.GREEN_HOUSING = ClimatePolicyID(4)
ClimatePolicyID.CARBON_TAX = ClimatePolicyID(5)
ClimatePolicyID.CLIMATE_COMPENSATION = ClimatePolicyID(6)

ALL_CLIMATE_POLICIES = [
    ClimatePolicyID.RENEWABLE_ENERGY,
    ClimatePolicyID.BAN_FOSSIL_FUEL,
    ClimatePolicyID.BAN_PETROL_CARS,
    ClimatePolicyID.GREEN_HOUSING,
    ClimatePolicyID.CARBON_TAX,
    ClimatePolicyID.CLIMATE_COMPENSATION,
]

SURVEY_COLUMN_MAP: dict[ClimatePolicyID, str] = {
    ClimatePolicyID.RENEWABLE_ENERGY: "page5posttreatment6_1",
    ClimatePolicyID.BAN_FOSSIL_FUEL: "page5posttreatment6_4",
    ClimatePolicyID.BAN_PETROL_CARS: "page5posttreatment6_5",
    ClimatePolicyID.GREEN_HOUSING: "page5posttreatment6_7",
    ClimatePolicyID.CARBON_TAX: "page5posttreatment6_9",
    ClimatePolicyID.CLIMATE_COMPENSATION: "page5posttreatment6_11",
}

SURVEY_QUESTIONS: dict[ClimatePolicyID, str] = {
    ClimatePolicyID.RENEWABLE_ENERGY: (
        "Please say how much you support or oppose government policies that do the following: "
        "Accelerate the roll-out of renewable energy production, (e.g. more offshore and onshore wind parks)"
    ),
    ClimatePolicyID.BAN_FOSSIL_FUEL: (
        "Please say how much you support or oppose government policies that do the following: "
        "Ban new oil/gas/coal licenses"
    ),
    ClimatePolicyID.BAN_PETROL_CARS: (
        "Please say how much you support or oppose government policies that do the following: "
        "Ban the sale of new petrol cars by no later than 2030"
    ),
    ClimatePolicyID.GREEN_HOUSING: (
        "Please say how much you support or oppose government policies that do the following: "
        "Mandate that all new housing developments should have non-fossil fuel heating systems, "
        "roof-top solar panels, high-level of insulation"
    ),
    ClimatePolicyID.CARBON_TAX: (
        "Please say how much you support or oppose government policies that do the following: "
        "Impose a carbon tax on fossil fuel sale and distribute the tax revenues to the public "
        "(i.e. carbon fee and dividend)"
    ),
    ClimatePolicyID.CLIMATE_COMPENSATION: (
        "Please say how much you support or oppose government policies that do the following: "
        "Compensate people in other countries, who are impacted by climate change"
    ),
}

RESPONSE_SCALE: dict[str, int] = {
    "A": -3, "B": -2, "C": -1, "D": 0, "E": 1, "F": 2, "G": 3,
}

RESPONSE_LABELS: dict[str, str] = {
    "A": "Strongly oppose",
    "B": "Somewhat oppose",
    "C": "Slightly oppose",
    "D": "Neutral",
    "E": "Slightly support",
    "F": "Somewhat support",
    "G": "Strongly support",
}


def clamp_opinion_shift(previous: int, new: int, max_shift: int = 1) -> int:
    """
    Clamp the opinion shift to a maximum magnitude per day.

    Args:
        previous: Previous day's opinion (-3 to +3).
        new: LLM's raw survey response (-3 to +3).
        max_shift: Maximum allowed shift magnitude (default: 1 scale point).

    Returns:
        Clamped opinion value (-3 to +3).

    Raises:
        ValueError: If max_shift is negative.
    """
    if max_shift < 0:
        raise ValueError(f"max_shift must be non-negative, got {max_shift}")
    shift = new - previous
    clamped_shift = max(min(shift, max_shift), -max_shift)
    return previous + clamped_shift


def ordinal_score(llm_numeric: int, real_numeric: int, scale_min: int = -3, scale_max: int = 3) -> float:
    """
    Distance-based accuracy score between an LLM response and the real survey response.

    Returns a float in [0.0, 1.0] where 1.0 is an exact match and 0.0 is the
    maximum possible distance on the scale.

    Args:
        llm_numeric: LLM's numeric opinion value.
        real_numeric: Real survey respondent's numeric value.
        scale_min: Minimum value on the scale (default: -3).
        scale_max: Maximum value on the scale (default: 3).

    Returns:
        Ordinal accuracy score between 0.0 and 1.0.
    """
    max_distance = scale_max - scale_min
    if max_distance == 0:
        return 1.0 if llm_numeric == real_numeric else 0.0
    distance = abs(llm_numeric - real_numeric)
    return 1 - (distance / max_distance)


if __name__ == "__main__":
    logging.info("\n--- Climate-Action-GABM: Opinion Module ---\n")
    logging.info("Defined climate policy IDs, survey questions, response scales, and opinion shift clamping function.") 

    # get a policy and print it
    policy_id = ClimatePolicyID.BAN_PETROL_CARS