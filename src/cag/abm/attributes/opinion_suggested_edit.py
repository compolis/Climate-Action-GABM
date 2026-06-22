"""
Opinion module for Climate-Action-GABM.

Defines the 6 climate policy survey questions, A-G response scale,
numeric mapping, and opinion shift clamping function.
"""
# Metadata
__author__ = ["Ajaykumar Manivannan <ashwamanivannan@gmail.com>", "Andy Turner <agdturner@gmail.com>", "Charlie Pilgrim <pilgrimcharlie2@gmail.com>"]
__version__ = "0.7.0"
__copyright__ = "Copyright (c) 2026 Climate-Action-GABM contributors, University of Leeds"


CLIMATE_POLICIES = [
    "renewable_energy",
    "ban_fossil_fuel",
    "ban_petrol_cars",
    "green_housing",
    "carbon_tax",
    "climate_compensation",
]

SURVEY_COLUMN_MAP = {
    "renewable_energy": "page5posttreatment6_1",
    "ban_fossil_fuel": "page5posttreatment6_4",
    "ban_petrol_cars": "page5posttreatment6_5",
    "green_housing": "page5posttreatment6_7",
    "carbon_tax": "page5posttreatment6_9",
    "climate_compensation": "page5posttreatment6_11",
}

SURVEY_QUESTIONS = {
    "renewable_energy": (
        "Please say how much you support or oppose government policies that do the following: "
        "Accelerate the roll-out of renewable energy production, (e.g. more offshore and onshore wind parks)"
        ),
    "ban_fossil_fuel": (
        "Please say how much you support or oppose government policies that do the following: "
        "Ban new oil/gas/coal licenses"
        ),
    "ban_petrol_cars": (
        "Please say how much you support or oppose government policies that do the following: "
        "Ban the sale of new petrol cars by no later than 2030"
        ),
    "green_housing": (
        "Please say how much you support or oppose government policies that do the following: "
        "Mandate that all new housing developments should have non-fossil fuel heating systems, "
        "roof-top solar panels, high-level of insulation"
        ),
    "carbon_tax": (
        "Please say how much you support or oppose government policies that do the following: "
        "Impose a carbon tax on fossil fuel sale and distribute the tax revenues to the public "
        "(i.e. carbon fee and dividend)"
        ),
    "climate_compensation": (
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