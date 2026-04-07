"""
Tests for the climate policy opinion system (Issue 1).
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from cag.abm.attributes.opinion import (
    ClimatePolicyID,
    ALL_CLIMATE_POLICIES,
    SURVEY_QUESTIONS,
    RESPONSE_SCALE,
    RESPONSE_LABELS,
    SURVEY_COLUMN_MAP,
    clamp_opinion_shift,
)


class TestClimatePolicyID(unittest.TestCase):

    def test_has_six_policies(self):
        self.assertEqual(len(ALL_CLIMATE_POLICIES), 6)

    def test_members_are_distinct(self):
        ids = [p.id for p in ALL_CLIMATE_POLICIES]
        self.assertEqual(len(set(ids)), 6)

    def test_each_policy_in_survey_questions(self):
        for policy in ALL_CLIMATE_POLICIES:
            self.assertIn(policy, SURVEY_QUESTIONS)

    def test_each_policy_in_column_map(self):
        for policy in ALL_CLIMATE_POLICIES:
            self.assertIn(policy, SURVEY_COLUMN_MAP)


class TestSurveyQuestions(unittest.TestCase):

    def test_renewable_energy_text(self):
        text = SURVEY_QUESTIONS[ClimatePolicyID.RENEWABLE_ENERGY]
        self.assertIn("renewable energy", text.lower())

    def test_all_questions_start_with_preamble(self):
        preamble = "Please say how much you support or oppose"
        for policy, text in SURVEY_QUESTIONS.items():
            self.assertTrue(text.startswith(preamble), f"{policy} missing preamble")


class TestResponseScale(unittest.TestCase):

    def test_a_maps_to_minus_3(self):
        self.assertEqual(RESPONSE_SCALE["A"], -3)

    def test_d_maps_to_zero(self):
        self.assertEqual(RESPONSE_SCALE["D"], 0)

    def test_g_maps_to_plus_3(self):
        self.assertEqual(RESPONSE_SCALE["G"], 3)

    def test_has_seven_entries(self):
        self.assertEqual(len(RESPONSE_SCALE), 7)

    def test_values_are_sequential(self):
        expected = list(range(-3, 4))
        actual = [RESPONSE_SCALE[chr(ord("A") + i)] for i in range(7)]
        self.assertEqual(actual, expected)


class TestResponseLabels(unittest.TestCase):

    def test_has_seven_entries(self):
        self.assertEqual(len(RESPONSE_LABELS), 7)

    def test_a_is_strongly_oppose(self):
        self.assertEqual(RESPONSE_LABELS["A"], "Strongly oppose")

    def test_g_is_strongly_support(self):
        self.assertEqual(RESPONSE_LABELS["G"], "Strongly support")


class TestSurveyColumnMap(unittest.TestCase):

    def test_renewable_energy_column(self):
        self.assertEqual(SURVEY_COLUMN_MAP[ClimatePolicyID.RENEWABLE_ENERGY], "page5posttreatment6_1")

    def test_climate_compensation_column(self):
        self.assertEqual(SURVEY_COLUMN_MAP[ClimatePolicyID.CLIMATE_COMPENSATION], "page5posttreatment6_11")

    def test_all_columns_start_with_prefix(self):
        for col in SURVEY_COLUMN_MAP.values():
            self.assertTrue(col.startswith("page5posttreatment6_"))


class TestClampOpinionShift(unittest.TestCase):

    def test_positive_shift_clamped(self):
        # Raw shift +3, clamped to +1: -1 + 1 = 0
        self.assertEqual(clamp_opinion_shift(-1, 2, max_shift=1), 0)

    def test_negative_shift_clamped(self):
        # Raw shift -3, clamped to -1: 1 - 1 = 0
        self.assertEqual(clamp_opinion_shift(1, -2, max_shift=1), 0)

    def test_no_change(self):
        self.assertEqual(clamp_opinion_shift(2, 2, max_shift=1), 2)

    def test_zero_shift(self):
        self.assertEqual(clamp_opinion_shift(0, 0), 0)

    def test_at_boundary_no_shift(self):
        self.assertEqual(clamp_opinion_shift(-3, -3), -3)

    def test_extreme_shift_clamped(self):
        # -3 to +3 is shift of 6, clamped to 1: -3 + 1 = -2
        self.assertEqual(clamp_opinion_shift(-3, 3, max_shift=1), -2)

    def test_shift_within_limit_not_clamped(self):
        # Shift of exactly 1, not clamped
        self.assertEqual(clamp_opinion_shift(0, 1, max_shift=1), 1)

    def test_custom_max_shift(self):
        # Shift of 3 with max_shift=2: clamped to 2: -1 + 2 = 1
        self.assertEqual(clamp_opinion_shift(-1, 2, max_shift=2), 1)

    def test_negative_max_shift_raises(self):
        with self.assertRaises(ValueError):
            clamp_opinion_shift(0, 1, max_shift=-1)


if __name__ == "__main__":
    unittest.main()
