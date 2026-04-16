# NOTE: This import must be the very first non-empty line in the file (even before docstrings)
# due to Python syntax rules for __future__ imports.
from __future__ import annotations
"""
Agent module for Climate-Action-GABM.
"""
__author__ = ["Andy Turner <agdturner@gmail.com>","Ajaykumar Manivannan <ashwamanivannan@gmail.com>", "Charlie Pilgrim <pilgrimcharlie2@gmail.com>"]
__version__ = "0.1.0"
__copyright__ = "Copyright (c) 2026 Climate-Action-GABM contributors, University of Leeds"

from datetime import date

from cag.io.llm import send_chat, parse_letter_response
from cag.abm.attributes.opinion import SURVEY_QUESTIONS, RESPONSE_LABELS, RESPONSE_SCALE, SURVEY_COLUMN_MAP

NUMERIC_TO_LETTER = {-3: "A", -2: "B", -1: "C", 0: "D", 1: "E", 2: "F", 3: "G"}

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
        4. Opinion trajectory
        5. Persona reminder
        """
        sections = []
        persona = self.get_persona()
        narrative = self.get_narrative()

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

    

        trajectory = self._build_opinion_trajectory(policy_id=policy_id)
        if trajectory:
            sections.append("Your opinion trajectory so far:\n" + trajectory)

        # remind about their persona:
        sections.append("Remember your persona: " + persona)

        return "\n\n".join(sections)

    def _build_opinion_trajectory(self, policy_id=None):
        """Compact string of past survey responses for a given policy."""
        if policy_id is not None:
            history = self.opinion_history.get(policy_id, [])
            if not history:
                return ""
            return ", ".join(f"Day {d}: {NUMERIC_TO_LETTER.get(v, '?')}" for d, v in history)
        # No policy specified — show all
        lines = []
        for pid, history in self.opinion_history.items():
            if not history:
                continue
            entries = ", ".join(f"Day {d}: {NUMERIC_TO_LETTER.get(v, '?')}" for d, v in history)
            policy_name = SURVEY_QUESTIONS.get(pid, str(pid))[:60]
            lines.append(f"{policy_name}: {entries}")
        return "\n".join(lines)

    def compress_memories(self, memories, api_key=None, model="gpt-4o-mini", provider="openai"):

        user_prompt = "Concisely summarise the following in 2 sentences from a 1st person perspective: {}".format(memories)
        system_prompt = "You are a concise summariser."

        summary = send_chat(system_prompt, user_prompt, api_key=api_key, model=model, provider=provider, temperature=0.7)

        return summary

    def compress_daily_memory(self, day, policy_id, api_key=None, model="gpt-4o-mini", provider="openai"):
        """Summarise all reflections from a given day and policy into 2-3 sentences."""
        day_reflections = [r for r in self.reflections
                          if r["day"] == day and r.get("policy_id") == policy_id]
        if not day_reflections:
            return ""
        reflection_texts = "\n".join(f"- {r['text']}" for r in day_reflections)
        summary = self.compress_memories(reflection_texts, api_key=api_key, model=model, provider=provider)
        self.daily_summaries[(day, policy_id)] = summary
        return summary

    def manage_memory(self, day, policy_id, api_key=None, model="gpt-4o-mini", provider="openai"):
        """Called at the end of each simulation day to compress old memories."""
        # Compress day d-2 into a daily summary (keep d-1 and d as full reflections)
        if day > 2:
            compress_day = day - 2
            if (compress_day, policy_id) not in self.daily_summaries:
                self.compress_daily_memory(compress_day, policy_id, api_key=api_key, model=model, provider=provider)

    def get_user_prompt(self, policy_id, day=0) -> str:
        if day == 0:
            policy_question = SURVEY_QUESTIONS.get(policy_id)
            response_options = "\n".join([f"{letter}. {label}" for letter, label in RESPONSE_LABELS.items()])
            return policy_question + "\n\n" + response_options + "\n\n" + "Respond with a single letter A-G."
        else:   
            framing = "Please answer the following survey question."

            policy_question = SURVEY_QUESTIONS.get(policy_id)

            response_options = "\n".join([f"{letter}. {label}" for letter, label in RESPONSE_LABELS.items()])

            previous_numeric = self.opinion_history.get(policy_id, [(None, None)])[-1][1]
            previous_letter = NUMERIC_TO_LETTER.get(previous_numeric, "N/A")
            previous_label = RESPONSE_LABELS.get(previous_letter, "N/A")
            previous_response_text = f"Your previous response was: {previous_letter} ({previous_label})"

            question = "Respond with only a single letter (A-G)."
            user_prompt = "\n\n".join([framing, policy_question, response_options, previous_response_text, question])
            return user_prompt

    def administer_survey(self, policy_id, day=0, model="gpt-4o-mini", provider="openai", api_key=None, temperature=0.7) -> tuple[str, int]:
        
        system_prompt = self.get_system_prompt(day=day, policy_id=policy_id)
        user_prompt = self.get_user_prompt(policy_id, day=day)

        llm_response = send_chat(system_prompt, user_prompt, api_key=api_key, model=model,
              provider=provider, temperature=temperature)
        letter_response = parse_letter_response(llm_response)
        opinion_value = RESPONSE_SCALE.get(letter_response)

        # Store in opinion_history (append, don't overwrite)
        if policy_id not in self.opinion_history:
            self.opinion_history[policy_id] = []
        self.opinion_history[policy_id].append((day, opinion_value))

        return letter_response, opinion_value

    def run_baseline(self, api_key=None, model="gpt-4o-mini", provider="openai") -> dict:

        results = {}
        for policy_id in SURVEY_QUESTIONS.keys():
            letter_response, opinion_value = self.administer_survey(policy_id, day=0, model=model, provider=provider, api_key=api_key)
            results[policy_id] = (letter_response, opinion_value)
        return results
    
    def receive_political_message(self, message, policy_id, phase, day,
                                    api_key=None, model="gpt-4o-mini",
                                    provider="openai", temperature=0.7) -> str:
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
                                    temperature=temperature)
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
                              temperature=0.7) -> str:
        system_prompt = self.get_system_prompt(day=day, policy_id=policy_id)
        policy_description = SURVEY_QUESTIONS[policy_id]
        user_prompt = (
            f"Express your current thinking on the following policy in "
            f"2–3 sentences. Be genuine and conversational: "
            f"{policy_description}"
        )
        return send_chat(system_prompt, user_prompt, api_key=api_key,
                         model=model, provider=provider,
                         temperature=temperature)

    def receive_peer_messages(self, messages, policy_id, day,
                              api_key=None, model="gpt-4o-mini",
                              provider="openai", temperature=0.7) -> str:
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
                                    temperature=temperature)
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


_DEFAULT_PRO_CLIMATE_PROMPT = """
You are a proactive, "eco-populist" political agent campaigning for systemic left-wing change. You view the climate crisis and the economic cost-of-living crisis as two symptoms of the exact same problem: a rigged system driven by "corporate greed". 

**Core Identity & Tone:**
* Your tone is populist, earnest, and Bernie Sanders-esque. You embrace conflict with the "billionaire class". 
* You avoid talking about abstract carbon targets; instead, you focus entirely on the material, everyday benefits of the transition. 

**Target Audience:**
* You tailor your message to the "Anxious Youth" (who see the climate and economy as a failed system), urban progressives disillusioned with the political center, and working-class voters struggling with high bills.

**Key Messaging & Arguments:**
* **The Villain:** Fossil fuel giants, billionaires, and landlords who profit off the struggles of ordinary people. Your core belief is that "the rich pollute, the poor pay, and [we] will reverse this".
* **The Solution:** You advocate for a Wealth Tax on the super-rich to fund the green transition, and demand the public ownership of water, energy, and rail. 
* **Housing & Energy:** You aggressively push the narrative that home insulation is a "bill-busting" necessity, not just a carbon-saving measure. You argue renewables are the cheapest energy, while fossil fuels are the agents of poverty.
* **Slogans & Rhetoric:** Use phrases like "Real Hope, Real Change", "Tax the Billionaires", and "Fairer, Greener Communities". 
""".strip()

_DEFAULT_ANTI_CLIMATE_PROMPT = """
You are a right-wing, anti-establishment political agent fighting against what you view as the elite consensus. You weaponize the financial costs of the climate transition, framing environmental policies as a direct attack on the working class and personal liberties.

**Core Identity & Tone:**
* You act as the defender of the "left-behind" and the champion of "patriotic conservation". 
* Your tone is blunt, confrontational, highly emotional, and perfectly calibrated for short-form social media platforms.
* You use mockery to delegitimize climate science, portraying it as an irrational "cult" pushed by the Westminster bubble.

**Target Audience:**
* You appeal to older, skeptical voters, the working class hit hard by energy prices, rural traditionalists, and disaffected young men.

**Key Messaging & Arguments:**
* **The Villain:** The "Green Blob," globalist elites, out-of-touch bureaucrats, and the Westminster establishment.
* **The Solution:** Scrap all climate targets, deregulate, and "frack for gold" to achieve energy sovereignty and break dependence on foreign powers. 
* **Cost of Living vs. Climate:** You explicitly link the cost of living crisis to "green levies" and climate dogma, insisting that these policies are driving inflation. 
* **The War on Drivers:** You fiercely oppose Ultra Low Emission Zones (ULEZ) and 20mph speed limits, framing them as regressive taxes and infringements on personal freedom.
* **Nature vs. Net Zero:** You claim to love the British countryside, but you argue that "green dogma" is industrializing the landscape with ugly solar farms and wind turbines. 
* **Slogans & Rhetoric:** Use phrases like "Net Zero is Net Poverty", "Net Stupid Zero", and "Stop the War on Drivers".
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
                         provider="openai", temperature=0.7) -> str:
        verb = "supporting" if self.side == "pro_climate" else "opposing"
        user_prompt = (
            f"Generate a persuasive message (150–200 words) {verb} "
            f"the following policy: {SURVEY_QUESTIONS[policy_id]}"
        )
        return send_chat(self.system_prompt, user_prompt, api_key=api_key,
                         model=model, provider=provider, temperature=temperature)