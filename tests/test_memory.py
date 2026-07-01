"""Tests for the v2 tiered-memory system (assemble_context + Day-0 anchor
+ unified daily summaries + target-scoped own-reasoning + today-so-far)."""

import os
import sys
from unittest import mock

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from cag.abm.agent import SurveyedCitizen, NUMERIC_TO_LETTER
from cag.abm.attributes.opinion import (
    ClimatePolicyID,
    PACKAGE_SCOPE,
    SURVEY_SHORT_LABELS,
)
from cag.abm.config.memory import resolve_memory_config


# ===================================================================
# Helpers
# ===================================================================

def _make_citizen():
    env = mock.MagicMock()
    citizen = SurveyedCitizen(agent_id=1, environment=env, year_of_birth=1990)
    citizen.get_persona = mock.MagicMock(return_value="I am a 36 year old teacher.")
    citizen.get_narrative = mock.MagicMock(return_value="I care about fairness.")
    return citizen


def _add_reflections(citizen, day, n=2, phase="P-A", policy_id=ClimatePolicyID.CARBON_TAX):
    for i in range(n):
        citizen.reflections.append({
            "day": day,
            "phase": phase,
            "policy_id": policy_id,
            "text": f"Reflection {i} from day {day}.",
            "messages_received": ["msg"],
        })


# ===================================================================
# Init
# ===================================================================

class TestMemoryInit:

    def test_daily_summaries_empty(self):
        c = _make_citizen()
        assert c.daily_summaries == {}


# ===================================================================
# assemble_context — v2 architecture
# ===================================================================

class TestAssembleContext:

    def test_day0_persona_only_when_no_other_data(self):
        c = _make_citizen()
        ctx = c.assemble_context(day=0)
        assert "36 year old teacher" in ctx
        assert "reflections" not in ctx.lower()

    def test_no_remember_who_you_are_trailing_line(self):
        c = _make_citizen()
        _add_reflections(c, day=3)
        ctx = c.assemble_context(day=3, policy_id=ClimatePolicyID.CARBON_TAX)
        assert "Remember who you are" not in ctx

    def test_day1_includes_recent_reflections(self):
        c = _make_citizen()
        _add_reflections(c, day=1)
        ctx = c.assemble_context(day=1, policy_id=ClimatePolicyID.CARBON_TAX)
        assert "Reflection 0 from day 1" in ctx
        assert "Reflection 1 from day 1" in ctx

    def test_recent_reflection_bullet_has_day_prefix_and_no_phase_tag(self):
        c = _make_citizen()
        _add_reflections(c, day=2, n=1, phase="P-A")
        _add_reflections(c, day=2, n=1, phase="P-B")
        ctx = c.assemble_context(day=2, policy_id=ClimatePolicyID.CARBON_TAX)
        # New format: "- Day {d}: {text}". No "(P-A)", "(P-B)", "(C)" tags.
        assert "- Day 2:" in ctx
        assert "(P-A)" not in ctx
        assert "(P-B)" not in ctx
        assert "(C)" not in ctx

    def test_day1_includes_day0_reflections_as_recent(self):
        c = _make_citizen()
        _add_reflections(c, day=0, n=1)
        _add_reflections(c, day=1, n=1)
        ctx = c.assemble_context(day=1, policy_id=ClimatePolicyID.CARBON_TAX)
        assert "from day 1" in ctx
        assert "from day 0" in ctx

    def test_daily_summaries_included_for_older_days(self):
        c = _make_citizen()
        pid = ClimatePolicyID.CARBON_TAX
        c.daily_summaries[(2, pid)] = "Agent became more supportive on day 2."
        c.daily_summaries[(3, pid)] = "Agent reconsidered on day 3."
        _add_reflections(c, day=5)
        ctx = c.assemble_context(day=5, policy_id=pid)
        assert "became more supportive on day 2" in ctx
        assert "reconsidered on day 3" in ctx

    def test_daily_summaries_excluded_for_recent_days(self):
        c = _make_citizen()
        pid = ClimatePolicyID.CARBON_TAX
        c.daily_summaries[(4, pid)] = "Should not appear as summary."
        _add_reflections(c, day=5)
        ctx = c.assemble_context(day=5, policy_id=pid)
        # Day 4 is d-1 so it would appear in vivid reflections, not summaries.
        assert "Should not appear as summary" not in ctx


# ===================================================================
# Day-0 anchor section (target-scoped)
# ===================================================================

class TestDay0AnchorSection:

    def test_anchor_section_from_day0_rationale(self):
        c = _make_citizen()
        pid = ClimatePolicyID.CARBON_TAX
        c.survey_reasoning[pid] = [(0, "Polluters should pay full stop.")]
        ctx = c.assemble_context(day=2, policy_id=pid, target_policy_id=pid)
        assert "Original prior position on" in ctx
        assert "Polluters should pay" in ctx

    def test_anchor_target_scoped_to_target_policy(self):
        c = _make_citizen()
        pid_a = ClimatePolicyID.CARBON_TAX
        pid_b = ClimatePolicyID.RENEWABLE_ENERGY
        c.survey_reasoning[pid_a] = [(0, "Carbon-tax Day-0 rationale.")]
        c.survey_reasoning[pid_b] = [(0, "Renewables Day-0 rationale.")]
        ctx = c.assemble_context(day=2, policy_id=PACKAGE_SCOPE, target_policy_id=pid_a)
        assert "Carbon-tax Day-0 rationale." in ctx
        assert "Renewables Day-0 rationale." not in ctx

    def test_package_anchor_lists_all_policies_when_no_single_target(self):
        # Package-scoped context with no single target (e.g. package-mode peer
        # messaging / reflection) carries every policy's Day-0 anchor so the
        # agent keeps the same identity tether it sees at survey time.
        c = _make_citizen()
        pid_a = ClimatePolicyID.CARBON_TAX
        pid_b = ClimatePolicyID.RENEWABLE_ENERGY
        c.survey_reasoning[pid_a] = [(0, "Carbon-tax Day-0 rationale.")]
        c.survey_reasoning[pid_b] = [(0, "Renewables Day-0 rationale.")]
        ctx = c.assemble_context(day=2, policy_id=PACKAGE_SCOPE, target_policy_id=PACKAGE_SCOPE)
        assert "Original prior positions:" in ctx
        assert "Carbon-tax Day-0 rationale." in ctx
        assert "Renewables Day-0 rationale." in ctx

    def test_package_anchor_present_on_peer_reflection_path(self):
        # The peer/reflection call path passes target_policy_id=None.
        c = _make_citizen()
        pid_a = ClimatePolicyID.CARBON_TAX
        pid_b = ClimatePolicyID.RENEWABLE_ENERGY
        c.survey_reasoning[pid_a] = [(0, "Carbon-tax Day-0 rationale.")]
        c.survey_reasoning[pid_b] = [(0, "Renewables Day-0 rationale.")]
        ctx = c.assemble_context(day=2, policy_id=PACKAGE_SCOPE, target_policy_id=None)
        assert "Original prior positions:" in ctx
        assert "Carbon-tax Day-0 rationale." in ctx
        assert "Renewables Day-0 rationale." in ctx

    def test_anchor_omitted_when_no_data(self):
        c = _make_citizen()
        _add_reflections(c, day=2)
        ctx = c.assemble_context(day=2, policy_id=ClimatePolicyID.CARBON_TAX)
        assert "Original prior position on" not in ctx


# ===================================================================
# Considered-position section (target-scoped own reasoning, d-1 + d)
# ===================================================================

class TestRecentOwnReasoning:

    def test_target_scoped_to_target_policy(self):
        c = _make_citizen()
        pid_a = ClimatePolicyID.CARBON_TAX
        pid_b = ClimatePolicyID.RENEWABLE_ENERGY
        c.survey_reasoning[pid_a] = [(1, "Carbon-tax day-1 reasoning.")]
        c.survey_reasoning[pid_b] = [(1, "Renewables day-1 reasoning.")]
        ctx = c.assemble_context(day=2, policy_id=PACKAGE_SCOPE, target_policy_id=pid_a)
        assert "Your considered position in recent days:" in ctx
        assert "Carbon-tax day-1 reasoning." in ctx
        assert "Renewables day-1 reasoning." not in ctx

    def test_only_days_dm1_and_d(self):
        c = _make_citizen()
        pid = ClimatePolicyID.CARBON_TAX
        c.survey_reasoning[pid] = [
            (1, "Day-1 reasoning."),
            (3, "Day-3 reasoning."),
            (4, "Day-4 reasoning."),
            (5, "Day-5 reasoning."),
        ]
        ctx = c.assemble_context(day=5, policy_id=PACKAGE_SCOPE, target_policy_id=pid)
        block = ctx.split("Your considered position in recent days:")[1]
        assert "Day-4 reasoning." in block
        assert "Day-5 reasoning." in block
        assert "Day-3 reasoning." not in block
        assert "Day-1 reasoning." not in block

    def test_day0_entries_excluded(self):
        c = _make_citizen()
        pid = ClimatePolicyID.CARBON_TAX
        c.survey_reasoning[pid] = [(0, "Day-0 anchor text."), (1, "Day-1 text.")]
        ctx = c.assemble_context(day=1, policy_id=PACKAGE_SCOPE, target_policy_id=pid)
        block = ctx.split("Your considered position in recent days:")[1]
        # Day-0 lives in the anchor section, not this one.
        assert "Day-0 anchor text." not in block
        assert "Day-1 text." in block

    def test_omitted_at_day0(self):
        c = _make_citizen()
        pid = ClimatePolicyID.CARBON_TAX
        c.survey_reasoning[pid] = [(0, "Day-0 text.")]
        ctx = c.assemble_context(day=0, policy_id=PACKAGE_SCOPE, target_policy_id=pid)
        assert "Your considered position in recent days:" not in ctx

    def test_omitted_when_target_is_package_scope(self):
        c = _make_citizen()
        pid = ClimatePolicyID.CARBON_TAX
        c.survey_reasoning[pid] = [(1, "Day-1 text.")]
        ctx = c.assemble_context(day=2, policy_id=PACKAGE_SCOPE, target_policy_id=PACKAGE_SCOPE)
        assert "Your considered position in recent days:" not in ctx


# ===================================================================
# Today-so-far section (package mode within-day, excludes target)
# ===================================================================

class TestTodaySoFar:

    def test_fires_in_package_mode_for_other_today_answered_policies(self):
        c = _make_citizen()
        pid_target = ClimatePolicyID.CARBON_TAX
        pid_other = ClimatePolicyID.RENEWABLE_ENERGY
        c.opinion_history[pid_other] = [(0, 1), (1, 2)]
        c.survey_reasoning[pid_other] = [(1, "Today renewables reasoning.")]
        ctx = c.assemble_context(day=1, policy_id=PACKAGE_SCOPE, target_policy_id=pid_target)
        assert "Your answers so far in today's survey:" in ctx
        block = ctx.split("Your answers so far in today's survey:")[1]
        assert SURVEY_SHORT_LABELS[pid_other] in block
        assert "Today renewables reasoning." in block

    def test_excludes_target_policy(self):
        c = _make_citizen()
        pid_target = ClimatePolicyID.CARBON_TAX
        pid_other = ClimatePolicyID.RENEWABLE_ENERGY
        c.opinion_history[pid_target] = [(1, 2)]  # target answered today (shouldn't be possible mid-flight)
        c.opinion_history[pid_other] = [(1, 2)]
        ctx = c.assemble_context(day=1, policy_id=PACKAGE_SCOPE, target_policy_id=pid_target)
        block = ctx.split("Your answers so far in today's survey:")[1]
        assert SURVEY_SHORT_LABELS[pid_target] not in block
        assert SURVEY_SHORT_LABELS[pid_other] in block

    def test_excludes_other_policies_not_answered_today(self):
        c = _make_citizen()
        pid_target = ClimatePolicyID.CARBON_TAX
        pid_other = ClimatePolicyID.RENEWABLE_ENERGY
        c.opinion_history[pid_other] = [(0, 1)]  # answered Day 0 only
        ctx = c.assemble_context(day=2, policy_id=PACKAGE_SCOPE, target_policy_id=pid_target)
        assert "Your answers so far in today's survey:" not in ctx

    def test_does_not_fire_in_single_policy_mode(self):
        c = _make_citizen()
        pid = ClimatePolicyID.CARBON_TAX
        c.opinion_history[pid] = [(1, 1)]
        # Single-policy mode: policy_id != PACKAGE_SCOPE → section never fires.
        ctx = c.assemble_context(day=1, policy_id=pid, target_policy_id=pid)
        assert "Your answers so far in today's survey:" not in ctx

    def test_includes_why_clause_when_reasoning_available(self):
        c = _make_citizen()
        pid_target = ClimatePolicyID.CARBON_TAX
        pid_other = ClimatePolicyID.RENEWABLE_ENERGY
        c.opinion_history[pid_other] = [(1, 3)]
        c.survey_reasoning[pid_other] = [(1, "Because clean energy is essential.")]
        ctx = c.assemble_context(day=1, policy_id=PACKAGE_SCOPE, target_policy_id=pid_target)
        assert "(Why: Because clean energy is essential.)" in ctx


# ===================================================================
# Section order
# ===================================================================

class TestSectionOrder:

    def test_full_package_mode_section_order(self):
        c = _make_citizen()
        pid_target = ClimatePolicyID.CARBON_TAX
        pid_other = ClimatePolicyID.RENEWABLE_ENERGY
        # Day-0 anchor: verbatim from survey_reasoning at day 0.
        # Daily summary (older than d-1).
        c.daily_summaries[(1, PACKAGE_SCOPE)] = "Day-1 summary."
        # Vivid reflection at d-1 = 2 and d = 3 (package-scoped so it isn't
        # filtered out under policy_id=PACKAGE_SCOPE).
        c.reflections.append({"day": 2, "phase": "P-A", "policy_id": PACKAGE_SCOPE,
                              "text": "Day-2 reflection."})
        c.reflections.append({"day": 3, "phase": "C", "policy_id": PACKAGE_SCOPE,
                              "text": "Day-3 reflection."})
        # Own reasoning at d=0 (anchor), d-1, d for target.
        c.survey_reasoning[pid_target] = [(0, "Target Day-0 rationale."),
                                           (2, "Day-2 target reasoning."),
                                           (3, "Day-3 target reasoning.")]
        # Today's answer for another policy.
        c.opinion_history[pid_other] = [(3, 2)]
        c.survey_reasoning[pid_other] = [(3, "Why renewables.")]

        ctx = c.assemble_context(day=3, policy_id=PACKAGE_SCOPE, target_policy_id=pid_target)
        headers = [
            "Original prior position on",
            "Summary of recent days:",
            "Recent reflections following received messages:",
            "Your considered position in recent days:",
            "Your answers so far in today's survey:",
        ]
        positions = [ctx.find(h) for h in headers]
        assert all(p >= 0 for p in positions), f"missing header: {positions}"
        assert positions == sorted(positions), \
            f"sections out of order: {dict(zip(headers, positions))}"


# ===================================================================
# compress_memories
# ===================================================================

class TestCompressMemories:

    @mock.patch("cag.abm.agent.send_chat", return_value="A concise summary.")
    def test_returns_summary(self, mock_send):
        c = _make_citizen()
        result = c.compress_memories("Some long text about reflections.")
        assert result == "A concise summary."

    @mock.patch("cag.abm.agent.send_chat", return_value="Summary.")
    def test_sends_text_to_llm(self, mock_send):
        c = _make_citizen()
        c.compress_memories("reflection text here")
        user_prompt = mock_send.call_args[0][1]
        assert "reflection text here" in user_prompt


# ===================================================================
# compress_daily_memory (unified: reflections + own reasoning)
# ===================================================================

class TestCompressDailyMemory:

    @mock.patch("cag.abm.agent.send_chat", return_value="Agent shifted toward support.")
    def test_stores_summary(self, mock_send):
        c = _make_citizen()
        pid = ClimatePolicyID.CARBON_TAX
        _add_reflections(c, day=3, n=3)
        summary = c.compress_daily_memory(3, pid)
        assert c.daily_summaries[(3, pid)] == summary
        assert "shifted toward support" in summary

    @mock.patch("cag.abm.agent.send_chat", return_value="Summary.")
    def test_sends_reflections_to_llm(self, mock_send):
        c = _make_citizen()
        pid = ClimatePolicyID.CARBON_TAX
        _add_reflections(c, day=2, n=2)
        c.compress_daily_memory(2, pid)
        user_prompt = mock_send.call_args[0][1]
        assert "Reflection 0 from day 2" in user_prompt
        assert "Reflection 1 from day 2" in user_prompt

    @mock.patch("cag.abm.agent.send_chat", return_value="Summary.")
    def test_package_mode_includes_all_policies_reflections(self, mock_send):
        c = _make_citizen()
        _add_reflections(c, day=2, n=1, policy_id=PACKAGE_SCOPE)
        _add_reflections(c, day=2, n=1, policy_id=ClimatePolicyID.CARBON_TAX)
        _add_reflections(c, day=2, n=1, policy_id=ClimatePolicyID.RENEWABLE_ENERGY)
        c.compress_daily_memory(2, PACKAGE_SCOPE)
        user_prompt = mock_send.call_args[0][1]
        # All three day-2 reflections should be in the prompt.
        assert user_prompt.count("Reflection 0 from day 2") == 3

    @mock.patch("cag.abm.agent.send_chat", return_value="Summary.")
    def test_package_mode_includes_own_reasoning(self, mock_send):
        c = _make_citizen()
        pid_a = ClimatePolicyID.CARBON_TAX
        pid_b = ClimatePolicyID.RENEWABLE_ENERGY
        c.survey_reasoning[pid_a] = [(2, "Carbon-tax reasoning today.")]
        c.survey_reasoning[pid_b] = [(2, "Renewables reasoning today.")]
        _add_reflections(c, day=2, n=1, policy_id=PACKAGE_SCOPE)
        c.compress_daily_memory(2, PACKAGE_SCOPE)
        user_prompt = mock_send.call_args[0][1]
        assert "Carbon-tax reasoning today." in user_prompt
        assert "Renewables reasoning today." in user_prompt
        assert "My own survey reasoning today:" in user_prompt

    @mock.patch("cag.abm.agent.send_chat", return_value="Summary.")
    def test_single_policy_includes_own_reasoning_for_that_policy_only(self, mock_send):
        c = _make_citizen()
        pid = ClimatePolicyID.CARBON_TAX
        other = ClimatePolicyID.RENEWABLE_ENERGY
        c.survey_reasoning[pid] = [(2, "Target reasoning.")]
        c.survey_reasoning[other] = [(2, "Other policy reasoning.")]
        _add_reflections(c, day=2, n=1, policy_id=pid)
        c.compress_daily_memory(2, pid)
        user_prompt = mock_send.call_args[0][1]
        assert "Target reasoning." in user_prompt
        assert "Other policy reasoning." not in user_prompt

    def test_returns_empty_if_no_reflections_or_reasoning(self):
        c = _make_citizen()
        pid = ClimatePolicyID.CARBON_TAX
        result = c.compress_daily_memory(5, pid)
        assert result == ""
        assert (5, pid) not in c.daily_summaries


# ===================================================================
# manage_memory (now called BEFORE EOD survey)
# ===================================================================

class TestManageMemory:

    @mock.patch("cag.abm.agent.send_chat", return_value="Compressed.")
    def test_compresses_day_minus_2(self, mock_send):
        c = _make_citizen()
        pid = ClimatePolicyID.CARBON_TAX
        _add_reflections(c, day=1, n=2)
        _add_reflections(c, day=2, n=2)
        _add_reflections(c, day=3, n=2)
        c.manage_memory(day=3, policy_id=pid)
        assert (1, pid) in c.daily_summaries  # day 3-2 = 1

    @mock.patch("cag.abm.agent.send_chat", return_value="Compressed.")
    def test_does_not_compress_recent_days(self, mock_send):
        c = _make_citizen()
        pid = ClimatePolicyID.CARBON_TAX
        _add_reflections(c, day=3, n=2)
        c.manage_memory(day=3, policy_id=pid)
        assert (3, pid) not in c.daily_summaries
        assert (2, pid) not in c.daily_summaries

    def test_does_not_compress_on_early_days(self):
        c = _make_citizen()
        pid = ClimatePolicyID.CARBON_TAX
        _add_reflections(c, day=1, n=2)
        c.manage_memory(day=1, policy_id=pid)
        assert len(c.daily_summaries) == 0

    @mock.patch("cag.abm.agent.send_chat", return_value="Compressed.")
    def test_does_not_recompress_existing_summary(self, mock_send):
        c = _make_citizen()
        pid = ClimatePolicyID.CARBON_TAX
        c.daily_summaries[(3, pid)] = "Already compressed."
        _add_reflections(c, day=3, n=2)
        _add_reflections(c, day=5, n=2)
        c.manage_memory(day=5, policy_id=pid)
        assert c.daily_summaries[(3, pid)] == "Already compressed."
        mock_send.assert_not_called()


# ===================================================================
# Deterministic EOD survey shuffle (sim-level)
# ===================================================================

class TestEodSurveyOrderShuffle:

    def test_same_seed_same_day_same_order(self):
        import random
        from cag.abm.attributes.opinion import ALL_CLIMATE_POLICIES
        policies = list(ALL_CLIMATE_POLICIES)
        a = list(policies); random.Random(42 * 1000 + 1).shuffle(a)
        b = list(policies); random.Random(42 * 1000 + 1).shuffle(b)
        assert a == b

    def test_different_days_different_orders(self):
        import random
        from cag.abm.attributes.opinion import ALL_CLIMATE_POLICIES
        policies = list(ALL_CLIMATE_POLICIES)
        orders = []
        for day in range(1, 6):
            order = list(policies)
            random.Random(42 * 1000 + day).shuffle(order)
            orders.append(tuple(order))
        # At least most pairs should differ (6! = 720; collision probability tiny).
        assert len(set(orders)) >= 4

    def test_shuffled_set_equals_input_set(self):
        import random
        from cag.abm.attributes.opinion import ALL_CLIMATE_POLICIES
        policies = list(ALL_CLIMATE_POLICIES)
        shuffled = list(policies)
        random.Random(42 * 1000 + 1).shuffle(shuffled)
        assert set(shuffled) == set(policies)
        assert len(shuffled) == len(policies)


# ===================================================================
# NUMERIC_TO_LETTER
# ===================================================================

class TestNumericToLetter:

    def test_all_values_mapped(self):
        for num in range(-3, 4):
            assert num in NUMERIC_TO_LETTER

    def test_matches_response_scale_inverse(self):
        from cag.abm.attributes.opinion import RESPONSE_SCALE
        for letter, num in RESPONSE_SCALE.items():
            assert NUMERIC_TO_LETTER[num] == letter


# ===================================================================
# Configurable memory: section toggles, verbatim window, per-stage
# ===================================================================

class TestMemoryConfigToggles:
    """Non-default memory configs. The default is exercised by every other
    test in this file (that IS the golden regression)."""

    def test_persona_disabled(self):
        c = _make_citizen()
        c.memory_cfg = resolve_memory_config("persona_only")
        c.memory_cfg = resolve_memory_config({"persona": {"enabled": False}})
        ctx = c.assemble_context(day=0)
        assert "36 year old teacher" not in ctx

    def test_day0_anchor_disabled(self):
        c = _make_citizen()
        pid = ClimatePolicyID.CARBON_TAX
        c.survey_reasoning[pid] = [(0, "Polluters should pay.")]
        c.memory_cfg = resolve_memory_config("no_anchor")
        ctx = c.assemble_context(day=2, policy_id=pid, target_policy_id=pid)
        assert "Original prior position on" not in ctx
        assert "Polluters should pay." not in ctx

    def test_anchor_ttl_retires_after_ttl_days(self):
        c = _make_citizen()
        pid = ClimatePolicyID.CARBON_TAX
        c.survey_reasoning[pid] = [(0, "Polluters should pay.")]
        c.memory_cfg = resolve_memory_config("anchor_ttl2")  # ttl_days=2
        # Present up to and including day 2.
        assert "Polluters should pay." in c.assemble_context(
            day=2, policy_id=pid, target_policy_id=pid)
        # Retired from day 3 onward.
        assert "Polluters should pay." not in c.assemble_context(
            day=3, policy_id=pid, target_policy_id=pid)

    def test_own_reasoning_disabled(self):
        c = _make_citizen()
        pid = ClimatePolicyID.CARBON_TAX
        c.survey_reasoning[pid] = [(1, "Day-1 reasoning."), (2, "Day-2 reasoning.")]
        c.memory_cfg = resolve_memory_config("no_own_reasoning")
        ctx = c.assemble_context(day=2, policy_id=PACKAGE_SCOPE, target_policy_id=pid)
        assert "Your considered position in recent days:" not in ctx

    def test_window_one_keeps_only_today(self):
        c = _make_citizen()
        pid = ClimatePolicyID.CARBON_TAX
        _add_reflections(c, day=3, n=1, policy_id=pid)
        _add_reflections(c, day=4, n=1, policy_id=pid)
        _add_reflections(c, day=5, n=1, policy_id=pid)
        c.memory_cfg = resolve_memory_config("short_memory")  # window=1
        ctx = c.assemble_context(day=5, policy_id=pid)
        assert "from day 5" in ctx
        assert "from day 4" not in ctx
        assert "from day 3" not in ctx

    def test_window_three_keeps_three_days(self):
        c = _make_citizen()
        pid = ClimatePolicyID.CARBON_TAX
        _add_reflections(c, day=2, n=1, policy_id=pid)
        _add_reflections(c, day=3, n=1, policy_id=pid)
        _add_reflections(c, day=4, n=1, policy_id=pid)
        _add_reflections(c, day=5, n=1, policy_id=pid)
        c.memory_cfg = resolve_memory_config("wide_memory")  # window=4
        ctx = c.assemble_context(day=5, policy_id=pid)
        for d in (2, 3, 4, 5):
            assert f"from day {d}" in ctx

    def test_window_shifts_summary_boundary(self):
        c = _make_citizen()
        pid = ClimatePolicyID.CARBON_TAX
        c.daily_summaries[(3, pid)] = "Day-3 summary text."
        _add_reflections(c, day=5, n=1, policy_id=pid)
        # Default window=2 → day 3 is older than {4,5}, so summarised & shown.
        c.memory_cfg = resolve_memory_config(None)
        assert "Day-3 summary text." in c.assemble_context(day=5, policy_id=pid)
        # Window=3 → verbatim window {3,4,5} covers day 3, so its summary is
        # NOT shown (it would be a verbatim day instead).
        c.memory_cfg = resolve_memory_config({"verbatim_window_days": 3})
        assert "Day-3 summary text." not in c.assemble_context(day=5, policy_id=pid)

    @mock.patch("cag.abm.agent.send_chat", return_value="Compressed.")
    def test_manage_memory_respects_window_three(self, mock_send):
        c = _make_citizen()
        pid = ClimatePolicyID.CARBON_TAX
        for d in range(1, 6):
            _add_reflections(c, day=d, n=1, policy_id=pid)
        c.memory_cfg = resolve_memory_config({"verbatim_window_days": 3})
        c.manage_memory(day=5, policy_id=pid)
        # Compresses day 5-3 = 2; leaves 3,4,5 verbatim.
        assert (2, pid) in c.daily_summaries
        assert (3, pid) not in c.daily_summaries

    @mock.patch("cag.abm.agent.send_chat", return_value="Compressed.")
    def test_no_compression_window_never_compresses(self, mock_send):
        c = _make_citizen()
        pid = ClimatePolicyID.CARBON_TAX
        for d in range(1, 8):
            _add_reflections(c, day=d, n=1, policy_id=pid)
        c.memory_cfg = resolve_memory_config("no_compression")  # window=None
        c.manage_memory(day=7, policy_id=pid)
        assert c.daily_summaries == {}
        mock_send.assert_not_called()

    def test_opinion_trajectory_off_by_default(self):
        c = _make_citizen()
        pid = ClimatePolicyID.CARBON_TAX
        c.opinion_history[pid] = [(0, 1), (1, 2), (2, 3)]
        ctx = c.assemble_context(day=2, policy_id=pid, target_policy_id=pid)
        assert "Your recorded stance over time" not in ctx

    def test_opinion_trajectory_when_enabled(self):
        c = _make_citizen()
        pid = ClimatePolicyID.CARBON_TAX
        c.opinion_history[pid] = [(0, 1), (1, 2), (2, 3)]
        c.memory_cfg = resolve_memory_config({"opinion_trajectory": {"enabled": True}})
        ctx = c.assemble_context(day=2, policy_id=pid, target_policy_id=pid)
        assert "Your recorded stance over time" in ctx
        assert "Day 0" in ctx and "Day 1" in ctx and "Day 2" in ctx

    def test_per_stage_override_survey_only(self):
        c = _make_citizen()
        pid = ClimatePolicyID.CARBON_TAX
        c.survey_reasoning[pid] = [(1, "Day-1 reasoning."), (2, "Day-2 reasoning.")]
        # Disable own_reasoning only in the survey stage.
        c.memory_cfg = resolve_memory_config(
            {"stages": {"survey": {"own_reasoning": {"enabled": False}}}}
        )
        survey_ctx = c.assemble_context(
            day=2, policy_id=PACKAGE_SCOPE, target_policy_id=pid, stage="survey")
        reflect_ctx = c.assemble_context(
            day=2, policy_id=PACKAGE_SCOPE, target_policy_id=pid, stage="reflection")
        assert "Your considered position in recent days:" not in survey_ctx
        assert "Your considered position in recent days:" in reflect_ctx

