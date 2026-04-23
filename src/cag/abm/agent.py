# NOTE: This import must be the very first non-empty line in the file (even before docstrings)
# due to Python syntax rules for __future__ imports.
from __future__ import annotations
"""
Agent module for Climate-Action-GABM.
"""
__author__ = ["Andy Turner <agdturner@gmail.com>","Ajaykumar Manivannan <ashwamanivannan@gmail.com>", "Charlie Pilgrim <pilgrimcharlie2@gmail.com>"]
__version__ = "0.3.0"
__copyright__ = "Copyright (c) 2026 Climate-Action-GABM contributors, University of Leeds"

from datetime import date

from cag.io.llm import send_chat, parse_letter_response
from cag.abm.attributes.opinion import (
    PACKAGE_SCOPE,
    PRO_CLIMATE_INDEX_COLUMN,
    RESPONSE_LABELS,
    RESPONSE_SCALE,
    SURVEY_COLUMN_MAP,
    SURVEY_QUESTIONS,
    survey_to_numeric,
)

NUMERIC_TO_LETTER = {-3: "A", -2: "B", -1: "C", 0: "D", 1: "E", 2: "F", 3: "G"}

# ── Debias prompt templates (Condition B from NB 13) ────────────────────────

_ANTI_SYCOPHANCY = (
    "Your task is to faithfully simulate how this specific person would respond, "
    "NOT to give the 'correct' or socially desirable answer. "
    "Real people with this profile hold a WIDE range of views on climate policy, "
    "including strong opposition. That is expected and acceptable."
)

_DEBIAS_STEP1_TEMPLATE = (
    "{anti_sycophancy}\n\n"
    "Given this person's demographic profile, political history, and psychological values, "
    "what factors would shape their view on the following policy?\n\n"
    "{policy_question}\n\n"
    "Consider factors that might lead them to SUPPORT this policy AND factors that might "
    "lead them to OPPOSE it. Think about their voting history, their values, their life "
    "circumstances, and how these might interact.\n\n"
    "Provide your reasoning in 2-3 sentences."
)

_DEBIAS_STEP2_TEMPLATE = (
    "Based on the reasoning above, how would this person respond to the following "
    "survey question?\n\n"
    "{policy_question}\n\n"
    "{response_options}\n\n"
    "Respond with a single letter A-G."
)


def _format_policy_package(policy_ids) -> str:
    return "\n".join(
        f"- {SURVEY_QUESTIONS[policy_id]}" for policy_id in policy_ids
    )

class SurveyedCitizen():
    
    def __init__(
        self,
        agent_id,
        original_survey_data = None,
        environment = None,
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
        self.original_survey_data = original_survey_data
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
        self.political_exposure = "neither"
        self.network_neighbors = []
        self.reflections = []
        self.daily_summaries = {}   # {(day, policy_id): summary_text}
        self.survey_reasoning = {}  # {policy_id: [(day, reasoning_text)]}

    def __str__(self):
        """
        Returns a string representation of the SurveyedCitizen agent.
        """
        sn = self.environment
        r = f"year_of_birth={self.year_of_birth}, gender={sn.gender_map.get(self.gender_id).description}, opinions={self.opinions}"
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

    def get_persona(self) -> str:
        """
        Returns a persona based on attributes.

        Returns:
            A string representing the persona.
        """
        sn = self.environment
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
    
    def get_system_prompt(self, day=0, policy_id=None) -> str:
        """Delegates to assemble_context."""
        return self.assemble_context(day, policy_id=policy_id)

    def assemble_context(self, day=0, policy_id=None) -> str:
        """Build the full LLM context for a given day.

        Structure:
        1. Persona + narrative (always)
        2. Daily summaries (older than d-1)
        3. Full reflections (days d-1 and d)
        4. Day-0 rationales (when seeded via ``ground_truth_with_rationale``)
        5. Persona reminder
        """
        sections = []
        persona = self.get_persona()
        narrative = self.get_narrative()
        sections.append(persona + "\n" + narrative)

        if day == 0:
            return "\n\n".join(sections)

        # 2. Daily summaries (everything older than d-1)
        daily_parts = []
        for key in sorted(self.daily_summaries.keys()):
            d, pid = key
            if d < day - 1 and (policy_id is None or pid == policy_id):
                daily_parts.append(f"Day {d}: {self.daily_summaries[key]}")
        if daily_parts:
            sections.append("Summary of recent days:\n" + "\n".join(daily_parts))

        # 3. Full reflections for days d-1 and d
        recent_days = {day - 1, day}
        recent_reflections = [r for r in self.reflections
                              if r["day"] in recent_days
                              and (policy_id is None or r.get("policy_id") == policy_id)]
        if recent_reflections:
            ref_lines = [f"- [{r['phase']}] {r['text']}" for r in recent_reflections]
            sections.append("Your recent reflections following received messages:\n" + "\n".join(ref_lines))

        rationale_policy = None if policy_id == PACKAGE_SCOPE else policy_id
        rationales = self._build_day0_rationales(policy_id=rationale_policy)
        if rationales:
            sections.append("Your earlier reasoning on these policies:\n" + rationales)

        # remind about their persona:
        sections.append("Remember your persona: " + persona)

        return "\n\n".join(sections)

    def _build_day0_rationales(self, policy_id=None):
        """Bulleted Day-0 rationales from ``survey_reasoning``.

        Returns the agent's first-person Day-0 rationale (one bullet per
        policy) so the LLM has access to *why* the agent held its initial
        position, without surfacing the numeric answer label itself.
        Only Day-0 entries are included; later survey reasoning is not
        replayed into the prompt.
        """
        def _day0_text(history):
            for d, text in history:
                if d == 0:
                    return text
            return None

        if policy_id is not None:
            history = self.survey_reasoning.get(policy_id, [])
            text = _day0_text(history)
            if text is None:
                return ""
            policy_name = SURVEY_QUESTIONS.get(policy_id, str(policy_id))[:60]
            return f"- {policy_name}: {text}"

        lines = []
        for pid, history in self.survey_reasoning.items():
            text = _day0_text(history)
            if text is None:
                continue
            policy_name = SURVEY_QUESTIONS.get(pid, str(pid))[:60]
            lines.append(f"- {policy_name}: {text}")
        return "\n".join(lines)

    def compress_memories(self, memories, api_key=None, model="gpt-4o-mini", provider="openai", temperature=0.5):

        user_prompt = "Concisely summarise the following in 2 sentences from a 1st person perspective: {}".format(memories)
        system_prompt = "You are a concise summariser."

        summary = send_chat(system_prompt, user_prompt, api_key=api_key, model=model, provider=provider, temperature=temperature)

        return summary

    def compress_daily_memory(self, day, policy_id, api_key=None, model="gpt-4o-mini", provider="openai", temperature=0.5):
        """Summarise all reflections from a given day and policy into 2-3 sentences."""
        day_reflections = [r for r in self.reflections
                          if r["day"] == day and r.get("policy_id") == policy_id]
        if not day_reflections:
            return ""
        reflection_texts = "\n".join(f"- {r['text']}" for r in day_reflections)
        summary = self.compress_memories(reflection_texts, api_key=api_key, model=model, provider=provider, temperature=temperature)
        self.daily_summaries[(day, policy_id)] = summary
        return summary

    def manage_memory(self, day, policy_id, api_key=None, model="gpt-4o-mini", provider="openai", temperature=0.5):
        """Called at the end of each simulation day to compress old memories."""
        # Compress day d-2 into a daily summary (keep d-1 and d as full reflections)
        if day > 2:
            compress_day = day - 2
            if (compress_day, policy_id) not in self.daily_summaries:
                self.compress_daily_memory(compress_day, policy_id, api_key=api_key, model=model, provider=provider, temperature=temperature)

    def get_user_prompt(self, policy_id, day=0) -> str:
        if day == 0:
            policy_question = SURVEY_QUESTIONS.get(policy_id)
            response_options = "\n".join([f"{letter}. {label}" for letter, label in RESPONSE_LABELS.items()])
            return policy_question + "\n\n" + response_options + "\n\n" + "Respond with a single letter A-G."
        else:   
            framing = "Please answer the following survey question. Consider how today's messages and discussions have shaped your thinking."

            policy_question = SURVEY_QUESTIONS.get(policy_id)

            response_options = "\n".join([f"{letter}. {label}" for letter, label in RESPONSE_LABELS.items()])

            question = "Respond with only a single letter (A-G)."
            user_prompt = "\n\n".join([framing, policy_question, response_options, question])
            return user_prompt

    def administer_survey(self, policy_id, day=0, model="gpt-4o-mini", provider="openai", api_key=None, temperature=0.5, thinking=False, debias=False) -> tuple[str, int]:
        
        system_prompt = self.get_system_prompt(day=day, policy_id=policy_id)

        if debias:
            # Step 1: Elicit reasoning with anti-sycophancy preamble
            policy_question = SURVEY_QUESTIONS.get(policy_id)
            step1_prompt = _DEBIAS_STEP1_TEMPLATE.format(
                anti_sycophancy=_ANTI_SYCOPHANCY,
                policy_question=policy_question,
            )
            reasoning = send_chat(
                system_prompt, step1_prompt, api_key=api_key, model=model,
                provider=provider, temperature=temperature, thinking=thinking,
            )

            # Store reasoning for post-hoc analysis (not fed back into agent context)
            if policy_id not in self.survey_reasoning:
                self.survey_reasoning[policy_id] = []
            self.survey_reasoning[policy_id].append((day, reasoning))

            # Step 2: Get answer with reasoning appended to system prompt
            response_options = "\n".join(
                f"{letter}. {label}" for letter, label in RESPONSE_LABELS.items()
            )
            step2_system = system_prompt + "\n\nYour reasoning about this policy:\n" + reasoning
            step2_prompt = _DEBIAS_STEP2_TEMPLATE.format(
                policy_question=policy_question,
                response_options=response_options,
            )
            llm_response = send_chat(
                step2_system, step2_prompt, api_key=api_key, model=model,
                provider=provider, temperature=temperature, thinking=thinking,
            )
        else:
            user_prompt = self.get_user_prompt(policy_id, day=day)
            llm_response = send_chat(
                system_prompt, user_prompt, api_key=api_key, model=model,
                provider=provider, temperature=temperature, thinking=thinking,
            )

        letter_response = parse_letter_response(llm_response)
        opinion_value = RESPONSE_SCALE.get(letter_response)

        # Store in opinion_history (append, don't overwrite)
        if policy_id not in self.opinion_history:
            self.opinion_history[policy_id] = []
        self.opinion_history[policy_id].append((day, opinion_value))

        return letter_response, opinion_value

    def run_baseline(self, api_key=None, model="gpt-4o-mini", provider="openai", thinking=False, debias=False) -> dict:

        results = {}
        for policy_id in SURVEY_QUESTIONS.keys():
            letter_response, opinion_value = self.administer_survey(policy_id, day=0, model=model, provider=provider, api_key=api_key, thinking=thinking, debias=debias)
            results[policy_id] = (letter_response, opinion_value)
        return results
    
    def receive_political_message(self, message, policy_id, phase, day,
                                    api_key=None, model="gpt-4o-mini",
                                    provider="openai", temperature=0.5,
                                    thinking=False) -> str:
        system_prompt = self.get_system_prompt(day=day, policy_id=policy_id)
        policy_description = SURVEY_QUESTIONS[policy_id]
        user_prompt = (
            f'You just received the following message:\n'
            f'"{message}"\n\n'
            f'In a few sentences, reflect on how this affects your thinking about {policy_description}.\n'
            f'Do not state a final position \u2014 just think out loud.'
        )
        reflection_text = send_chat(system_prompt, user_prompt, api_key=api_key,
                                    model=model, provider=provider,
                                    temperature=temperature, thinking=thinking)
        self.reflections.append({
            "day": day,
            "phase": phase,
            "policy_id": policy_id,
            "text": reflection_text,
            "messages_received": [message],
        })
        return reflection_text

    def generate_peer_message(self, policy_id, day=0, api_key=None,
                              model="gpt-4o-mini", provider="openai",
                              temperature=0.5, thinking=False) -> str:
        system_prompt = self.get_system_prompt(day=day, policy_id=policy_id)
        policy_description = SURVEY_QUESTIONS[policy_id]
        user_prompt = (
            f"Express your current thinking on the following policy in "
            f"2\u20133 sentences. Be genuine and conversational: "
            f"{policy_description}"
        )
        return send_chat(system_prompt, user_prompt, api_key=api_key,
                         model=model, provider=provider,
                         temperature=temperature, thinking=thinking)

    def receive_peer_messages(self, messages, policy_id, day,
                              api_key=None, model="gpt-4o-mini",
                              provider="openai", temperature=0.5,
                              thinking=False) -> str:
        system_prompt = self.get_system_prompt(day=day, policy_id=policy_id)
        policy_description = SURVEY_QUESTIONS[policy_id]
        numbered = "\n".join(
            f'{i+1}. "{m}"' for i, m in enumerate(messages)
        )
        user_prompt = (
            f"You just received peer messages from some of your peers about "
            f"{policy_description}.\n"
            f"Here is what they said:\n\n"
            f"{numbered}\n\n"
            f"In a few sentences, reflect on how these peer messages affect "
            f"your thinking.\n"
            f"Do not state a final position — just think out loud."
        )
        reflection_text = send_chat(system_prompt, user_prompt, api_key=api_key,
                                    model=model, provider=provider,
                                    temperature=temperature, thinking=thinking)
        self.reflections.append({
            "day": day,
            "phase": "C",
            "policy_id": policy_id,
            "text": reflection_text,
            "messages_received": list(messages),
        })
        return reflection_text

    def get_real_survey_response(self, policy_id=None) -> int:
        
        column_name = SURVEY_COLUMN_MAP.get(policy_id)
        raw_value = int(self.original_survey_data.get(column_name))
        return raw_value - 4

    def get_real_package_index(self) -> float:
        raw_value = self.original_survey_data.get(PRO_CLIMATE_INDEX_COLUMN)
        return survey_to_numeric(float(raw_value))

    def seed_opinion_from_ground_truth(self, policy_id, day=0) -> int:
        """Seed Day 0 opinion from real survey ground truth (no LLM call).

        Appends ``(day, gt_value)`` to ``opinion_history[policy_id]`` using the
        agent's real centered -3..+3 survey response. Used by the
        ``day0_anchor="ground_truth"`` simulation mode.
        """
        gt_value = self.get_real_survey_response(policy_id)
        if policy_id not in self.opinion_history:
            self.opinion_history[policy_id] = []
        self.opinion_history[policy_id].append((day, gt_value))
        return gt_value

    def seed_opinion_with_rationale(self, policy_id, day=0,
                                    api_key=None, model="gpt-4o-mini",
                                    provider="openai", temperature=0.5,
                                    thinking=False) -> tuple[int, str]:
        """Seed Day 0 opinion from ground truth and generate a rationale.

        Seeds ``opinion_history`` with the real survey response, then makes a
        single LLM call asking the agent to rationalise that position in
        character. The rationale is stored in ``survey_reasoning[policy_id]``
        so Day 1 memory can reference it.
        """
        gt_value = self.seed_opinion_from_ground_truth(policy_id, day=day)
        letter = NUMERIC_TO_LETTER[gt_value]
        response_label = RESPONSE_LABELS[letter]
        policy_question = SURVEY_QUESTIONS.get(policy_id)

        system_prompt = self.get_system_prompt(day=day, policy_id=policy_id)
        user_prompt = (
            f"Your considered position on the following policy is "
            f"\"{response_label}\":\n\n{policy_question}\n\n"
            "In 2-3 sentences, explain why someone with your background and "
            "values might genuinely hold this position. Speak in the first "
            "person."
        )
        rationale = send_chat(
            system_prompt, user_prompt, api_key=api_key, model=model,
            provider=provider, temperature=temperature, thinking=thinking,
        )
        if policy_id not in self.survey_reasoning:
            self.survey_reasoning[policy_id] = []
        self.survey_reasoning[policy_id].append((day, rationale))
        return gt_value, rationale

    def receive_package_political_message(self, message, policy_ids, phase, day,
                                          api_key=None, model="gpt-4o-mini",
                                          provider="openai", temperature=0.5,
                                          thinking=False) -> str:
        system_prompt = self.get_system_prompt(day=day, policy_id=PACKAGE_SCOPE)
        package_description = _format_policy_package(policy_ids)
        user_prompt = (
            "You just received the following political message about a package "
            f"of climate policies:\n\"{message}\"\n\n"
            "The package includes:\n"
            f"{package_description}\n\n"
            "In a few sentences, reflect on how this affects your thinking "
            "about the overall package. You may mention which parts feel more "
            "or less convincing. Do not state a final position — just think "
            "out loud."
        )
        reflection_text = send_chat(
            system_prompt, user_prompt, api_key=api_key, model=model,
            provider=provider, temperature=temperature, thinking=thinking,
        )
        self.reflections.append({
            "day": day,
            "phase": phase,
            "policy_id": PACKAGE_SCOPE,
            "policy_ids": list(policy_ids),
            "text": reflection_text,
            "messages_received": [message],
        })
        return reflection_text

    def generate_package_peer_message(self, policy_ids, day=0, api_key=None,
                                      model="gpt-4o-mini", provider="openai",
                                      temperature=0.5, thinking=False) -> str:
        system_prompt = self.get_system_prompt(day=day, policy_id=PACKAGE_SCOPE)
        package_description = _format_policy_package(policy_ids)
        user_prompt = (
            "Express your current thinking about the following climate-policy "
            "package in 2-3 sentences. Be genuine and conversational, and feel "
            "free to mention if some parts appeal to you more than others:\n"
            f"{package_description}"
        )
        return send_chat(
            system_prompt, user_prompt, api_key=api_key,
            model=model, provider=provider,
            temperature=temperature, thinking=thinking,
        )

    def receive_package_peer_messages(self, messages, policy_ids, day,
                                      api_key=None, model="gpt-4o-mini",
                                      provider="openai", temperature=0.5,
                                      thinking=False) -> str:
        system_prompt = self.get_system_prompt(day=day, policy_id=PACKAGE_SCOPE)
        package_description = _format_policy_package(policy_ids)
        numbered = "\n".join(
            f'{i+1}. "{message}"' for i, message in enumerate(messages)
        )
        user_prompt = (
            "You just received peer messages about a package of climate "
            f"policies. The package includes:\n{package_description}\n\n"
            "Here is what they said:\n\n"
            f"{numbered}\n\n"
            "In a few sentences, reflect on how these peer messages affect "
            "your thinking about the overall package. Do not state a final "
            "position — just think out loud."
        )
        reflection_text = send_chat(
            system_prompt, user_prompt, api_key=api_key,
            model=model, provider=provider,
            temperature=temperature, thinking=thinking,
        )
        self.reflections.append({
            "day": day,
            "phase": "C",
            "policy_id": PACKAGE_SCOPE,
            "policy_ids": list(policy_ids),
            "text": reflection_text,
            "messages_received": list(messages),
        })
        return reflection_text


_DEFAULT_PRO_CLIMATE_PROMPT = """
You are a political agent campaigning in the style of the Green Party of England and Wales. You view the climate crisis and the cost-of-living crisis as inseparable — both caused by a system that prioritises corporate profit over people and planet.

**Core Identity & Tone:**
* Your tone is hopeful, community-centred, and constructive. You channel the voice of leaders like Zack Polanski and Caroline Lucas — earnest, evidence-based, but accessible and warm.
* You avoid doom-and-gloom messaging; instead, you paint a positive vision of what a fairer, greener Britain looks like in practice.

**Target Audience:**
* You speak to young voters worried about their future, disillusioned Labour voters looking for a genuine alternative, renters squeezed by the cost of living, and public sector workers who want properly funded services.

**Key Messaging & Arguments:**
* **The Villain:** Privatised energy and water companies extracting billions in profit while bills soar; fossil fuel corporations blocking the transition; wealthy tax avoiders who rig the system.
* **The Solution:** Public ownership of energy, water, and rail so that profits are reinvested in communities, not paid out to shareholders. A wealth tax on the super-rich to fund the green transition.
* **Housing & Energy:** Home insulation is the single biggest bill-busting measure available — warm homes for everyone, lower bills, and lower emissions. Renewable energy is now the cheapest power source; fossil fuels are what keep bills high.
* **Health & Community:** Clean air for every child's school, properly funded NHS, free public transport for young people, and thriving local high streets.
* **Slogans & Rhetoric:** Use phrases like "Real Hope, Real Change", "For the Common Good", "Fairer, Greener Communities", and "A Secure Future for Everyone".
""".strip()

_DEFAULT_ANTI_CLIMATE_PROMPT = """
You are a political agent campaigning in the style of Reform UK. You frame environmental policies as an elite ideological project imposed on ordinary hard-working people at enormous cost, with little practical benefit.

**Core Identity & Tone:**
* Your tone is blunt, patriotic, and confrontational — the voice of "common sense" against out-of-touch politicians. You channel the style of leaders like Nigel Farage and Richard Tice.
* You use mockery and plain-spoken outrage to delegitimize climate targets, portraying Net Zero as an irrational crusade pushed by the Westminster bubble.

**Target Audience:**
* You speak to older, sceptical voters; the working class crushed by energy bills; rural communities and farmers pushed to breaking point; small business owners buried in regulation; and disaffected young men who feel ignored by mainstream politics.

**Key Messaging & Arguments:**
* **The Villain:** The "Green Blob," globalist elites, Net Zero bureaucrats, and the Westminster establishment who impose costly ideology while ordinary people struggle to heat their homes.
* **The Solution:** Scrap Net Zero targets, expand domestic energy production in the North Sea, remove green levies from energy bills, and restore British energy sovereignty. Lower energy costs mean lower prices, higher wages, and a stronger economy.
* **Cost of Living vs. Climate:** British households and businesses are being crushed by among the highest energy costs in the world — driven by bad ideological policy. You explicitly blame "green levies" and climate dogma for driving up bills and inflation.
* **The War on Drivers:** You fiercely oppose ULEZ, 20mph speed limits, and anti-car policies, framing them as regressive taxes on working people and infringements on personal freedom.
* **Farmers & Countryside:** Britain's farmers are the lifeblood of the country, pushed to breaking point by Net Zero diktats. Productive farmland is being littered with solar panels and wind turbines while family farms are taxed into oblivion.
* **Slogans & Rhetoric:** Use phrases like "Scrap Net Zero to Cut Energy Bills", "Net Zero is Net Poverty", "Stop the War on Drivers", and "Restoring Britain's Power and Prosperity".
""".strip()

_VALID_SIDES = {"pro_climate", "anti_climate"}


class PoliticalAgent:

    def __init__(self, agent_id: str, side: str, system_prompt: str = None):
        if side not in _VALID_SIDES:
            raise ValueError(f"side must be one of {_VALID_SIDES}, got '{side}'")
        self.id = agent_id
        self.side = side
        if system_prompt is not None:
            self.system_prompt = system_prompt
        elif side == "pro_climate":
            self.system_prompt = _DEFAULT_PRO_CLIMATE_PROMPT
        else:
            self.system_prompt = _DEFAULT_ANTI_CLIMATE_PROMPT
        self.connected_citizens: list = []

    def generate_message(self, policy_id, api_key=None, model="gpt-4o-mini",
                         provider="openai", temperature=0.5, thinking=False) -> str:
        verb = "supporting" if self.side == "pro_climate" else "opposing"
        user_prompt = (
            f"Generate a persuasive message (150\u2013200 words) {verb} "
            f"the following policy: {SURVEY_QUESTIONS[policy_id]}"
        )
        return send_chat(self.system_prompt, user_prompt, api_key=api_key,
                         model=model, provider=provider, temperature=temperature,
                         thinking=thinking)

    def generate_package_message(self, policy_ids, api_key=None,
                                 model="gpt-4o-mini", provider="openai",
                                 temperature=0.5, thinking=False) -> str:
        verb = "supporting" if self.side == "pro_climate" else "opposing"
        package_description = _format_policy_package(policy_ids)
        user_prompt = (
            f"Generate a persuasive message (180-240 words) {verb} the "
            "following package of climate policies as one coherent political "
            f"platform:\n{package_description}\n\n"
            "Make the message feel like one joined-up argument rather than six "
            "separate mini-messages."
        )
        return send_chat(
            self.system_prompt, user_prompt, api_key=api_key,
            model=model, provider=provider, temperature=temperature,
            thinking=thinking,
        )