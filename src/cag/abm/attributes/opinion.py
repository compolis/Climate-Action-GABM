"""
Opinion module for Climate-Action-GABM.

Defines the 6 climate policy survey questions, A-G response scale,
numeric mapping, and opinion shift clamping function.
"""
# Metadata
__author__ = ["Ajaykumar Manivannan <ashwamanivannan@gmail.com>", "Andy Turner <agdturner@gmail.com>"]
__version__ = "0.7.0"
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

PRO_CLIMATE_INDEX_COLUMN = "ProClimatePolSupp"
PACKAGE_SCOPE = "climate_policy_package"

SURVEY_COLUMN_MAP: dict[ClimatePolicyID, str] = {
    ClimatePolicyID.RENEWABLE_ENERGY: "page5posttreatment6_1",
    ClimatePolicyID.BAN_FOSSIL_FUEL: "page5posttreatment6_4",
    ClimatePolicyID.BAN_PETROL_CARS: "page5posttreatment6_5",
    ClimatePolicyID.GREEN_HOUSING: "page5posttreatment6_7",
    ClimatePolicyID.CARBON_TAX: "page5posttreatment6_9",
    ClimatePolicyID.CLIMATE_COMPENSATION: "page5posttreatment6_11",
}

SURVEY_SHORT_LABELS: dict[ClimatePolicyID, str] = {
    ClimatePolicyID.RENEWABLE_ENERGY: "Accelerate renewable energy roll-out",
    ClimatePolicyID.BAN_FOSSIL_FUEL: "Ban new oil/gas/coal licences",
    ClimatePolicyID.BAN_PETROL_CARS: "Ban new petrol cars by 2030",
    ClimatePolicyID.GREEN_HOUSING: "Green standards for new housing",
    ClimatePolicyID.CARBON_TAX: "Carbon fee and dividend",
    ClimatePolicyID.CLIMATE_COMPENSATION: "Climate compensation for poorer countries",
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


def survey_to_numeric(raw_value: int) -> int:
    """Convert the survey's 1-7 scale to the model's centered -3 to +3 scale."""
    return raw_value - 4


def numeric_to_survey(numeric_value: int) -> int:
    """Convert the model's centered -3 to +3 scale back to the survey's 1-7 scale."""
    return numeric_value + 4


def compute_package_index(numeric_values: list[int], centered: bool = True) -> float:
    """Average six policy responses into a package-level support index.

    Args:
        numeric_values: Climate policy responses on the model's -3..+3 scale.
        centered: When True, return the centered -3..+3 average.
            When False, return the survey-aligned 1..7 average.

    Returns:
        Arithmetic mean of the supplied policy responses.

    Raises:
        ValueError: If no values are supplied.
    """
    if not numeric_values:
        raise ValueError("numeric_values must contain at least one response")
    if centered:
        return sum(numeric_values) / len(numeric_values)
    survey_values = [numeric_to_survey(value) for value in numeric_values]
    return sum(survey_values) / len(survey_values)


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