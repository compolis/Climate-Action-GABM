"""
Core workflow for GABM survey-agent simulation.

This module now includes end-to-end functionality to:

- load and clean processed YouGov survey data,
- map coded respondent attributes into readable persona narratives,
- define influencer archetype personas (pro-/anti-climate),
- build respondent and influencer interaction graphs with NetworkX,
- run repeated LLM-mediated survey responses with per-agent memory,
- generate influencer persuasive messages per survey topic,
- convert categorical answers (A-G) into numeric support scores,
- visualize response trends and final-round distributions.

Primary dependencies:
- pandas
- networkx
- google-genai
- matplotlib (for plotting)

(change mode name for genai if needed, e.g. "gemini-2.0-flash" or "gemini-1.5-pro")

Notes:
- API keys are loaded from `data/api_key.csv`.
- Survey question definitions are imported from `survey_dict`.
"""
# Metadata
__author__ = ["Ajaykumar Manivannan <ashwamanivannan@gmail.com>"]
__version__ = "0.1.0"
__copyright__ = "Copyright (c) 2026 GABM contributors, University of Leeds"

# Standard library imports
from collections import defaultdict, Counter
from datetime import datetime
from pathlib import Path
import random
import time

import pandas as pd
import google.genai as genai

from google.genai import types

import networkx as nx

import numpy as np

import matplotlib.pyplot as plt

from collections import Counter

PROJECT_ROOT = Path(__file__).resolve().parents[2] if "__file__" in globals() else Path.cwd()
DATA_DIR = PROJECT_ROOT / "data"

_API_KEYS_DF = None
_GEMINI_CLIENT = None
_LAST_GEMINI_CALL_TS = 0.0

GEMINI_MIN_CALL_INTERVAL_SECONDS = 0.7
GEMINI_MAX_RETRIES = 5
GEMINI_INITIAL_BACKOFF_SECONDS = 1.5
GEMINI_MAX_BACKOFF_SECONDS = 20
GEMINI_MAX_RETRY_TIME_SECONDS = 120


def get_api_keys_df():
    """Load API keys once and reuse across calls."""
    global _API_KEYS_DF
    if _API_KEYS_DF is None:
        _API_KEYS_DF = pd.read_csv(DATA_DIR / "api_key.csv")
    return _API_KEYS_DF


def get_gemini_client():
    """Create Gemini client once and reuse across calls."""
    global _GEMINI_CLIENT
    if _GEMINI_CLIENT is None:
        api_keys = get_api_keys_df()
        genai_key = api_keys.loc[api_keys["api"] == "genai", "key"].iloc[0]
        _GEMINI_CLIENT = genai.Client(api_key=genai_key)
    return _GEMINI_CLIENT


def _throttle_gemini_calls(min_interval_seconds=GEMINI_MIN_CALL_INTERVAL_SECONDS):
    """Pause between Gemini calls to reduce rate-limit errors."""
    global _LAST_GEMINI_CALL_TS
    now = time.monotonic()
    elapsed = now - _LAST_GEMINI_CALL_TS
    wait_time = min_interval_seconds - elapsed
    if wait_time > 0:
        time.sleep(wait_time)
    _LAST_GEMINI_CALL_TS = time.monotonic()


def _is_retryable_gemini_error(exc: Exception) -> bool:
    """Return True for transient Gemini/API errors that are safe to retry."""
    message = str(exc).lower()
    retryable_markers = [
        "429",
        "resource_exhausted",
        "rate limit",
        "quota",
        "503",
        "unavailable",
        "deadline",
        "timeout",
        "temporarily",
        "internal",
        "empty response",
        "empty response text",
    ]
    return any(marker in message for marker in retryable_markers)


def _extract_text_from_gemini_response(response) -> str:
    """Extract text safely from Gemini response, including candidate-part fallback."""
    direct_text = (getattr(response, "text", "") or "").strip()
    if direct_text:
        return direct_text

    candidates = getattr(response, "candidates", None) or []
    parts_text = []
    for cand in candidates:
        content = getattr(cand, "content", None)
        parts = getattr(content, "parts", None) or []
        for part in parts:
            text = (getattr(part, "text", "") or "").strip()
            if text:
                parts_text.append(text)

    return "\n".join(parts_text).strip()


def gemini_generate_content_with_retry(prompt, model_name, config):
    """Generate Gemini content with throttling and retry/backoff safeguards."""
    genai_client = get_gemini_client()
    start_time = time.monotonic()
    last_exception = None

    for attempt in range(GEMINI_MAX_RETRIES + 1):
        try:
            _throttle_gemini_calls()
            response = genai_client.models.generate_content(
                model=model_name,
                contents=prompt,
                config=config,
            )
            output_text = _extract_text_from_gemini_response(response)
            if not output_text:
                raise RuntimeError("Gemini returned empty response text.")
            return output_text
        except Exception as exc:
            last_exception = exc
            retries_exhausted = attempt >= GEMINI_MAX_RETRIES
            retryable = _is_retryable_gemini_error(exc)
            elapsed = time.monotonic() - start_time

            if retries_exhausted or not retryable or elapsed >= GEMINI_MAX_RETRY_TIME_SECONDS:
                raise RuntimeError(
                    f"Gemini request failed after safeguards: {exc}"
                ) from exc

            backoff = min(
                GEMINI_INITIAL_BACKOFF_SECONDS * (2 ** attempt) + random.uniform(0, 0.4),
                GEMINI_MAX_BACKOFF_SECONDS,
            )
            print(
                f"Gemini transient error (attempt {attempt + 1}/{GEMINI_MAX_RETRIES + 1}): {exc}. "
                f"Retrying in {backoff:.2f}s..."
            )
            time.sleep(backoff)

    raise RuntimeError(f"Gemini request failed: {last_exception}")

def load_survey_data(file_path):
    """
    Load survey data from a CSV file.

    Parameters:
    file_path (str | Path): Path to the CSV file containing survey data.

    Returns:
    pd.DataFrame: A DataFrame containing the survey data.
    """
    try:
        # Read the Excel file into a DataFrame
        survey_data = pd.read_csv(file_path) 

        print('length of survey data: ', len(survey_data))
        # Select relevant columns and filter out rows with missing values
        col_list=['ID','age','male_dummy',
        'tprofile_GOR',
        "profile_education_level",
        'tprofile_gross_household',
        'ethnicity_R',
        'parent_dummy',
        'Vote2019R',
        'pastvote_EURef',
        'Political_Left_Right',\
        'Selftransc_Val','Selfenh_Values','Openness','ConformTrad','SDO','EDO','RWA',\
            'page5posttreatment6_1','page5posttreatment6_4','page5posttreatment6_5','page5posttreatment6_7',\
                'page5posttreatment6_9','page5posttreatment6_11','ProClimatePolSupp']


        survey_data= survey_data[col_list]
        # Identify columns with the most NaNs before filtering
        nan_counts = survey_data.isna().sum().sort_values(ascending=False)
        print("\nColumns with NaN counts (before filtering):")
        print(nan_counts[nan_counts > 0])

        if nan_counts.max() > 0:
            max_nan_col = nan_counts.idxmax()
            print(f"\nColumn with most NaNs: {max_nan_col} ({nan_counts.max()} NaNs)")
        else:
            print("\nNo NaNs found in selected columns.")
        # Drop rows with missing values in the selected columns
        survey_data = survey_data.dropna(subset=survey_data.columns.values)
        # Convert ID to integer to avoid numpy float64 keys (must be after dropna)
        survey_data['ID'] = survey_data['ID'].astype(int)
        # Filter out rows based on specified conditions (skipped or invalid responses)
        survey_data=survey_data[(survey_data['profile_education_level']<18) & (survey_data['ethnicity_R']<5) & (survey_data['pastvote_EURef']<4) &(survey_data['Political_Left_Right']<8)  ]
        print('length of survey data after filtering: ', len(survey_data))
        return survey_data
    except Exception as e:
        print(f"Error loading survey data: {e}")
        return None

    

def get_narrative(score, attribute_name):
    """
    Converts a numerical score into a first-person narrative description 
    based on the attribute.
    """
    metrics_data = {
        "Selftransc_Val": {
            "scale": 6,
            "low": "I prioritize my own immediate circle or needs and do not place high importance on protecting the natural environment, promoting global peace, or actively caring for the well-being and equal treatment of others.",
            "moderate": "I care about the people close to me and have a basic respect for nature, but I do not actively champion global equality or make environmental protection a primary, driving life focus.",
            "high": "I am deeply committed to caring for nature, protecting the environment, and responding to the needs of others. I strongly believe in global harmony, equal opportunities for everyone, and actively helping those around me."
        },
        "Selfenh_Values": {
            "scale": 6,
            "low": "I am not strongly driven by the need to get ahead of others, impress people, or hold leadership positions where I tell others what to do.",
            "moderate": "I appreciate personal success and am capable of taking charge when necessary, but I do not feel a constant need to dominate decisions or impress others to feel fulfilled.",
            "high": "I am highly motivated by personal success, getting ahead in life, and impressing others. I strongly desire to be in charge, be the primary decision-maker, and have people follow my lead."
        },
        "Openness": {
            "scale": 6,
            "low": "I prefer routine and the familiar, showing little interest in taking risks, seeking out new adventures, or coming up with highly original ideas.",
            "moderate": "I am moderately curious and will occasionally try new things, but I generally balance this by relying on familiar methods rather than constantly seeking out extreme novelty or risks.",
            "high": "I am highly curious, adventurous, and love trying out new things. I value creativity, originality, and taking risks to fully understand the world around me."
        },
        "ConformTrad": {
            "scale": 6,
            "low": "I do not feel strictly bound by traditional values, customs, or the need to be unconditionally obedient to older generations.",
            "moderate": "I maintain a general respect for elders and standard societal norms, but I am flexible in my thinking and do not strictly adhere to all traditional customs.",
            "high": "I place a high value on obedience, showing deep respect for parents and older people. I strongly believe in maintaining traditional ways of thinking, keeping up customs, and always behaving properly according to expectations."
        },
        "SDO": {
            "scale": 7,
            "low": "I strongly believe that all groups should have an equal chance to succeed and that society should actively work to equalize conditions. I firmly reject the idea that any group is inferior or should dominate others.",
            "moderate": "I generally support fairness but might implicitly accept that some mild social hierarchies are a natural part of society, without actively pushing for extreme inequality or strict egalitarianism.",
            "high": "I believe that an ideal society requires some groups to be on top and others on the bottom. I view certain groups as inherently inferior and oppose efforts to make all groups equal, feeling that equality should not be a primary goal."
        },
        "EDO": {
            "scale": 7,
            "low": "I believe that all lifeforms on Earth should be treated equally and that no single species, including humans, should dominate the planet.",
            "moderate": "I believe human progress is important but should generally be balanced with environmental respect, avoiding the extreme view that humans must always dominate nature.",
            "high": "I believe humans are inherently superior to other lifeforms and that humanity must sometimes put itself ahead of nature to progress. I firmly support the idea that humans should dominate the natural world."
        },
        "RWA": {
            "scale": 6,
            "low": "I am highly skeptical of leaders and believe that questioning authority and traditions is necessary for societal progress. I strongly oppose the use of force against others, even if ordered to do so by proper authorities.",
            "moderate": "I have a healthy respect for leaders and traditions but maintain some skepticism; I generally believe force should be avoided unless dealing with highly specific, threatening situations.",
            "high": "I believe leaders generally know what is best and tell the truth, and that traditions are the foundation of a healthy society. I view people who challenge traditions as dangerous and strongly support using strong force against threatening groups."
        }
    }

    if attribute_name not in metrics_data:
        return ""

    data = metrics_data[attribute_name]
    max_scale = data["scale"]

    if max_scale == 6:
        if score < 2.67: return data["low"]
        elif score < 4.34: return data["moderate"]
        else: return data["high"]
    elif max_scale == 7:
        if score <= 3.00: return data["low"]
        elif score <= 5.00: return data["moderate"]
        else: return data["high"]

def format_persona_from_row(row):
    """
    Takes a dataframe row (dict) and formats it into a comprehensive
    persona string structure incorporating demographics, politics, and 7 core values.
    """
    # 1. Base Demographic and Political String
    base_persona = (
        f"Demographically, I am a {row['age']}-year-old {row['male_dummy']} living in the {row['tprofile_GOR']}, United Kingdom. "
        f"My ethnic background is {row['ethnicity_R']}, and I hold a {row['profile_education_level']}. "
        f"Financially, my gross household income falls into the {row['tprofile_gross_household']} bracket. "
        f"Regarding my family status, I {row['parent_dummy']} a parent. "
        f"Politically, I position myself on the {row['Political_Left_Right']} of the spectrum. "
        f"In the 2019 General Election, I cast my vote for the {row['Vote2019R']}. "
        f"Looking back at the EU Referendum, {row['pastvote_EURef']}."
    )

    # 2. Fetch Narratives for all 7 metrics (Core Human Values, Ideological Attitudes/Worldviews)
    selftransc_narrative = get_narrative(row['Selftransc_Val'], 'Selftransc_Val')
    selfenh_narrative = get_narrative(row['Selfenh_Values'], 'Selfenh_Values')
    openness_narrative = get_narrative(row['Openness'], 'Openness')
    conform_narrative = get_narrative(row['ConformTrad'], 'ConformTrad')
    sdo_narrative = get_narrative(row['SDO'], 'SDO')
    edo_narrative = get_narrative(row['EDO'], 'EDO')
    rwa_narrative = get_narrative(row['RWA'], 'RWA')

    # 3. Combine into a cohesive final profile
    full_persona = (
        f"{base_persona}\n\n"
        f"When it comes to my core values and worldview: {selftransc_narrative} {selfenh_narrative} "
        f"{openness_narrative} {conform_narrative} {sdo_narrative} {edo_narrative} {rwa_narrative}"
    )

    return full_persona

# def format_persona_from_row(row):
#     """
#     Takes a dataframe row (dict) and formats it into the specific 
#     persona string structure requested.
#    only includes demographics and political attributes, not the 7 core values (to keep it concise for now).
#     """
#     return (f"Demographically, I am a {row['age']}-year-old {row['male_dummy']} living in the {row['tprofile_GOR']}, United Kingdom. My ethnic background is {row['ethnicity_R']}, and I hold a {row['profile_education_level']}. Financially, my gross household income falls into the {row['tprofile_gross_household']} bracket. Regarding my family status, I {row['parent_dummy']} a parent. Politically, I position myself on the {row['Political_Left_Right']} of the spectrum. In the 2019 General Election, I cast my vote for the {row['Vote2019R']}. Looking back at the EU Referendum, {row['pastvote_EURef']}.")
    

def create_persona_text_for_people_agent(survey_data):
    """
        Create persona text for each respondent from coded survey data.

    Parameters:
        survey_data (pd.DataFrame): A DataFrame containing respondent profile columns
        with coded values.

    Returns:
        dict: A dictionary mapping respondent `ID` to a formatted persona text string.

        Notes:
        - Uses `PROFILE_DICT` from `gabm.survey_dict` to map coded values to
            human-readable labels.
        - Uses `format_persona_from_row` to generate the final persona sentence.
    """
    # Define the list of profile attributes to be included in the persona text
    p_list=['age','male_dummy',
    'tprofile_GOR',
    "profile_education_level",
    'tprofile_gross_household',
    'ethnicity_R',
    'parent_dummy',
    'Vote2019R',
    'pastvote_EURef',
    'Political_Left_Right',"Selftransc_Val","Selfenh_Values","Openness","ConformTrad","SDO","EDO","RWA"]
    # ------------------------------------------------------------------
    # Load THE PROFILE DICTIONARY TO MAP CODED VALUES TO HUMAN-READABLE TEXT
    try:
        from survey_dict import PROFILE_DICT
    except ImportError:
        from survey_dict import PROFILE_DICT

    # Iterate through each row in the survey data to create persona texts
    all_persona_texts = {}
    for index,row in survey_data.iterrows():
        # Create a dictionary to hold the profile attributes for the current respondent - converting coded values to human-readable text using PROFILE_DICT
        id_profile_dict={}
        for x in p_list:
            # For 'age' and core values/Ideological Attitudes, we can directly use the value without conversion
            if x in ['age','Selftransc_Val','Selfenh_Values','Openness','ConformTrad','SDO','EDO','RWA']:
                id_profile_dict[x]=row[x]
            else:
                # Convert the coded value to human-readable text using PROFILE_DICT - first round the value to the nearest integer to match the keys in PROFILE_DICT
                id_profile_dict[x]=PROFILE_DICT[x][str(round(row[x]))]
        # 1. Generate the Persona String dynamically
        persona_text = format_persona_from_row(id_profile_dict)
        # 2. Store the generated persona text in a dictionary with the respondent's ID as the key (converted to int)
        all_persona_texts[int(row['ID'])]=persona_text
    return all_persona_texts

def create_persona_text_for_influencer_agent():
    """
    Define the personas for the influencer agents based on Green Party UK (Pro) and Reform Party UK (anti) archetypes.
    """
    pro_climate_agent_persona = """
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
"""

    anti_climate_agent_persona = """
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
"""

    return {"pro_climate_agent_persona": pro_climate_agent_persona, "anti_climate_agent_persona": anti_climate_agent_persona}



def compute_similarity(text_a, text_b):
    """
    Compute a simple similarity score between two persona texts using
    Jaccard similarity over lowercase word tokens.
    """
    tokens_a = set(str(text_a).lower().split())
    tokens_b = set(str(text_b).lower().split())

    if not tokens_a and not tokens_b:
        return 1.0
    if not tokens_a or not tokens_b:
        return 0.0

    intersection = tokens_a.intersection(tokens_b)
    union = tokens_a.union(tokens_b)
    return len(intersection) / len(union)


def create_networkx_graph_between_people_agents(all_persona_texts):
    """
    Create a NetworkX graph where each node represents a respondent persona, and edges represent similarity between personas based on their text descriptions.

    Parameters:
        all_persona_texts (dict): A dictionary mapping respondent IDs to their persona text descriptions.
    """
    G = nx.Graph()

    # Add nodes for each persona
    for respondent_id, persona_text in all_persona_texts.items():
        G.add_node(respondent_id, description=persona_text,agent_type='people_agent')

    # Compute similarity between personas and add edges
    respondent_ids = list(all_persona_texts.keys())
    for i in range(len(respondent_ids)):
        for j in range(i + 1, len(respondent_ids)):
            id_i = respondent_ids[i]
            id_j = respondent_ids[j]
            text_i = all_persona_texts[id_i]
            text_j = all_persona_texts[id_j]

            # Compute similarity (this is a placeholder - replace with actual similarity computation)
            similarity_score = compute_similarity(text_i, text_j)

            # Add an edge if similarity is above a certain threshold
            if similarity_score > 0.3:  # Example threshold
                G.add_edge(id_i, id_j, weight=similarity_score)

    return G

    
def create_networkx_graph_between_people_and_influencer_agents(G_people_agent, influencer_personas):
    """
    Build a combined social graph by extending the respondent graph with influencer nodes.

    This function starts from `G_people_agent`, adds each influencer persona as a
    node (with its text stored in `description`), and then connects every influencer
    to every respondent node.

    Parameters:
        G_people_agent (nx.Graph): Existing graph of respondent personas.
        influencer_personas (dict[str, str]): Mapping of influencer node names to
            persona descriptions.

    Returns:
        nx.Graph: A copied graph containing both respondent and influencer nodes,
        with influencer-to-respondent edges added.
    """
    G = G_people_agent.copy()

    # Add influencer persona nodes
    for persona_name, persona_text in influencer_personas.items():
        G.add_node(persona_name, description=persona_text, agent_type='influencer_agent')

    #Option A: Crete a directed edge from each influence agent to all people agents
    for influencer_name, influencer_text in influencer_personas.items():
        for respondent_id in G_people_agent.nodes:
            G.add_edge(influencer_name, respondent_id)
    # Optional B: Create edge between influencer agent and people agents based on political alignment and climate policy support
    
    
    return G


class AgentMemoryStore:
    """
    In-memory store for per-agent, per-question interaction history.

    Each history item stores influencer message and the selected survey answer.
    """

    def __init__(self, max_turns=8):
        self.max_turns = max_turns
        self.history = defaultdict(list)

    def get_history(self, agent_id, question_id):
        turns = self.history[(agent_id, question_id)]
        return turns[-self.max_turns:]

    def add_turn(self, agent_id, question_id, influencer_message, answer):
        self.history[(agent_id, question_id)].append(
            {
                "influencer_message": influencer_message,
                "answer": answer,
            }
        )


def ask_agent_survey_question(
    persona_description,
    question_data,
    provider="gemini",
    model_name=None,
    agent_id=None,
    influencer_message="",
    memory_store=None,
    question_id=None,
):
    """
    Ask an LLM to answer one survey question while role-playing a respondent persona.

    The function builds a constrained prompt that includes persona, influencer
    exposure, and optional prior answer history for this same question.
    It then sends the prompt to the selected provider (currently Gemini) and
    returns a single cleaned option letter (A-G).

    Parameters:
        persona_description (str): Persona text describing the respondent.
        question_data (dict): Survey question payload with:
            - 'text' (str): question prompt
            - 'options' (dict): option text keyed by letters, e.g. 'A'...'G'
        provider (str, optional): LLM provider name. Currently supports
            'gemini'. Defaults to 'gemini'.
        model_name (str, optional): Model override. If None, a default Gemini
            model is used.
        agent_id (str|int, optional): Unique respondent ID used for memory.
        influencer_message (str, optional): Latest influencer message shown to
            the respondent before answering.
        memory_store (AgentMemoryStore, optional): Memory store used to fetch
            and append previous turns.
        question_id (str, optional): Stable question identifier. If None,
            `question_data['id']` is used, otherwise `question_data['text']`.

    Returns:
        str: A single uppercase letter in A-G when successful, otherwise an
        error string beginning with "Error:".
    """

    resolved_question_id = (
        question_id
        if question_id is not None
        else question_data.get("id", question_data.get("text", "unknown_question"))
    )

    history_text = "None"
    if memory_store is not None and agent_id is not None:
        prior_turns = memory_store.get_history(agent_id, resolved_question_id)
        if prior_turns:
            history_lines = []
            for idx, turn in enumerate(prior_turns, start=1):
                prior_message = str(turn.get("influencer_message", "")).strip()
                prior_answer = str(turn.get("answer", "")).strip()
                history_lines.append(
                    f"{idx}. Message: {prior_message} | Your answer: {prior_answer}"
                )
            history_text = "\n".join(history_lines)
    
    # 1. Construct the Prompt
    # Note: We safely use .get() for D-G in case a question only has A-C
    prompt = f"""
    You are participating in a demographic survey.
    
    YOUR PERSONA:
    {persona_description}

    CURRENT INFLUENCER MESSAGE:
    {influencer_message}

    YOUR PAST ANSWER HISTORY FOR THIS QUESTION:
    {history_text}
    
    INSTRUCTIONS:
    1. Read the question below.
    2. Consider your persona, current influencer message, and your prior answers.
    3. Select the option (A-G) that ALIGNS BEST with your current worldview.
    3. You MUST output ONLY the letter of your choice. Do not explain.
    
    QUESTION: {question_data['text']}
    
    OPTIONS:
    A) {question_data['options'].get('A', '')}
    B) {question_data['options'].get('B', '')}
    C) {question_data['options'].get('C', '')}
    D) {question_data['options'].get('D', '')}
    E) {question_data['options'].get('E', '')}
    F) {question_data['options'].get('F', '')}
    G) {question_data['options'].get('G', '')}
    
    YOUR CHOICE (Letter Only):
    """

    system_instruction = "You are a survey respondent. You strictly follow persona instructions."
    
    try:
        raw_content = ""

        # ------------------------------------------------------------------
        # PROVIDER LOGIC
        # ------------------------------------------------------------------

        # GEMINI
        if provider.lower() == "gemini":
            # Gemini defines system instruction at model init
            config = types.GenerateContentConfig(
                temperature=0.3,
                max_output_tokens=5,
                system_instruction=system_instruction  # <--- MOVED HERE
            )

            raw_content = gemini_generate_content_with_retry(
                prompt=prompt,
                model_name=model_name if model_name else "gemini-2.0-flash",
                config=config,
            )

        else:
            return "Error: Unknown Provider"
       # ------------------------------------------------------------------
        # CLEANUP & RETURN
        # ------------------------------------------------------------------
        answer = raw_content.strip().upper()
        
        # If the model output "Option A" or "A)", just take the first char
        if len(answer) > 1:
            # Simple check to see if the first char is a valid letter
            if answer[0] in ['A', 'B', 'C', 'D', 'E', 'F', 'G']:
                answer = answer[0]

        if (
            memory_store is not None
            and agent_id is not None
            and answer in ['A', 'B', 'C', 'D', 'E', 'F', 'G']
        ):
            memory_store.add_turn(
                agent_id=agent_id,
                question_id=resolved_question_id,
                influencer_message=influencer_message,
                answer=answer,
            )
        
        return answer

    except Exception as e:
        return f"Error: {e}"


def draft_influencer_persuasive_message(
    influencer_name,
    influencer_persona,
    topic_or_question,
    provider="gemini",
    model_name=None
):
    """
    Draft a brief persuasive message from a political party influencer
    that is either pro- or anti-climate policy.

    Stance is inferred from `influencer_name`:
    - startswith("pro")  -> pro-climate policy
    - startswith("anti") -> anti-climate policy
    """
    if not isinstance(influencer_name, str) or not influencer_name.strip():
        return "Error: influencer_name must be a non-empty string"


    if influencer_name=="pro_climate_agent_persona":
        party_position = "pro-climate policy"
        action_phrase = "supports stronger climate policy"
    elif influencer_name=="anti_climate_agent_persona":
        party_position = "anti-climate policy"
        action_phrase = "opposes stronger climate policy"
    else:
        return "Error: influencer_name must be 'pro_climate_agent_persona' or 'anti_climate_agent_persona'"

    prompt = f"""
    You are a UK political party influencer.

    PARTY POSITION:
    {party_position}

    PARTY PERSONA:
    {influencer_persona}

    TOPIC / SURVEY QUESTION:
    {topic_or_question}

    TASK:
    Write a short persuasive public message (2-4 sentences, max ~80 words) that {action_phrase}.
    Keep the tone natural, clear, and consistent with the party persona.
    Do not output labels, bullet points, or explanations.
    """

    system_instruction = (
        "You are a political messaging assistant. Follow the party persona and policy position exactly."
    )

    try:
        if provider.lower() != "gemini":
            return "Error: Unknown Provider"

        config = types.GenerateContentConfig(
            temperature=0.7,
            max_output_tokens=140,
            system_instruction=system_instruction,
        )
        # from gabm.io.llm.genai import GenAIService
        # api_keys = get_api_keys_df()
        # genai_key = api_keys.loc[api_keys["api"] == "genai", "key"].iloc[0]
        # genai_service = GenAIService()
        # result = genai_service.send(api_key=genai_key, message=prompt)
        # print('raw result from genai service: ', result)
        return gemini_generate_content_with_retry(
            prompt=prompt,
            model_name=model_name if model_name else "gemini-2.0-flash",
            config=config,
        )

    except Exception as e:
        return f"Error: {e}"
    

def strip_after_colon(text: str) -> str:
    """Utility function to strip any text after a colon in a string."""
    return text.split(":", 1)[0].strip()


def answer_to_score(answer: str) -> float:
    """
    Convert survey answer (A-G) to numerical score (-3 to +3).
    A (Strongly oppose) = -3
    B (Somewhat oppose) = -2
    C (Slightly oppose) = -1
    D (Neutral) = 0
    E (Slightly support) = +1
    F (Somewhat support) = +2
    G (Strongly support) = +3
    """
    mapping = {'A': -3, 'B': -2, 'C': -1, 'D': 0, 'E': 1, 'F': 2, 'G': 3}
    return mapping.get(answer, None)


def plot_question_results(question_results, question_id, figsize=(14, 6)):
    """
    Plot trend of agent responses across rounds and influencers.
    
    Parameters:
        question_results (dict): Results dict with structure {round: {influencer: {agent_id: answer}}}
        question_id (str): Question identifier for title
        figsize (tuple): Figure size
    """
    import matplotlib.pyplot as plt
    import numpy as np
    
    fig, axes = plt.subplots(1, 2, figsize=figsize)
    
    # Extract influencer names
    influencers = list(question_results[1].keys())
    rounds = sorted(question_results.keys())
    
    # For each influencer, compute mean score per round
    for influencer_name in influencers:
        mean_scores = []
        std_scores = []
        
        for round_num in rounds:
            answers = question_results[round_num][influencer_name].values()
            scores = [answer_to_score(ans) for ans in answers if ans]
            
            if scores:
                mean_scores.append(np.mean(scores))
                std_scores.append(np.std(scores))
            else:
                mean_scores.append(0)
                std_scores.append(0)
        
        # Plot 1: Line plot of mean score over rounds
        axes[0].plot(
            rounds, 
            mean_scores, 
            marker='o', 
            label=influencer_name, 
            linewidth=2
        )
        axes[0].fill_between(
            rounds, 
            np.array(mean_scores) - np.array(std_scores),
            np.array(mean_scores) + np.array(std_scores),
            alpha=0.2
        )
    
    axes[0].axhline(y=0, color='gray', linestyle='--', alpha=0.5)
    axes[0].set_xlabel('Round')
    axes[0].set_ylabel('Mean Score (-3=oppose, +3=support)')
    axes[0].set_title(f'{question_id}: Mean Response Trend')
    axes[0].legend()
    axes[0].grid(True, alpha=0.3)
    axes[0].set_ylim([-3.5, 3.5])
    
    # Plot 2: Distribution of final round responses
    for influencer_name in influencers:
        final_round = rounds[-1]
        answers = question_results[final_round][influencer_name].values()
        scores = [answer_to_score(ans) for ans in answers if ans]
        
        axes[1].hist(
            scores, 
            bins=7, 
            alpha=0.5, 
            label=influencer_name,
            range=(-3.5, 3.5)
        )
    
    axes[1].axvline(x=0, color='gray', linestyle='--', alpha=0.5)
    axes[1].set_xlabel('Score (-3=oppose, +3=support)')
    axes[1].set_ylabel('Frequency')
    axes[1].set_title(f'{question_id}: Response Distribution (Final Round)')
    axes[1].legend()
    axes[1].grid(True, alpha=0.3, axis='y')
    
    plt.tight_layout()
    return fig

def run_persona_description_test():
    """
    Test function to load survey data, create persona descriptions for each respondent, and print them out.

    """
    file_path = DATA_DIR / "yougov_survey_data" / "YouGovProcessedData.csv"
    survey_data = load_survey_data(file_path)
    survey_data = survey_data.head(1)
    all_persona_texts = create_persona_text_for_people_agent(survey_data)
    for respondent_id, persona_text in all_persona_texts.items():
        print(f"Respondent ID: {respondent_id}")
        print("Persona Description:")
        print(persona_text)
        print("\n" + "="*80 + "\n")



def print_column_counters(df, column_names, include_nan=True, top_n=None):
    """Utility function to print value counts for specified columns in a DataFrame.
    Parameters:
        df (pd.DataFrame): The DataFrame containing the data.
        column_names (list of str): List of column names to analyze.
        include_nan (bool): Whether to include NaN values in the counts. Default is True.
        top_n (int or None): If specified, only print the top N most common values. Default is None (print all).    
    """
    # Keep only columns that exist
    missing = [c for c in column_names if c not in df.columns]
    valid = [c for c in column_names if c in df.columns]

    if missing:
        print("Skipped missing columns:", missing)

    for col in valid:
        values = df[col] if include_nan else df[col].dropna()
        counts = Counter(values.tolist())

        print(f"\n=== {col} ===")
        if top_n is None:
            for k, v in counts.items():
                print(f"{k}: {v}")
        else:
            for k, v in counts.most_common(top_n):
                print(f"{k}: {v}")


def survey_data_split():
    """
    Splits the survey data into train, test, and validation sets and saves them as separate CSV files.
    The function reads the original survey data, shuffles it, and then splits it into:
    - Train set: 60% of the data
    - Test set: 20% of the data
    - Validation set: 20% of the data
    Each split is saved in the same directory as the original data with filenames:
    - YouGovProcessedData_train.csv
    - YouGovProcessedData_test.csv
    - YouGovProcessedData_validation.csv
    """
    file_path = DATA_DIR / "yougov_survey_data" / "YouGovProcessedData.csv"
    survey_data = load_survey_data(file_path)

    if survey_data is None or survey_data.empty:
        print("No survey data available to split.")
        return None

    shuffled = survey_data.sample(frac=1.0, random_state=42).reset_index(drop=True)
    total_rows = len(shuffled)

    train_end = int(total_rows * 0.6)
    test_end = train_end + int(total_rows * 0.2)

    train_data = shuffled.iloc[:train_end].copy()
    test_data = shuffled.iloc[train_end:test_end].copy()
    validation_data = shuffled.iloc[test_end:].copy()

    output_dir = DATA_DIR / "yougov_survey_data"
    output_dir.mkdir(parents=True, exist_ok=True)

    train_path = output_dir / "YouGovProcessedData_train.csv"
    test_path = output_dir / "YouGovProcessedData_test.csv"
    validation_path = output_dir / "YouGovProcessedData_validation.csv"

    train_data.to_csv(train_path, index=False)
    test_data.to_csv(test_path, index=False)
    validation_data.to_csv(validation_path, index=False)

    print("Survey data split complete:")
    print(f"Total rows: {total_rows}")
    print(f"Train (60%): {len(train_data)} -> {train_path}")
    print(f"Test (20%): {len(test_data)} -> {test_path}")
    print(f"Validation (20%): {len(validation_data)} -> {validation_path}")

    return train_data, test_data, validation_data

def survey_data_test():
    file_path = DATA_DIR / "yougov_survey_data" / "YouGovProcessedData_train.csv"
    survey_data = load_survey_data(file_path)
    column_names=["Political_Left_Right","Vote2019R"]
    print_column_counters(survey_data, column_names, include_nan=True, top_n=None)


def ask_agent_survey_question_acc(persona_description, question_data, provider="gemini", model_name=None):
    """
    Prompts an LLM to answer a survey question as a specific persona.
    
    Args:
        persona_description (str): The demographic details.
        question_data (dict): Dictionary containing 'text' and 'options'.
        provider (str): 'openai', 'deepseek', 'llama', 'claude', or 'gemini'.
        model_name (str): Optional override. If None, defaults are used.
    """
    
    # 1. Construct the Prompt
    # Note: We safely use .get() for D-G in case a question only has A-C
    prompt = f"""
    You are participating in a demographic survey.
    
    YOUR PERSONA:
    {persona_description}
    
    INSTRUCTIONS:
    1. Read the question below.
    2. Select the option (A-G) that ALIGNS BEST with your persona's worldview.
    3. You MUST output ONLY the letter of your choice. Do not explain.
    
    QUESTION: {question_data['text']}
    
    OPTIONS:
    A) {question_data['options'].get('A', '')}
    B) {question_data['options'].get('B', '')}
    C) {question_data['options'].get('C', '')}
    D) {question_data['options'].get('D', '')}
    E) {question_data['options'].get('E', '')}
    F) {question_data['options'].get('F', '')}
    G) {question_data['options'].get('G', '')}
    
    YOUR CHOICE (Letter Only):
    """

    system_instruction = "You are a survey respondent. You strictly follow persona instructions."
    
    try:
        raw_content = ""

        # ------------------------------------------------------------------
        # PROVIDER LOGIC
        # ------------------------------------------------------------------
        
        # 1. OPENAI
        if provider.lower() == "openai":
            model = model_name if model_name else "gpt-4o-mini"
            response = client_openai.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_instruction},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=5
            )
            raw_content = response.choices[0].message.content

        # 2. DEEPSEEK
        elif provider.lower() == "deepseek":
            model = model_name if model_name else "deepseek-chat"
            response = client_deepseek.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_instruction},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=5
            )
            raw_content = response.choices[0].message.content

        # 3. LLAMA (via Groq)
        elif provider.lower() == "llama":
            model = model_name if model_name else "llama3-70b-8192"
            response = client_llama.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_instruction},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=5
            )
            raw_content = response.choices[0].message.content

        # 4. CLAUDE
        elif provider.lower() == "claude":
            model = model_name if model_name else "claude-3-5-sonnet-20241022"
            response = client_claude.messages.create(
                model=model,
                system=system_instruction,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=5
            )
            raw_content = response.content[0].text

        # 5. GEMINI
        elif provider.lower() == "gemini":
            # Gemini defines system instruction at model init
            config = types.GenerateContentConfig(
                temperature=0.3,
                max_output_tokens=5,
                system_instruction=system_instruction  # <--- MOVED HERE
            )

            raw_content = gemini_generate_content_with_retry(
                prompt=prompt,
                model_name=model_name if model_name else "gemini-2.5-flash",
                config=config,
            )

        else:
            return "Error: Unknown Provider"

        # ------------------------------------------------------------------
        # CLEANUP & RETURN
        # ------------------------------------------------------------------
        answer = raw_content.strip().upper()
        
        # If the model output "Option A" or "A)", just take the first char
        if len(answer) > 1:
            # Simple check to see if the first char is a valid letter
            if answer[0] in ['A', 'B', 'C', 'D', 'E', 'F', 'G']:
                answer = answer[0]
        
        return answer

    except Exception as e:
        return f"Error: {e}"

def calculate_ordinal_score(agent_choice, expected_choice, options_keys):
    """
    Calculates accuracy based on distance.
    Example: Options [A, B, C, D, E]
    If Expected 'A' and Agent 'B' -> Distance is 1. Score is high.
    If Expected 'A' and Agent 'E' -> Distance is 4. Score is low.
    """
    # 1. Map letters to indices (A=0, B=1, C=2, etc.)
    # We sort the keys to ensure A comes before B
    sorted_options = sorted(options_keys)
    
    try:
        agent_idx = sorted_options.index(agent_choice)
        expected_idx = sorted_options.index(expected_choice)
    except ValueError:
        return 0.0 # Return 0 if invalid option returned

    # 2. Calculate absolute distance
    distance = abs(agent_idx - expected_idx)
    
    # 3. Calculate max possible distance for this specific question
    # (e.g., if A,B,C, max distance is 2)
    max_distance = len(sorted_options) - 1
    
    if max_distance == 0: return 1.0 if distance == 0 else 0.0

    # 4. Normalize to a 0-1 score
    # A score of 1 means 0 distance. A score of 0 means max distance.
    score = 1 - (distance / max_distance)
    
    return score


def collapse_answer_to_stance(answer):
    """
    Collapse A-G survey answers into 3 stance buckets.

    - A, B, C -> Oppose
    - D       -> Neutral
    - E, F, G -> Support
    """
    if not isinstance(answer, str):
        return None

    normalized = answer.strip().upper()
    if normalized in {"A", "B", "C"}:
        return "Oppose"
    if normalized == "D":
        return "Neutral"
    if normalized in {"E", "F", "G"}:
        return "Support"
    return None


def calculate_exact_match_score_by_stance(agent_choice, expected_choice):
    """
    Exact-match scoring after collapsing answers to stance buckets.

    Returns:
        1.0 if collapsed stances are identical, else 0.0.
    """
    agent_stance = collapse_answer_to_stance(agent_choice)
    expected_stance = collapse_answer_to_stance(expected_choice)

    if agent_stance is None or expected_stance is None:
        return 0.0

    return 1.0 if agent_stance == expected_stance else 0.0

def survey_simulation_test():
    """
    Run survey simulation and save tidy respondent-question level outputs to CSV.

    Output files:
    - data/output/experiments/20260301/survey_simulation_results_<timestamp>.csv
    - data/output/experiments/20260301/survey_simulation_question_summary_<timestamp>.csv
    - data/output/experiments/20260301/survey_simulation_agent_answer_boxplot_<timestamp>.png
    """
    try:
        genai_client = get_gemini_client()
    except Exception as e:
        return f"Error loading API key: {e}"

    options_dict={'1':	'A','2':	'B',
    '3':	'C',
    '4':	'D',
    '5':	'E',
    '6':	'F',
    '7':	'G'}

    file_path = DATA_DIR / "yougov_survey_data" / "YouGovProcessedData_train.csv"
    survey_data = load_survey_data(file_path)

    if survey_data is None or survey_data.empty:
        print("No survey data available for simulation.")
        return None

    # Set respondent_sample_n to an integer (e.g., 5) for quick tests.
    # Keep it as None to run on all respondents.
    respondent_sample_n = 100
    if respondent_sample_n is not None:
        sample_n = min(respondent_sample_n, len(survey_data))
        survey_data = survey_data.sample(n=sample_n, replace=False, random_state=1)
    all_persona_texts = create_persona_text_for_people_agent(survey_data)

    # for respondent_id, persona_text in all_persona_texts.items():
    #     print(f"Respondent ID: {respondent_id}")
    #     print("Persona Description:")
    #     print(persona_text)
    #     print("\n" + "="*80 + "\n")

    try:
        from survey_dict import SURVEY_QUESTIONS
    except ImportError:
        from survey_dict import SURVEY_QUESTIONS

    all_results = []
    per_question_summary = []
    question_sequence_ids = []
    run_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    for q in SURVEY_QUESTIONS:
        scores=[]
        question_id = q.get('id', q.get('col_name', 'unknown_question'))
        question_text = q.get('text', '')
        question_sequence_ids.append(question_id)

        for index,row in survey_data.iterrows():
            respondent_id = int(row['ID'])
            answer = ask_agent_survey_question_acc(
                persona_description=all_persona_texts[respondent_id],
                question_data=q,
                provider='gemini',
                model_name=None
            )
            
            if isinstance(answer, str) and answer.startswith("Error:"):
                raise RuntimeError(
                    f"Stopping simulation due to Gemini/API error for respondent {respondent_id}, "
                    f"question {question_id}: {answer}"
                )

            expected=row[q['col_name']]
            expected=options_dict[str(int(expected))]
            score = calculate_ordinal_score(answer, expected, q['options'].keys())
            scores.append(score)

            all_results.append(
                {
                    "run_timestamp": run_timestamp,
                    "question_id": question_id,
                    "question_text": question_text,
                    "question_column": q.get('col_name', ''),
                    "respondent_id": respondent_id,
                    "persona_text": all_persona_texts[respondent_id],
                    "agent_answer": answer,
                    "expected_answer": expected,
                    "ordinal_accuracy_score": round(score, 4),
                    "provider": "gemini",
                    "model_name": "gemini-2.5-flash",
                }
            )

            # print(f"Question: {q['text']}")
            # print(f"Agent Answer: {answer}")
            # print(f"Expected Answer: {expected}")
            # print(f"Exact Match Score (stance-collapsed): {score:.2f}")
            # print("-"*40)

        average_score = sum(scores) / len(scores) if scores else 0
        per_question_summary.append(
            {
                "run_timestamp": run_timestamp,
                "question_id": question_id,
                "question_text": question_text,
                "num_respondents": len(scores),
                "average_ordinal_accuracy_score": round(average_score, 4),
            }
        )
        print(f"Average Ordinal Accuracy Score across all agents: {average_score:.2f}")

    output_dir = DATA_DIR / "output" / "experiments" / "20260301"
    output_dir.mkdir(parents=True, exist_ok=True)

    results_df = pd.DataFrame(all_results)
    summary_df = pd.DataFrame(per_question_summary)

    results_path = output_dir / f"survey_simulation_results_{run_timestamp}.csv"
    summary_path = output_dir / f"survey_simulation_question_summary_{run_timestamp}.csv"
    boxplot_path = output_dir / f"survey_simulation_agent_answer_boxplot_{run_timestamp}.png"

    results_df.to_csv(results_path, index=False)
    summary_df.to_csv(summary_path, index=False)

    boxplot_data = []
    boxplot_labels = []
    for idx, question_id in enumerate(question_sequence_ids, start=1):
        question_scores = results_df.loc[
            results_df["question_id"] == question_id,
            "ordinal_accuracy_score",
        ].tolist()
        question_scores = [score for score in question_scores if pd.notna(score)]

        if question_scores:
            boxplot_data.append(question_scores)
            boxplot_labels.append(f"Q{idx}")

    if boxplot_data:
        fig, ax = plt.subplots(figsize=(12, 6))
        ax.boxplot(boxplot_data, whis=[5, 95], tick_labels=boxplot_labels)
        ax.set_xlabel("Question")
        ax.set_ylabel("Ordinal Accuracy Score (0 to 1)")
        ax.set_title("Ordinal Accuracy Distribution by Question")
        ax.set_ylim(-0.05, 1.05)
        ax.grid(True, axis="y", alpha=0.3)
        plt.tight_layout()
        fig.savefig(boxplot_path, dpi=150, bbox_inches='tight')
        plt.close(fig)
    else:
        boxplot_path = None

    print("\nSaved simulation outputs:")
    print(f"- Detailed row-level results: {results_path}")
    print(f"- Per-question summary: {summary_path}")
    if boxplot_path is not None:
        print(f"- Boxplot figure: {boxplot_path}")
    else:
        print("- Boxplot figure: skipped (no valid answer scores)")

    return results_df, summary_df


def _build_profile_dict_from_row(row):
    """Build a mapped profile dict (coded -> readable) for one survey row."""
    p_list = [
        "age", "male_dummy", "tprofile_GOR", "profile_education_level",
        "tprofile_gross_household", "ethnicity_R", "parent_dummy", "Vote2019R",
        "pastvote_EURef", "Political_Left_Right", "Selftransc_Val", "Selfenh_Values",
        "Openness", "ConformTrad", "SDO", "EDO", "RWA",
    ]

    try:
        from survey_dict import PROFILE_DICT
    except ImportError:
        from sandbox.ajay_sandbox.survey_dict import PROFILE_DICT

    profile = {}
    for key in p_list:
        if key in [
            "age", "Selftransc_Val", "Selfenh_Values", "Openness",
            "ConformTrad", "SDO", "EDO", "RWA",
        ]:
            profile[key] = row[key]
        else:
            profile[key] = PROFILE_DICT[key][str(round(row[key]))]
    return profile


def create_persona_variants_for_people_agent(survey_data):
    """
    Create deterministic persona variants from the same mapped survey fields.

    Variants:
    - full_persona: existing rich narrative (all attributes)
    - demographics_politics_only: demographics + politics only
    - values_only: value/worldview only
    - compressed_full: all attributes preserved in concise structured text
    """
    all_variants = {
        "full_persona": {},
        "demographics_politics_only": {},
        "values_only": {},
        "compressed_full": {},
    }

    for _, row in survey_data.iterrows():
        respondent_id = int(row["ID"])
        p = _build_profile_dict_from_row(row)

        demographics_politics = (
            f"Demographically, I am a {p['age']}-year-old {p['male_dummy']} living in the {p['tprofile_GOR']}, United Kingdom. "
            f"My ethnic background is {p['ethnicity_R']}, and I hold a {p['profile_education_level']}. "
            f"Financially, my gross household income falls into the {p['tprofile_gross_household']} bracket. "
            f"Regarding my family status, I {p['parent_dummy']} a parent. "
            f"Politically, I position myself on the {p['Political_Left_Right']} of the spectrum. "
            f"In the 2019 General Election, I cast my vote for the {p['Vote2019R']}. "
            f"Looking back at the EU Referendum, {p['pastvote_EURef']}."
        )

        values_only = (
            "When it comes to my core values and worldview: "
            f"{get_narrative(p['Selftransc_Val'], 'Selftransc_Val')} "
            f"{get_narrative(p['Selfenh_Values'], 'Selfenh_Values')} "
            f"{get_narrative(p['Openness'], 'Openness')} "
            f"{get_narrative(p['ConformTrad'], 'ConformTrad')} "
            f"{get_narrative(p['SDO'], 'SDO')} "
            f"{get_narrative(p['EDO'], 'EDO')} "
            f"{get_narrative(p['RWA'], 'RWA')}"
        )

        compressed_full = (
            "PROFILE (compressed): "
            f"age={p['age']}; sex={p['male_dummy']}; region={p['tprofile_GOR']}; "
            f"ethnicity={p['ethnicity_R']}; education={p['profile_education_level']}; "
            f"income={p['tprofile_gross_household']}; parent={p['parent_dummy']}; "
            f"left_right={p['Political_Left_Right']}; vote2019={p['Vote2019R']}; eu_ref={p['pastvote_EURef']}; "
            f"Selftransc_Val={p['Selftransc_Val']}; Selfenh_Values={p['Selfenh_Values']}; Openness={p['Openness']}; "
            f"ConformTrad={p['ConformTrad']}; SDO={p['SDO']}; EDO={p['EDO']}; RWA={p['RWA']}."
        )

        all_variants["full_persona"][respondent_id] = format_persona_from_row(p)
        all_variants["demographics_politics_only"][respondent_id] = demographics_politics
        all_variants["values_only"][respondent_id] = values_only
        all_variants["compressed_full"][respondent_id] = compressed_full

    return all_variants


def ask_agent_survey_question_acc_neutral_calibrated(
    persona_description,
    question_data,
    provider="gemini",
    model_name=None,
    temperature=0.0,
):
    """
    Ask one survey question with a neutral-calibrated prompt (question text unchanged).

    Notes:
    - Keeps survey question/options exactly as-is.
    - Encourages selecting D when persona is genuinely mixed/uncertain.
    - Designed for deterministic evaluation when temperature=0.0.
    """
    prompt = f"""
    You are participating in a demographic survey.

    YOUR PERSONA:
    {persona_description}

    INSTRUCTIONS:
    1. Read the survey question and options exactly as shown.
    2. Select the option (A-G) that best matches your persona.
    3. If your persona is genuinely mixed, uncertain, or balanced between support and opposition, choose D (Neutral).
    4. Do not force support or opposition when the persona does not clearly lean.
    5. Output ONLY the single letter A, B, C, D, E, F, or G.

    QUESTION: {question_data['text']}

    OPTIONS:
    A) {question_data['options'].get('A', '')}
    B) {question_data['options'].get('B', '')}
    C) {question_data['options'].get('C', '')}
    D) {question_data['options'].get('D', '')}
    E) {question_data['options'].get('E', '')}
    F) {question_data['options'].get('F', '')}
    G) {question_data['options'].get('G', '')}

    YOUR CHOICE (Letter Only):
    """

    if provider.lower() != "gemini":
        return "Error: Unknown Provider"

    system_instruction = (
        "You are a survey respondent. Follow persona faithfully and use Neutral (D) when stance is mixed."
    )

    try:
        config = types.GenerateContentConfig(
            temperature=temperature,
            max_output_tokens=5,
            system_instruction=system_instruction,
        )
        raw_content = gemini_generate_content_with_retry(
            prompt=prompt,
            model_name=model_name if model_name else "gemini-2.5-flash",
            config=config,
        )

        answer = raw_content.strip().upper()
        if len(answer) > 1 and answer[0] in ["A", "B", "C", "D", "E", "F", "G"]:
            answer = answer[0]
        return answer
    except Exception as e:
        return f"Error: {e}"


def run_neutral_calibrated_persona_ablation_experiment(
    respondent_sample_n=100,
    random_state=1,
    provider="gemini",
    model_name=None,
    temperature=0.0,
    persona_modes=None,
    output_dir=None,
    save_outputs=True,
):
    """
    Run controlled ablation over persona variants with neutral-calibrated prompting.

    Keeps survey question text unchanged while varying persona representation and
    LLM prompting/decoding settings.

    Outputs:
    - detail CSV (one row per variant-question-respondent)
    - summary CSV (mean exact-match score by variant)
    - stance-share comparison CSV (expected vs predicted by variant/question)
    """
    file_path = DATA_DIR / "yougov_survey_data" / "YouGovProcessedData_train.csv"
    survey_data = load_survey_data(file_path)
    if survey_data is None or survey_data.empty:
        raise ValueError("No survey data available for neutral-calibrated ablation.")

    if respondent_sample_n is not None:
        sample_n = min(int(respondent_sample_n), len(survey_data))
        survey_data = survey_data.sample(n=sample_n, replace=False, random_state=random_state)

    persona_variant_maps = create_persona_variants_for_people_agent(survey_data)
    if persona_modes is None:
        persona_modes = [
            "full_persona",
            "demographics_politics_only",
            "values_only",
            "compressed_full",
        ]

    unknown_modes = [mode for mode in persona_modes if mode not in persona_variant_maps]
    if unknown_modes:
        raise ValueError(f"Unknown persona modes: {unknown_modes}")

    try:
        from survey_dict import SURVEY_QUESTIONS
    except ImportError:
        from sandbox.ajay_sandbox.survey_dict import SURVEY_QUESTIONS

    options_dict = {
        "1": "A", "2": "B", "3": "C", "4": "D", "5": "E", "6": "F", "7": "G"
    }

    run_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    detail_rows = []

    for mode in persona_modes:
        persona_map = persona_variant_maps[mode]
        print(f"\nRunning mode: {mode}")

        for q in SURVEY_QUESTIONS:
            question_id = q.get("id", q.get("col_name", "unknown_question"))
            question_text = q.get("text", "")

            for _, row in survey_data.iterrows():
                respondent_id = int(row["ID"])
                expected = options_dict[str(int(row[q["col_name"]]))]

                answer = ask_agent_survey_question_acc_neutral_calibrated(
                    persona_description=persona_map[respondent_id],
                    question_data=q,
                    provider=provider,
                    model_name=model_name,
                    temperature=temperature,
                )

                if isinstance(answer, str) and answer.startswith("Error:"):
                    raise RuntimeError(
                        f"Ablation stopped due to API error for mode={mode}, respondent={respondent_id}, "
                        f"question={question_id}: {answer}"
                    )

                score = calculate_exact_match_score_by_stance(answer, expected)
                detail_rows.append(
                    {
                        "run_timestamp": run_timestamp,
                        "experiment_name": "neutral_calibrated_persona_ablation",
                        "persona_mode": mode,
                        "question_id": question_id,
                        "question_text": question_text,
                        "question_column": q.get("col_name", ""),
                        "respondent_id": respondent_id,
                        "agent_answer": answer,
                        "expected_answer": expected,
                        "exact_match_score": float(score),
                        "provider": provider,
                        "model_name": model_name if model_name else "gemini-2.5-flash",
                        "temperature": float(temperature),
                    }
                )

    detail_df = pd.DataFrame(detail_rows)
    if detail_df.empty:
        raise RuntimeError("Ablation run produced no rows.")

    summary_df = (
        detail_df.groupby("persona_mode", as_index=False)
        .agg(
            n_rows=("exact_match_score", "size"),
            mean_exact_match_score=("exact_match_score", "mean"),
        )
        .sort_values("mean_exact_match_score", ascending=False)
        .reset_index(drop=True)
    )

    stance_map = {
        "A": "Oppose", "B": "Oppose", "C": "Oppose",
        "D": "Neutral",
        "E": "Support", "F": "Support", "G": "Support",
    }
    stance_df = detail_df.copy()
    stance_df["expected_stance"] = stance_df["expected_answer"].map(stance_map)
    stance_df["predicted_stance"] = stance_df["agent_answer"].map(stance_map)

    expected_share = (
        stance_df.groupby(["persona_mode", "question_id", "expected_stance"]).size()
        .rename("expected_count")
        .reset_index()
        .rename(columns={"expected_stance": "stance"})
    )
    predicted_share = (
        stance_df.groupby(["persona_mode", "question_id", "predicted_stance"]).size()
        .rename("predicted_count")
        .reset_index()
        .rename(columns={"predicted_stance": "stance"})
    )
    stance_comparison_df = expected_share.merge(
        predicted_share,
        on=["persona_mode", "question_id", "stance"],
        how="outer",
    ).fillna(0)

    q_totals = (
        stance_df.groupby(["persona_mode", "question_id"]).size().rename("n_rows").reset_index()
    )
    stance_comparison_df = stance_comparison_df.merge(
        q_totals, on=["persona_mode", "question_id"], how="left"
    )
    stance_comparison_df["expected_share"] = stance_comparison_df["expected_count"] / stance_comparison_df["n_rows"]
    stance_comparison_df["predicted_share"] = stance_comparison_df["predicted_count"] / stance_comparison_df["n_rows"]
    stance_comparison_df["share_delta_pred_minus_expected"] = (
        stance_comparison_df["predicted_share"] - stance_comparison_df["expected_share"]
    )

    base_output_dir = (
        DATA_DIR / "output" / "experiments" / "20260306"
        if output_dir is None
        else Path(output_dir)
    )
    base_output_dir.mkdir(parents=True, exist_ok=True)

    detail_csv_path = None
    summary_csv_path = None
    stance_comparison_csv_path = None
    neutral_gap_plot_path = None

    if save_outputs:
        detail_csv_path = base_output_dir / f"survey_simulation_neutral_calibrated_persona_ablation_detail_{run_timestamp}.csv"
        summary_csv_path = base_output_dir / f"survey_simulation_neutral_calibrated_persona_ablation_summary_{run_timestamp}.csv"
        stance_comparison_csv_path = base_output_dir / f"survey_simulation_neutral_calibrated_persona_ablation_stance_comparison_{run_timestamp}.csv"

        detail_df.to_csv(detail_csv_path, index=False)
        summary_df.to_csv(summary_csv_path, index=False)
        stance_comparison_df.to_csv(stance_comparison_csv_path, index=False)

        neutral_gap_df = stance_comparison_df[
            stance_comparison_df["stance"] == "Neutral"
        ].copy()
        neutral_gap_df = (
            neutral_gap_df.groupby("persona_mode", as_index=False)
            .agg(mean_neutral_share_delta=("share_delta_pred_minus_expected", "mean"))
            .sort_values("mean_neutral_share_delta", ascending=False)
        )

        if not neutral_gap_df.empty:
            fig, ax = plt.subplots(figsize=(10, 5))
            ax.bar(
                neutral_gap_df["persona_mode"].astype(str),
                neutral_gap_df["mean_neutral_share_delta"].astype(float),
            )
            ax.axhline(0.0, color="black", linestyle="--", linewidth=1)
            ax.set_xlabel("Persona Mode")
            ax.set_ylabel("Mean Predicted-Expected Neutral Share")
            ax.set_title("Neutral Share Gap by Persona Mode (Neutral-Calibrated Prompt)")
            ax.grid(True, axis="y", alpha=0.3)
            plt.xticks(rotation=15, ha="right")
            plt.tight_layout()
            neutral_gap_plot_path = base_output_dir / f"survey_simulation_neutral_calibrated_persona_ablation_neutral_gap_{run_timestamp}.png"
            fig.savefig(neutral_gap_plot_path, dpi=150, bbox_inches="tight")
            plt.close(fig)

        print(f"Saved ablation detail CSV: {detail_csv_path}")
        print(f"Saved ablation summary CSV: {summary_csv_path}")
        print(f"Saved ablation stance-comparison CSV: {stance_comparison_csv_path}")
        if neutral_gap_plot_path is not None:
            print(f"Saved ablation neutral-gap PNG: {neutral_gap_plot_path}")

    print("\nAblation summary (mean exact-match score by persona mode):")
    print(summary_df.to_string(index=False))

    return {
        "detail_df": detail_df,
        "summary_df": summary_df,
        "stance_comparison_df": stance_comparison_df,
        "detail_csv_path": detail_csv_path,
        "summary_csv_path": summary_csv_path,
        "stance_comparison_csv_path": stance_comparison_csv_path,
        "neutral_gap_plot_path": neutral_gap_plot_path,
    }


def ask_agent_survey_question_acc_calibration_level(
    persona_description,
    question_data,
    calibration_level="baseline",
    provider="gemini",
    model_name=None,
    temperature=0.0,
):
    """
    Ask one survey question using a selectable neutral-calibration level.

    calibration_level:
    - baseline: no extra neutral guidance
    - soft: choose D only when genuinely mixed
    - strong: stronger instruction to select D when mixed/uncertain
    """
    if provider.lower() != "gemini":
        return "Error: Unknown Provider"

    if calibration_level == "baseline":
        extra_instructions = (
            "3. Select the option (A-G) that ALIGNS BEST with your persona's worldview.\n"
            "4. Output ONLY the letter of your choice. Do not explain."
        )
        system_instruction = "You are a survey respondent. You strictly follow persona instructions."
    elif calibration_level == "soft":
        extra_instructions = (
            "3. Select the option (A-G) that best matches your persona.\n"
            "4. If your persona is genuinely mixed between support and opposition, you may choose D (Neutral).\n"
            "5. If your persona has a clear lean, do not choose D.\n"
            "6. Output ONLY the letter of your choice. Do not explain."
        )
        system_instruction = (
            "You are a survey respondent. Follow persona faithfully and use D only for truly mixed positions."
        )
    elif calibration_level == "strong":
        extra_instructions = (
            "3. Select the option (A-G) that best matches your persona.\n"
            "4. If your persona is mixed, uncertain, or balanced, choose D (Neutral).\n"
            "5. Do not force support or opposition when the persona does not clearly lean.\n"
            "6. Output ONLY the letter of your choice. Do not explain."
        )
        system_instruction = (
            "You are a survey respondent. Follow persona faithfully and use Neutral (D) when stance is mixed."
        )
    else:
        return "Error: Unknown calibration level"

    prompt = f"""
    You are participating in a demographic survey.

    YOUR PERSONA:
    {persona_description}

    INSTRUCTIONS:
    1. Read the question below.
    2. Keep the survey question and options exactly as written.
    {extra_instructions}

    QUESTION: {question_data['text']}

    OPTIONS:
    A) {question_data['options'].get('A', '')}
    B) {question_data['options'].get('B', '')}
    C) {question_data['options'].get('C', '')}
    D) {question_data['options'].get('D', '')}
    E) {question_data['options'].get('E', '')}
    F) {question_data['options'].get('F', '')}
    G) {question_data['options'].get('G', '')}

    YOUR CHOICE (Letter Only):
    """

    try:
        config = types.GenerateContentConfig(
            temperature=temperature,
            max_output_tokens=5,
            system_instruction=system_instruction,
        )
        raw_content = gemini_generate_content_with_retry(
            prompt=prompt,
            model_name=model_name if model_name else "gemini-2.5-flash",
            config=config,
        )

        answer = raw_content.strip().upper()
        if len(answer) > 1 and answer[0] in ["A", "B", "C", "D", "E", "F", "G"]:
            answer = answer[0]
        return answer
    except Exception as e:
        return f"Error: {e}"


def run_neutral_calibration_sweep_full_persona(
    respondent_sample_n=30,
    random_state=1,
    calibration_levels=None,
    provider="gemini",
    model_name=None,
    temperature=0.0,
    output_dir=None,
    save_outputs=True,
    continue_on_error=True,
    max_total_errors=40,
    max_consecutive_errors=12,
):
    """
    Sweep neutral-calibration levels while keeping persona mode fixed to full_persona.

    Designed to tune neutral calibration without re-running persona-mode ablation.
    """
    if calibration_levels is None:
        calibration_levels = ["baseline", "soft", "strong"]

    file_path = DATA_DIR / "yougov_survey_data" / "YouGovProcessedData_train.csv"
    survey_data = load_survey_data(file_path)
    if survey_data is None or survey_data.empty:
        raise ValueError("No survey data available for calibration sweep.")

    if respondent_sample_n is not None:
        sample_n = min(int(respondent_sample_n), len(survey_data))
        survey_data = survey_data.sample(n=sample_n, replace=False, random_state=random_state)

    full_persona_map = create_persona_variants_for_people_agent(survey_data)["full_persona"]

    try:
        from survey_dict import SURVEY_QUESTIONS
    except ImportError:
        from sandbox.ajay_sandbox.survey_dict import SURVEY_QUESTIONS

    options_dict = {
        "1": "A", "2": "B", "3": "C", "4": "D", "5": "E", "6": "F", "7": "G"
    }

    run_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    detail_rows = []
    error_rows = []
    total_errors = 0
    consecutive_errors = 0
    abort_run = False

    for level in calibration_levels:
        print(f"\nRunning calibration level: {level}")
        for q in SURVEY_QUESTIONS:
            question_id = q.get("id", q.get("col_name", "unknown_question"))
            question_text = q.get("text", "")

            for _, row in survey_data.iterrows():
                respondent_id = int(row["ID"])
                expected = options_dict[str(int(row[q["col_name"]]))]

                answer = ask_agent_survey_question_acc_calibration_level(
                    persona_description=full_persona_map[respondent_id],
                    question_data=q,
                    calibration_level=level,
                    provider=provider,
                    model_name=model_name,
                    temperature=temperature,
                )

                if isinstance(answer, str) and answer.startswith("Error:"):
                    total_errors += 1
                    consecutive_errors += 1
                    error_rows.append(
                        {
                            "run_timestamp": run_timestamp,
                            "calibration_level": level,
                            "question_id": question_id,
                            "respondent_id": respondent_id,
                            "error_message": answer,
                            "total_errors_so_far": total_errors,
                            "consecutive_errors_so_far": consecutive_errors,
                        }
                    )

                    should_abort = (
                        (not continue_on_error)
                        or (total_errors >= max_total_errors)
                        or (consecutive_errors >= max_consecutive_errors)
                    )
                    if should_abort:
                        abort_run = True
                        print(
                            "Aborting calibration sweep due to error threshold: "
                            f"total_errors={total_errors}/{max_total_errors}, "
                            f"consecutive_errors={consecutive_errors}/{max_consecutive_errors}"
                        )
                        break
                    continue

                consecutive_errors = 0

                score = calculate_exact_match_score_by_stance(answer, expected)
                detail_rows.append(
                    {
                        "run_timestamp": run_timestamp,
                        "experiment_name": "neutral_calibration_sweep_full_persona",
                        "calibration_level": level,
                        "persona_mode": "full_persona",
                        "question_id": question_id,
                        "question_text": question_text,
                        "question_column": q.get("col_name", ""),
                        "respondent_id": respondent_id,
                        "agent_answer": answer,
                        "expected_answer": expected,
                        "exact_match_score": float(score),
                        "provider": provider,
                        "model_name": model_name if model_name else "gemini-2.5-flash",
                        "temperature": float(temperature),
                    }
                )

            if abort_run:
                break

        if abort_run:
            break

    detail_df = pd.DataFrame(detail_rows)
    error_df = pd.DataFrame(error_rows)
    if detail_df.empty:
        raise RuntimeError(
            "Calibration sweep produced no successful rows. "
            f"Captured errors: {len(error_df)}"
        )

    summary_df = (
        detail_df.groupby("calibration_level", as_index=False)
        .agg(
            n_rows=("exact_match_score", "size"),
            mean_exact_match_score=("exact_match_score", "mean"),
        )
        .sort_values("mean_exact_match_score", ascending=False)
        .reset_index(drop=True)
    )

    stance_map = {
        "A": "Oppose", "B": "Oppose", "C": "Oppose",
        "D": "Neutral",
        "E": "Support", "F": "Support", "G": "Support",
    }
    stance_df = detail_df.copy()
    stance_df["expected_stance"] = stance_df["expected_answer"].map(stance_map)
    stance_df["predicted_stance"] = stance_df["agent_answer"].map(stance_map)

    expected_counts = (
        stance_df.groupby(["calibration_level", "question_id", "expected_stance"]).size()
        .rename("expected_count")
        .reset_index()
        .rename(columns={"expected_stance": "stance"})
    )
    predicted_counts = (
        stance_df.groupby(["calibration_level", "question_id", "predicted_stance"]).size()
        .rename("predicted_count")
        .reset_index()
        .rename(columns={"predicted_stance": "stance"})
    )
    stance_comparison_df = expected_counts.merge(
        predicted_counts,
        on=["calibration_level", "question_id", "stance"],
        how="outer",
    ).fillna(0)

    totals = (
        stance_df.groupby(["calibration_level", "question_id"]).size().rename("n_rows").reset_index()
    )
    stance_comparison_df = stance_comparison_df.merge(
        totals,
        on=["calibration_level", "question_id"],
        how="left",
    )
    stance_comparison_df["expected_share"] = stance_comparison_df["expected_count"] / stance_comparison_df["n_rows"]
    stance_comparison_df["predicted_share"] = stance_comparison_df["predicted_count"] / stance_comparison_df["n_rows"]
    stance_comparison_df["share_delta_pred_minus_expected"] = (
        stance_comparison_df["predicted_share"] - stance_comparison_df["expected_share"]
    )

    neutral_gap_summary_df = (
        stance_comparison_df[stance_comparison_df["stance"] == "Neutral"]
        .groupby("calibration_level", as_index=False)
        .agg(
            mean_expected_neutral_share=("expected_share", "mean"),
            mean_predicted_neutral_share=("predicted_share", "mean"),
            mean_neutral_share_delta=("share_delta_pred_minus_expected", "mean"),
        )
        .sort_values("mean_neutral_share_delta")
    )

    support_gap_summary_df = (
        stance_comparison_df[stance_comparison_df["stance"] == "Support"]
        .groupby("calibration_level", as_index=False)
        .agg(
            mean_expected_support_share=("expected_share", "mean"),
            mean_predicted_support_share=("predicted_share", "mean"),
            mean_support_share_delta=("share_delta_pred_minus_expected", "mean"),
        )
        .sort_values("mean_support_share_delta", ascending=False)
    )

    base_output_dir = (
        DATA_DIR / "output" / "experiments" / "20260306"
        if output_dir is None
        else Path(output_dir)
    )
    base_output_dir.mkdir(parents=True, exist_ok=True)

    detail_csv_path = None
    summary_csv_path = None
    stance_comparison_csv_path = None
    neutral_gap_summary_csv_path = None
    support_gap_summary_csv_path = None
    calibration_neutral_gap_plot_path = None
    error_csv_path = None

    if save_outputs:
        detail_csv_path = base_output_dir / f"survey_simulation_neutral_calibration_sweep_full_persona_detail_{run_timestamp}.csv"
        summary_csv_path = base_output_dir / f"survey_simulation_neutral_calibration_sweep_full_persona_summary_{run_timestamp}.csv"
        stance_comparison_csv_path = base_output_dir / f"survey_simulation_neutral_calibration_sweep_full_persona_stance_comparison_{run_timestamp}.csv"
        neutral_gap_summary_csv_path = base_output_dir / f"survey_simulation_neutral_calibration_sweep_full_persona_neutral_gap_summary_{run_timestamp}.csv"
        support_gap_summary_csv_path = base_output_dir / f"survey_simulation_neutral_calibration_sweep_full_persona_support_gap_summary_{run_timestamp}.csv"
        error_csv_path = base_output_dir / f"survey_simulation_neutral_calibration_sweep_full_persona_errors_{run_timestamp}.csv"

        detail_df.to_csv(detail_csv_path, index=False)
        summary_df.to_csv(summary_csv_path, index=False)
        stance_comparison_df.to_csv(stance_comparison_csv_path, index=False)
        neutral_gap_summary_df.to_csv(neutral_gap_summary_csv_path, index=False)
        support_gap_summary_df.to_csv(support_gap_summary_csv_path, index=False)
        error_df.to_csv(error_csv_path, index=False)

        fig, ax = plt.subplots(figsize=(8, 5))
        ax.bar(
            neutral_gap_summary_df["calibration_level"].astype(str),
            neutral_gap_summary_df["mean_neutral_share_delta"].astype(float),
        )
        ax.axhline(0.0, color="black", linestyle="--", linewidth=1)
        ax.set_xlabel("Calibration Level")
        ax.set_ylabel("Mean Predicted-Expected Neutral Share")
        ax.set_title("Neutral Share Gap by Calibration Level (Full Persona)")
        ax.grid(True, axis="y", alpha=0.3)
        plt.tight_layout()
        calibration_neutral_gap_plot_path = base_output_dir / f"survey_simulation_neutral_calibration_sweep_full_persona_neutral_gap_{run_timestamp}.png"
        fig.savefig(calibration_neutral_gap_plot_path, dpi=150, bbox_inches="tight")
        plt.close(fig)

        print(f"Saved sweep detail CSV: {detail_csv_path}")
        print(f"Saved sweep summary CSV: {summary_csv_path}")
        print(f"Saved sweep stance-comparison CSV: {stance_comparison_csv_path}")
        print(f"Saved sweep neutral-gap summary CSV: {neutral_gap_summary_csv_path}")
        print(f"Saved sweep support-gap summary CSV: {support_gap_summary_csv_path}")
        print(f"Saved sweep errors CSV: {error_csv_path}")
        print(f"Saved sweep neutral-gap PNG: {calibration_neutral_gap_plot_path}")

    print("\nCalibration sweep summary (mean exact-match score):")
    print(summary_df.to_string(index=False))
    print("\nCalibration sweep neutral-gap summary:")
    print(neutral_gap_summary_df.to_string(index=False))

    return {
        "detail_df": detail_df,
        "error_df": error_df,
        "summary_df": summary_df,
        "stance_comparison_df": stance_comparison_df,
        "neutral_gap_summary_df": neutral_gap_summary_df,
        "support_gap_summary_df": support_gap_summary_df,
        "detail_csv_path": detail_csv_path,
        "error_csv_path": error_csv_path,
        "summary_csv_path": summary_csv_path,
        "stance_comparison_csv_path": stance_comparison_csv_path,
        "neutral_gap_summary_csv_path": neutral_gap_summary_csv_path,
        "support_gap_summary_csv_path": support_gap_summary_csv_path,
        "calibration_neutral_gap_plot_path": calibration_neutral_gap_plot_path,
    }


def plot_ordinal_boxplot_from_saved_results(
    results_csv_path=None,
    output_png_path=None,
    whis=(5, 95),
    figsize=(12, 6),
):
    """
    Load a saved survey simulation CSV and plot ordinal-score boxplots (Q1..Qn).

    Parameters:
        results_csv_path (str | Path | None):
            Path to a saved survey_simulation_results_*.csv. If None, loads the
            most recent file from data/output.
        output_png_path (str | Path | None):
            Output path for PNG. If None, saves next to CSV with suffix
            '_ordinal_boxplot.png'.
        whis (tuple): Whisker percentiles for matplotlib boxplot, default (5, 95).
        figsize (tuple): Figure size, default (12, 6).

    Returns:
        tuple[pd.DataFrame, Path]: Loaded DataFrame and saved PNG path.
    """
    output_dir = DATA_DIR / "output"

    if results_csv_path is None:
        candidates = sorted(output_dir.glob("survey_simulation_results_*.csv"))
        if not candidates:
            raise FileNotFoundError(
                f"No survey_simulation_results_*.csv found in: {output_dir}"
            )
        results_csv_path = candidates[-1]
    else:
        results_csv_path = Path(results_csv_path)

    if not results_csv_path.exists():
        raise FileNotFoundError(f"Results CSV not found: {results_csv_path}")

    results_df = pd.read_csv(results_csv_path)

    required_cols = {"question_id", "ordinal_accuracy_score"}
    missing_cols = required_cols - set(results_df.columns)
    if missing_cols:
        raise ValueError(f"Results CSV missing required columns: {sorted(missing_cols)}")

    ordered_question_ids = list(dict.fromkeys(results_df["question_id"].tolist()))

    boxplot_data = []
    boxplot_labels = []
    for idx, question_id in enumerate(ordered_question_ids, start=1):
        question_scores = results_df.loc[
            results_df["question_id"] == question_id,
            "ordinal_accuracy_score",
        ].tolist()
        question_scores = [score for score in question_scores if pd.notna(score)]

        if question_scores:
            boxplot_data.append(question_scores)
            boxplot_labels.append(f"Q{idx}")

    if not boxplot_data:
        raise ValueError("No valid ordinal_accuracy_score values found to plot.")

    if output_png_path is None:
        output_png_path = results_csv_path.with_name(
            f"{results_csv_path.stem}_ordinal_boxplot.png"
        )
    else:
        output_png_path = Path(output_png_path)

    output_png_path.parent.mkdir(parents=True, exist_ok=True)

    fig, ax = plt.subplots(figsize=figsize)
    ax.boxplot(boxplot_data, whis=list(whis), tick_labels=boxplot_labels)
    ax.set_xlabel("Question")
    ax.set_ylabel("Ordinal Accuracy Score (0 to 1)")
    ax.set_title("Ordinal Accuracy Distribution by Question")
    ax.set_ylim(-0.05, 1.05)
    ax.grid(True, axis="y", alpha=0.3)
    plt.tight_layout()
    fig.savefig(output_png_path, dpi=150, bbox_inches="tight")
    plt.close(fig)

    print(f"Loaded results CSV: {results_csv_path}")
    print(f"Saved boxplot PNG: {output_png_path}")

    return results_df, output_png_path


def analyze_exact_match_errors_from_saved_results(
    results_csv_path=None,
    output_dir=None,
    save_outputs=True,
):
    """
    Full diagnosis of exact-match errors for stance-collapsed scoring.

    This function loads saved exact-match simulation results and reports:
    - global, question-level, and expected-stance error rates,
    - directional stance-flow errors (e.g., Oppose->Neutral, Neutral->Support),
    - whether Neutral is disproportionately involved in errors,
    - proximity diagnostics for expected C/E (near D) and expected D->C/E confusions.

    It also saves diagnostic CSVs and plots for downstream review.

    Parameters:
        results_csv_path (str | Path | None):
            Path to a saved survey_simulation_exact_match_results_*.csv.
            If None, latest file from output_dir is used.
        output_dir (str | Path | None):
            Base output directory. Defaults to data/output/experiments/20260306.
        save_outputs (bool):
            Whether to save diagnostics as CSV/PNG files.

    Returns:
        dict: Summary stats, diagnostic DataFrames, and optional artifact paths.
    """
    base_output_dir = (
        DATA_DIR / "output" / "experiments" / "20260306"
        if output_dir is None
        else Path(output_dir)
    )
    base_output_dir.mkdir(parents=True, exist_ok=True)

    if results_csv_path is None:
        candidates = sorted(base_output_dir.glob("survey_simulation_exact_match_results_*.csv"))
        if not candidates:
            raise FileNotFoundError(
                f"No survey_simulation_exact_match_results_*.csv found in: {base_output_dir}"
            )
        results_csv_path = candidates[-1]
    else:
        results_csv_path = Path(results_csv_path)

    if not results_csv_path.exists():
        raise FileNotFoundError(f"Results CSV not found: {results_csv_path}")

    df = pd.read_csv(results_csv_path)
    required_cols = {"question_id", "agent_answer", "expected_answer"}
    missing_cols = required_cols - set(df.columns)
    if missing_cols:
        raise ValueError(f"Results CSV missing required columns: {sorted(missing_cols)}")

    valid_answers = {"A", "B", "C", "D", "E", "F", "G"}
    df["agent_answer"] = df["agent_answer"].astype(str).str.strip().str.upper()
    df["expected_answer"] = df["expected_answer"].astype(str).str.strip().str.upper()

    df = df[
        df["agent_answer"].isin(valid_answers)
        & df["expected_answer"].isin(valid_answers)
    ].copy()

    if df.empty:
        raise ValueError("No valid A-G answer rows found in results CSV.")

    stance_map = {
        "A": "Oppose",
        "B": "Oppose",
        "C": "Oppose",
        "D": "Neutral",
        "E": "Support",
        "F": "Support",
        "G": "Support",
    }
    df["agent_stance"] = df["agent_answer"].map(stance_map)
    df["expected_stance"] = df["expected_answer"].map(stance_map)
    df["recomputed_exact_match"] = (
        df["agent_stance"] == df["expected_stance"]
    ).astype(float)
    df["is_error"] = 1.0 - df["recomputed_exact_match"]

    logic_mismatch_count = None
    if "exact_match_score" in df.columns:
        score_numeric = pd.to_numeric(df["exact_match_score"], errors="coerce").fillna(0.0)
        logic_mismatch_count = int((score_numeric.round(0) != df["recomputed_exact_match"]).sum())

    total_rows = int(len(df))
    total_errors = int(df["is_error"].sum())
    overall_error_rate = float(total_errors / total_rows) if total_rows else np.nan

    by_question_df = (
        df.groupby("question_id", as_index=False)
        .agg(
            n_rows=("is_error", "size"),
            n_errors=("is_error", "sum"),
        )
        .sort_values("n_errors", ascending=False)
    )
    by_question_df["error_rate"] = by_question_df["n_errors"] / by_question_df["n_rows"]

    by_expected_stance_df = (
        df.groupby("expected_stance", as_index=False)
        .agg(
            n_rows=("is_error", "size"),
            n_errors=("is_error", "sum"),
        )
        .sort_values("n_errors", ascending=False)
    )
    by_expected_stance_df["error_rate"] = (
        by_expected_stance_df["n_errors"] / by_expected_stance_df["n_rows"]
    )

    # Per-question neutral fragility: compare D->non-D error rate against non-D baseline.
    neutral_fragility_rows = []
    for question_id, group in df.groupby("question_id"):
        d_group = group[group["expected_answer"] == "D"]
        nond_group = group[group["expected_answer"] != "D"]

        n_expected_d = int(len(d_group))
        n_expected_nond = int(len(nond_group))

        d_to_nond_errors = int((d_group["is_error"] == 1.0).sum())
        nond_errors = int((nond_group["is_error"] == 1.0).sum())

        d_to_nond_error_rate = (
            float(d_to_nond_errors / n_expected_d) if n_expected_d else np.nan
        )
        nond_error_rate = (
            float(nond_errors / n_expected_nond) if n_expected_nond else np.nan
        )

        if pd.notna(d_to_nond_error_rate) and pd.notna(nond_error_rate) and nond_error_rate > 0:
            neutral_fragility_ratio = float(d_to_nond_error_rate / nond_error_rate)
        else:
            neutral_fragility_ratio = np.nan

        neutral_fragility_rows.append(
            {
                "question_id": question_id,
                "n_expected_D": n_expected_d,
                "n_expected_nonD": n_expected_nond,
                "n_D_to_nonD_errors": d_to_nond_errors,
                "n_nonD_errors": nond_errors,
                "D_to_nonD_error_rate": d_to_nond_error_rate,
                "nonD_error_rate": nond_error_rate,
                "neutral_fragility_ratio": neutral_fragility_ratio,
                "neutral_fragility_rate_diff": (
                    d_to_nond_error_rate - nond_error_rate
                    if pd.notna(d_to_nond_error_rate) and pd.notna(nond_error_rate)
                    else np.nan
                ),
            }
        )

    neutral_fragility_by_question_df = pd.DataFrame(neutral_fragility_rows).sort_values(
        "neutral_fragility_ratio", ascending=False, na_position="last"
    )

    # Error-only frame for directional diagnostics.
    errors_df = df[df["is_error"] == 1.0].copy()

    # Directional error flows by stance (expected -> predicted stance).
    error_flow_df = (
        errors_df.groupby(["expected_stance", "agent_stance"], as_index=False)
        .size()
        .rename(columns={"size": "count"})
        .sort_values("count", ascending=False)
    )
    if total_errors > 0:
        error_flow_df["share_of_all_errors"] = error_flow_df["count"] / total_errors
    else:
        error_flow_df["share_of_all_errors"] = np.nan

    # Expected-stance x predicted-stance matrix over all rows and error rates per expected stance.
    stance_confusion_all_df = (
        df.pivot_table(
            index="expected_stance",
            columns="agent_stance",
            values="question_id",
            aggfunc="count",
            fill_value=0,
        )
        .reset_index()
    )

    # Neutral-specific breakdowns.
    neutral_df = df[df["expected_stance"] == "Neutral"].copy()
    neutral_total = int(len(neutral_df))
    neutral_errors_df = neutral_df[neutral_df["is_error"] == 1.0].copy()
    neutral_error_count = int(len(neutral_errors_df))
    neutral_error_rate = float(neutral_error_count / neutral_total) if neutral_total else np.nan

    neutral_answer_mix_df = (
        neutral_errors_df.groupby("agent_answer", as_index=False)
        .size()
        .rename(columns={"size": "count"})
        .sort_values("count", ascending=False)
    )

    neutral_error_by_question_df = (
        neutral_errors_df.groupby("question_id", as_index=False)
        .size()
        .rename(columns={"size": "n_errors_expected_D"})
        .sort_values("n_errors_expected_D", ascending=False)
    )

    # Non-neutral expected rows predicted as neutral (opposite direction).
    nonneutral_df = df[df["expected_stance"] != "Neutral"].copy()
    nonneutral_total = int(len(nonneutral_df))
    nonneutral_to_neutral_df = nonneutral_df[nonneutral_df["agent_stance"] == "Neutral"].copy()
    nonneutral_to_neutral_count = int(len(nonneutral_to_neutral_df))
    nonneutral_to_neutral_rate = (
        float(nonneutral_to_neutral_count / nonneutral_total)
        if nonneutral_total
        else np.nan
    )

    # Neutral involvement decomposition across all errors.
    expected_neutral_pred_nonneutral_count = int(
        len(errors_df[errors_df["expected_stance"] == "Neutral"])
    )
    expected_nonneutral_pred_neutral_count = int(
        len(errors_df[errors_df["agent_stance"] == "Neutral"])
    )
    neutral_involved_errors = (
        expected_neutral_pred_nonneutral_count
        + expected_nonneutral_pred_neutral_count
    )
    neutral_involved_error_share = (
        float(neutral_involved_errors / total_errors) if total_errors else np.nan
    )

    neutral_error_components_df = pd.DataFrame(
        [
            {
                "component": "expected_neutral_pred_nonneutral",
                "count": expected_neutral_pred_nonneutral_count,
                "share_of_all_errors": (
                    expected_neutral_pred_nonneutral_count / total_errors
                    if total_errors
                    else np.nan
                ),
            },
            {
                "component": "expected_nonneutral_pred_neutral",
                "count": expected_nonneutral_pred_neutral_count,
                "share_of_all_errors": (
                    expected_nonneutral_pred_neutral_count / total_errors
                    if total_errors
                    else np.nan
                ),
            },
            {
                "component": "all_neutral_involved_errors",
                "count": neutral_involved_errors,
                "share_of_all_errors": neutral_involved_error_share,
            },
        ]
    )

    # Fine-grained letter-level proximity diagnostics around D using C/E.
    letter_error_flow_df = (
        errors_df.groupby(["expected_answer", "agent_answer"], as_index=False)
        .size()
        .rename(columns={"size": "count"})
        .sort_values("count", ascending=False)
    )

    def _near_neutral_metrics(expected_letter):
        subset = df[df["expected_answer"] == expected_letter]
        total = int(len(subset))
        if total == 0:
            return {
                "expected_answer": expected_letter,
                "n_rows": 0,
                "n_errors": 0,
                "error_rate": np.nan,
                "n_predicted_D": 0,
                "predicted_D_rate_within_expected": np.nan,
                "share_of_errors_predicted_D": np.nan,
            }

        errors_subset = subset[subset["is_error"] == 1.0]
        n_errors = int(len(errors_subset))
        to_d = int((subset["agent_answer"] == "D").sum())
        to_d_errors = int(((errors_subset["agent_answer"] == "D")).sum())
        return {
            "expected_answer": expected_letter,
            "n_rows": total,
            "n_errors": n_errors,
            "error_rate": float(n_errors / total),
            "n_predicted_D": to_d,
            "predicted_D_rate_within_expected": float(to_d / total),
            "share_of_errors_predicted_D": (
                float(to_d_errors / n_errors) if n_errors else np.nan
            ),
        }

    c_e_neutral_proximity_df = pd.DataFrame(
        [_near_neutral_metrics("C"), _near_neutral_metrics("E")]
    )

    # Additional D<->(C/E) directional counts.
    d_to_c_or_e_count = int(
        len(
            errors_df[
                (errors_df["expected_answer"] == "D")
                & (errors_df["agent_answer"].isin(["C", "E"]))
            ]
        )
    )
    c_or_e_to_d_count = int(
        len(
            errors_df[
                (errors_df["expected_answer"].isin(["C", "E"]))
                & (errors_df["agent_answer"] == "D")
            ]
        )
    )

    print("\nExact-match error diagnostics")
    print(f"- Loaded: {results_csv_path}")
    print(f"- Total rows: {total_rows}")
    print(f"- Total errors: {total_errors} ({overall_error_rate:.4f})")
    if logic_mismatch_count is not None:
        print(f"- Score logic mismatch rows (saved vs recomputed): {logic_mismatch_count}")

    print("\nTop questions by error count:")
    print(by_question_df[["question_id", "n_errors", "error_rate"]].head(10).to_string(index=False))

    print("\nExpected-stance error rates:")
    print(by_expected_stance_df[["expected_stance", "n_errors", "error_rate"]].to_string(index=False))

    print("\nPer-question neutral fragility (D->non-D vs non-D baseline):")
    if not neutral_fragility_by_question_df.empty:
        print(
            neutral_fragility_by_question_df[
                [
                    "question_id",
                    "D_to_nonD_error_rate",
                    "nonD_error_rate",
                    "neutral_fragility_ratio",
                    "neutral_fragility_rate_diff",
                ]
            ]
            .head(10)
            .to_string(index=False)
        )

    print("\nTop error flows (expected stance -> predicted stance):")
    if not error_flow_df.empty:
        print(
            error_flow_df[
                ["expected_stance", "agent_stance", "count", "share_of_all_errors"]
            ]
            .head(10)
            .to_string(index=False)
        )

    print("\nExpected D (Neutral) diagnostics:")
    print(f"- Rows with expected D: {neutral_total}")
    print(f"- Errors when expected D: {neutral_error_count} ({neutral_error_rate:.4f})")
    if not neutral_answer_mix_df.empty:
        print("- Agent answers during expected-D errors:")
        print(neutral_answer_mix_df.head(10).to_string(index=False))

    print("\nNeutral-involved error decomposition:")
    print(
        neutral_error_components_df[
            ["component", "count", "share_of_all_errors"]
        ].to_string(index=False)
    )

    print("\nNon-neutral expected predicted as Neutral:")
    print(
        f"- Count: {nonneutral_to_neutral_count} | "
        f"Rate within non-neutral expected rows: {nonneutral_to_neutral_rate:.4f}"
    )

    print("\nC/E proximity-to-Neutral diagnostics:")
    print(c_e_neutral_proximity_df.to_string(index=False))
    print(
        f"- expected D -> predicted C/E errors: {d_to_c_or_e_count}\n"
        f"- expected C/E -> predicted D errors: {c_or_e_to_d_count}"
    )

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    by_question_csv_path = None
    by_stance_csv_path = None
    neutral_mix_csv_path = None
    neutral_by_question_csv_path = None
    error_flow_csv_path = None
    stance_confusion_all_csv_path = None
    neutral_components_csv_path = None
    c_e_proximity_csv_path = None
    letter_error_flow_csv_path = None
    neutral_fragility_by_question_csv_path = None
    error_rate_by_question_png_path = None
    neutral_error_answer_mix_png_path = None
    stance_error_flow_png_path = None
    neutral_component_png_path = None
    neutral_fragility_ratio_png_path = None

    if save_outputs:
        by_question_csv_path = base_output_dir / f"survey_simulation_exact_match_error_by_question_{timestamp}.csv"
        by_stance_csv_path = base_output_dir / f"survey_simulation_exact_match_error_by_expected_stance_{timestamp}.csv"
        neutral_mix_csv_path = base_output_dir / f"survey_simulation_exact_match_expected_D_error_answer_mix_{timestamp}.csv"
        neutral_by_question_csv_path = base_output_dir / f"survey_simulation_exact_match_expected_D_error_by_question_{timestamp}.csv"
        error_flow_csv_path = base_output_dir / f"survey_simulation_exact_match_error_flow_by_stance_{timestamp}.csv"
        stance_confusion_all_csv_path = base_output_dir / f"survey_simulation_exact_match_stance_confusion_all_{timestamp}.csv"
        neutral_components_csv_path = base_output_dir / f"survey_simulation_exact_match_neutral_error_components_{timestamp}.csv"
        c_e_proximity_csv_path = base_output_dir / f"survey_simulation_exact_match_CE_neutral_proximity_{timestamp}.csv"
        letter_error_flow_csv_path = base_output_dir / f"survey_simulation_exact_match_letter_error_flow_{timestamp}.csv"
        neutral_fragility_by_question_csv_path = base_output_dir / f"survey_simulation_exact_match_neutral_fragility_by_question_{timestamp}.csv"

        by_question_df.to_csv(by_question_csv_path, index=False)
        by_expected_stance_df.to_csv(by_stance_csv_path, index=False)
        neutral_answer_mix_df.to_csv(neutral_mix_csv_path, index=False)
        neutral_error_by_question_df.to_csv(neutral_by_question_csv_path, index=False)
        error_flow_df.to_csv(error_flow_csv_path, index=False)
        stance_confusion_all_df.to_csv(stance_confusion_all_csv_path, index=False)
        neutral_error_components_df.to_csv(neutral_components_csv_path, index=False)
        c_e_neutral_proximity_df.to_csv(c_e_proximity_csv_path, index=False)
        letter_error_flow_df.to_csv(letter_error_flow_csv_path, index=False)
        neutral_fragility_by_question_df.to_csv(neutral_fragility_by_question_csv_path, index=False)

        # Plot 1: per-question error rate
        plot_df = by_question_df.sort_values("error_rate", ascending=False).copy()
        fig, ax = plt.subplots(figsize=(10, 5))
        ax.bar(plot_df["question_id"].astype(str), plot_df["error_rate"].astype(float))
        ax.set_xlabel("Question")
        ax.set_ylabel("Error Rate")
        ax.set_title("Exact-Match Error Rate by Question")
        ax.set_ylim(0.0, 1.0)
        ax.grid(True, axis="y", alpha=0.3)
        plt.tight_layout()
        error_rate_by_question_png_path = base_output_dir / f"survey_simulation_exact_match_error_rate_by_question_{timestamp}.png"
        fig.savefig(error_rate_by_question_png_path, dpi=150, bbox_inches="tight")
        plt.close(fig)

        # Plot 2: answer mix for expected D errors
        if not neutral_answer_mix_df.empty:
            fig, ax = plt.subplots(figsize=(8, 4))
            ax.bar(
                neutral_answer_mix_df["agent_answer"].astype(str),
                neutral_answer_mix_df["count"].astype(float),
            )
            ax.set_xlabel("Agent Answer")
            ax.set_ylabel("Count")
            ax.set_title("Expected D (Neutral) Errors: Agent Answer Mix")
            ax.grid(True, axis="y", alpha=0.3)
            plt.tight_layout()
            neutral_error_answer_mix_png_path = (
                base_output_dir
                / f"survey_simulation_exact_match_expected_D_error_answer_mix_{timestamp}.png"
            )
            fig.savefig(neutral_error_answer_mix_png_path, dpi=150, bbox_inches="tight")
            plt.close(fig)

        # Plot 3: top stance-flow errors
        if not error_flow_df.empty:
            top_flow = error_flow_df.head(8).copy()
            top_flow["flow"] = top_flow["expected_stance"] + "->" + top_flow["agent_stance"]
            fig, ax = plt.subplots(figsize=(10, 5))
            ax.bar(top_flow["flow"], top_flow["count"].astype(float))
            ax.set_xlabel("Error Flow")
            ax.set_ylabel("Count")
            ax.set_title("Top Exact-Match Error Flows (Expected->Predicted Stance)")
            ax.grid(True, axis="y", alpha=0.3)
            plt.xticks(rotation=25, ha="right")
            plt.tight_layout()
            stance_error_flow_png_path = base_output_dir / f"survey_simulation_exact_match_error_flow_by_stance_{timestamp}.png"
            fig.savefig(stance_error_flow_png_path, dpi=150, bbox_inches="tight")
            plt.close(fig)

        # Plot 4: neutral component contributions
        fig, ax = plt.subplots(figsize=(8, 4))
        plot_components = neutral_error_components_df[
            neutral_error_components_df["component"] != "all_neutral_involved_errors"
        ].copy()
        ax.bar(plot_components["component"], plot_components["count"].astype(float))
        ax.set_xlabel("Component")
        ax.set_ylabel("Count")
        ax.set_title("Neutral-Related Error Components")
        ax.grid(True, axis="y", alpha=0.3)
        plt.xticks(rotation=20, ha="right")
        plt.tight_layout()
        neutral_component_png_path = base_output_dir / f"survey_simulation_exact_match_neutral_components_{timestamp}.png"
        fig.savefig(neutral_component_png_path, dpi=150, bbox_inches="tight")
        plt.close(fig)

        # Plot 5: neutral fragility ratio by question
        plot_fragility = neutral_fragility_by_question_df.copy()
        plot_fragility = plot_fragility[plot_fragility["neutral_fragility_ratio"].notna()]
        if not plot_fragility.empty:
            fig, ax = plt.subplots(figsize=(10, 5))
            ax.bar(
                plot_fragility["question_id"].astype(str),
                plot_fragility["neutral_fragility_ratio"].astype(float),
            )
            ax.axhline(1.0, color="gray", linestyle="--", linewidth=1)
            ax.set_xlabel("Question")
            ax.set_ylabel("Neutral Fragility Ratio")
            ax.set_title("Per-Question Neutral Fragility Ratio (D->non-D / non-D baseline)")
            ax.grid(True, axis="y", alpha=0.3)
            plt.tight_layout()
            neutral_fragility_ratio_png_path = base_output_dir / f"survey_simulation_exact_match_neutral_fragility_ratio_by_question_{timestamp}.png"
            fig.savefig(neutral_fragility_ratio_png_path, dpi=150, bbox_inches="tight")
            plt.close(fig)

        print(f"Saved error-by-question CSV: {by_question_csv_path}")
        print(f"Saved error-by-expected-stance CSV: {by_stance_csv_path}")
        print(f"Saved expected-D answer-mix CSV: {neutral_mix_csv_path}")
        print(f"Saved expected-D by-question CSV: {neutral_by_question_csv_path}")
        print(f"Saved stance-flow error CSV: {error_flow_csv_path}")
        print(f"Saved stance confusion CSV: {stance_confusion_all_csv_path}")
        print(f"Saved neutral-components CSV: {neutral_components_csv_path}")
        print(f"Saved C/E proximity CSV: {c_e_proximity_csv_path}")
        print(f"Saved letter-flow error CSV: {letter_error_flow_csv_path}")
        print(f"Saved neutral-fragility-by-question CSV: {neutral_fragility_by_question_csv_path}")
        print(f"Saved error-rate-by-question PNG: {error_rate_by_question_png_path}")
        if neutral_error_answer_mix_png_path is not None:
            print(f"Saved expected-D answer-mix PNG: {neutral_error_answer_mix_png_path}")
        if stance_error_flow_png_path is not None:
            print(f"Saved stance-flow PNG: {stance_error_flow_png_path}")
        if neutral_component_png_path is not None:
            print(f"Saved neutral-components PNG: {neutral_component_png_path}")
        if neutral_fragility_ratio_png_path is not None:
            print(f"Saved neutral-fragility-ratio PNG: {neutral_fragility_ratio_png_path}")

    summary = {
        "results_csv": str(results_csv_path),
        "total_rows": total_rows,
        "total_errors": total_errors,
        "overall_error_rate": overall_error_rate,
        "expected_D_rows": neutral_total,
        "expected_D_errors": neutral_error_count,
        "expected_D_error_rate": neutral_error_rate,
        "expected_nonneutral_pred_neutral_count": expected_nonneutral_pred_neutral_count,
        "expected_neutral_pred_nonneutral_count": expected_neutral_pred_nonneutral_count,
        "neutral_involved_errors": neutral_involved_errors,
        "neutral_involved_error_share": neutral_involved_error_share,
        "expected_D_to_C_or_E_errors": d_to_c_or_e_count,
        "expected_C_or_E_to_D_errors": c_or_e_to_d_count,
        "score_logic_mismatch_rows": logic_mismatch_count,
    }

    return {
        "summary": summary,
        "df": df,
        "errors_df": errors_df,
        "by_question_df": by_question_df,
        "by_expected_stance_df": by_expected_stance_df,
        "error_flow_df": error_flow_df,
        "stance_confusion_all_df": stance_confusion_all_df,
        "neutral_answer_mix_df": neutral_answer_mix_df,
        "neutral_error_by_question_df": neutral_error_by_question_df,
        "neutral_error_components_df": neutral_error_components_df,
        "c_e_neutral_proximity_df": c_e_neutral_proximity_df,
        "letter_error_flow_df": letter_error_flow_df,
        "neutral_fragility_by_question_df": neutral_fragility_by_question_df,
        "by_question_csv_path": by_question_csv_path,
        "by_stance_csv_path": by_stance_csv_path,
        "neutral_mix_csv_path": neutral_mix_csv_path,
        "neutral_by_question_csv_path": neutral_by_question_csv_path,
        "error_flow_csv_path": error_flow_csv_path,
        "stance_confusion_all_csv_path": stance_confusion_all_csv_path,
        "neutral_components_csv_path": neutral_components_csv_path,
        "c_e_proximity_csv_path": c_e_proximity_csv_path,
        "letter_error_flow_csv_path": letter_error_flow_csv_path,
        "neutral_fragility_by_question_csv_path": neutral_fragility_by_question_csv_path,
        "error_rate_by_question_png_path": error_rate_by_question_png_path,
        "neutral_error_answer_mix_png_path": neutral_error_answer_mix_png_path,
        "stance_error_flow_png_path": stance_error_flow_png_path,
        "neutral_component_png_path": neutral_component_png_path,
        "neutral_fragility_ratio_png_path": neutral_fragility_ratio_png_path,
    }


def evaluate_non_random_signal_from_saved_results(
    results_csv_path=None,
    output_dir=None,
    n_baseline_sims=5000,
    n_permutations=5000,
    n_bootstrap=2000,
    random_state=42,
    save_outputs=True,
):
    """
    Stage-1 evaluation: test whether ordinal scores are better than random.

    Includes:
    - random baseline simulation (uniform and expected-frequency matched)
    - permutation test (shuffle expected answers within each question)
    - bootstrap confidence interval for observed mean score

    Parameters:
        results_csv_path (str | Path | None):
            Path to survey_simulation_results_*.csv. If None, newest in data/output.
        output_dir (str | Path | None):
            Where to save summary artifacts. Defaults to data/output.
        n_baseline_sims (int): Number of random baseline simulations.
        n_permutations (int): Number of permutation samples.
        n_bootstrap (int): Number of bootstrap samples.
        random_state (int): Seed for reproducibility.
        save_outputs (bool): Whether to save CSV/PNG artifacts.

    Returns:
        dict: Evaluation outputs and summary metrics.
    """
    base_output_dir = DATA_DIR / "output" if output_dir is None else Path(output_dir)
    base_output_dir.mkdir(parents=True, exist_ok=True)

    if results_csv_path is None:
        candidates = sorted(base_output_dir.glob("survey_simulation_results_*.csv"))
        if not candidates:
            raise FileNotFoundError(
                f"No survey_simulation_results_*.csv found in: {base_output_dir}"
            )
        results_csv_path = candidates[-1]
    else:
        results_csv_path = Path(results_csv_path)

    if not results_csv_path.exists():
        raise FileNotFoundError(f"Results CSV not found: {results_csv_path}")

    results_df = pd.read_csv(results_csv_path)
    required_cols = {"question_id", "agent_answer", "expected_answer"}
    missing_cols = required_cols - set(results_df.columns)
    if missing_cols:
        raise ValueError(f"Results CSV missing required columns: {sorted(missing_cols)}")

    valid_answers = set(["A", "B", "C", "D", "E", "F", "G"])
    eval_df = results_df.copy()
    eval_df["agent_answer"] = eval_df["agent_answer"].astype(str).str.strip().str.upper()
    eval_df["expected_answer"] = eval_df["expected_answer"].astype(str).str.strip().str.upper()
    eval_df = eval_df[
        eval_df["agent_answer"].isin(valid_answers)
        & eval_df["expected_answer"].isin(valid_answers)
    ].copy()

    if eval_df.empty:
        raise ValueError("No valid A-G answer rows found in results CSV.")

    option_keys = ["A", "B", "C", "D", "E", "F", "G"]

    def compute_mean_ordinal_score(agent_series, expected_series):
        scores = [
            calculate_ordinal_score(a, e, option_keys)
            for a, e in zip(agent_series.tolist(), expected_series.tolist())
        ]
        return float(np.mean(scores))

    observed_mean_score = compute_mean_ordinal_score(
        eval_df["agent_answer"],
        eval_df["expected_answer"],
    )

    rng = np.random.default_rng(random_state)

    # Random baseline 1: uniform random A-G
    uniform_baseline_scores = []
    for _ in range(n_baseline_sims):
        random_answers = rng.choice(option_keys, size=len(eval_df), replace=True)
        mean_score = compute_mean_ordinal_score(
            pd.Series(random_answers),
            eval_df["expected_answer"],
        )
        uniform_baseline_scores.append(mean_score)
    uniform_baseline_scores = np.array(uniform_baseline_scores)

    # Random baseline 2: frequency-matched by question (using expected answer frequencies)
    freq_matched_scores = []
    question_groups = {qid: grp for qid, grp in eval_df.groupby("question_id")}
    for _ in range(n_baseline_sims):
        sampled_agents = []
        sampled_expected = []
        for _, group in question_groups.items():
            probs = (
                group["expected_answer"]
                .value_counts(normalize=True)
                .reindex(option_keys, fill_value=0.0)
                .values
            )
            probs_sum = probs.sum()
            if probs_sum == 0:
                probs = np.repeat(1 / len(option_keys), len(option_keys))
            else:
                probs = probs / probs_sum

            draws = rng.choice(option_keys, size=len(group), replace=True, p=probs)
            sampled_agents.extend(draws.tolist())
            sampled_expected.extend(group["expected_answer"].tolist())

        mean_score = compute_mean_ordinal_score(
            pd.Series(sampled_agents),
            pd.Series(sampled_expected),
        )
        freq_matched_scores.append(mean_score)
    freq_matched_scores = np.array(freq_matched_scores)

    # Permutation test: shuffle expected labels within each question
    permutation_scores = []
    for _ in range(n_permutations):
        shuffled_expected_parts = []
        for _, group in question_groups.items():
            values = group["expected_answer"].to_numpy(copy=True)
            rng.shuffle(values)
            shuffled_expected_parts.append(pd.Series(values, index=group.index))

        shuffled_expected = pd.concat(shuffled_expected_parts).sort_index()
        mean_score = compute_mean_ordinal_score(eval_df["agent_answer"], shuffled_expected)
        permutation_scores.append(mean_score)
    permutation_scores = np.array(permutation_scores)

    # Bootstrap CI for observed score
    bootstrap_scores = []
    index_values = np.arange(len(eval_df))
    for _ in range(n_bootstrap):
        sampled_idx = rng.choice(index_values, size=len(index_values), replace=True)
        sampled = eval_df.iloc[sampled_idx]
        score = compute_mean_ordinal_score(sampled["agent_answer"], sampled["expected_answer"])
        bootstrap_scores.append(score)
    bootstrap_scores = np.array(bootstrap_scores)

    observed_ci_low = float(np.percentile(bootstrap_scores, 2.5))
    observed_ci_high = float(np.percentile(bootstrap_scores, 97.5))

    # One-sided p-values for "observed > null"
    p_perm = float((np.sum(permutation_scores >= observed_mean_score) + 1) / (len(permutation_scores) + 1))
    p_uniform = float((np.sum(uniform_baseline_scores >= observed_mean_score) + 1) / (len(uniform_baseline_scores) + 1))
    p_freq = float((np.sum(freq_matched_scores >= observed_mean_score) + 1) / (len(freq_matched_scores) + 1))

    summary = {
        "results_csv": str(results_csv_path),
        "n_rows_evaluated": int(len(eval_df)),
        "n_questions": int(eval_df["question_id"].nunique()),
        "observed_mean_ordinal_score": float(observed_mean_score),
        "observed_bootstrap_ci_95_low": observed_ci_low,
        "observed_bootstrap_ci_95_high": observed_ci_high,
        "uniform_baseline_mean": float(np.mean(uniform_baseline_scores)),
        "uniform_baseline_ci_95_low": float(np.percentile(uniform_baseline_scores, 2.5)),
        "uniform_baseline_ci_95_high": float(np.percentile(uniform_baseline_scores, 97.5)),
        "freq_matched_baseline_mean": float(np.mean(freq_matched_scores)),
        "freq_matched_baseline_ci_95_low": float(np.percentile(freq_matched_scores, 2.5)),
        "freq_matched_baseline_ci_95_high": float(np.percentile(freq_matched_scores, 97.5)),
        "permutation_null_mean": float(np.mean(permutation_scores)),
        "permutation_null_ci_95_low": float(np.percentile(permutation_scores, 2.5)),
        "permutation_null_ci_95_high": float(np.percentile(permutation_scores, 97.5)),
        "p_value_permutation_one_sided": p_perm,
        "p_value_uniform_baseline_one_sided": p_uniform,
        "p_value_freq_baseline_one_sided": p_freq,
        "effect_vs_uniform_baseline": float(observed_mean_score - np.mean(uniform_baseline_scores)),
        "effect_vs_freq_baseline": float(observed_mean_score - np.mean(freq_matched_scores)),
    }

    print("\nNon-randomness evaluation summary:")
    for key, value in summary.items():
        if isinstance(value, float):
            print(f"- {key}: {value:.6f}")
        else:
            print(f"- {key}: {value}")

    outputs = {
        "summary": summary,
        "eval_df": eval_df,
        "uniform_baseline_scores": uniform_baseline_scores,
        "freq_matched_baseline_scores": freq_matched_scores,
        "permutation_scores": permutation_scores,
        "bootstrap_scores": bootstrap_scores,
        "summary_csv_path": None,
        "null_dist_png_path": None,
    }

    if save_outputs:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        summary_csv_path = base_output_dir / f"survey_simulation_nonrandom_summary_{timestamp}.csv"
        pd.DataFrame([summary]).to_csv(summary_csv_path, index=False)

        null_dist_png_path = base_output_dir / f"survey_simulation_nonrandom_null_dist_{timestamp}.png"
        fig, ax = plt.subplots(figsize=(10, 5))
        ax.hist(permutation_scores, bins=40, alpha=0.7, label="Permutation null")
        ax.axvline(observed_mean_score, color="red", linestyle="--", linewidth=2, label="Observed mean")
        ax.set_xlabel("Mean ordinal score")
        ax.set_ylabel("Frequency")
        ax.set_title("Permutation Null Distribution vs Observed Score")
        ax.legend()
        ax.grid(True, axis="y", alpha=0.3)
        plt.tight_layout()
        fig.savefig(null_dist_png_path, dpi=150, bbox_inches="tight")
        plt.close(fig)

        print(f"Saved evaluation summary CSV: {summary_csv_path}")
        print(f"Saved null distribution PNG: {null_dist_png_path}")

        outputs["summary_csv_path"] = summary_csv_path
        outputs["null_dist_png_path"] = null_dist_png_path

    return outputs


def analyze_expected_vs_predicted_stance_by_question(
    results_csv_path=None,
    output_dir=None,
    save_outputs=True,
):
    """
    Compare expected (survey) vs predicted (LLM) stance distribution per question.

    Expected stance is derived from `expected_answer` and predicted stance from
    `agent_answer`, collapsed as:
    - A/B/C -> Oppose
    - D     -> Neutral
    - E/F/G -> Support

    Parameters:
        results_csv_path (str | Path | None):
            Path to a saved survey_simulation_exact_match_results_*.csv.
            If None, latest file from output_dir is used.
        output_dir (str | Path | None):
            Base output directory. Defaults to data/output/experiments/20260306.
        save_outputs (bool):
            Whether to save CSV/PNG diagnostics.

    Returns:
        dict: Summary and DataFrames for expected vs predicted stance mix.
    """
    base_output_dir = (
        DATA_DIR / "output" / "experiments" / "20260306"
        if output_dir is None
        else Path(output_dir)
    )
    base_output_dir.mkdir(parents=True, exist_ok=True)

    if results_csv_path is None:
        candidates = sorted(base_output_dir.glob("survey_simulation_exact_match_results_*.csv"))
        if not candidates:
            raise FileNotFoundError(
                f"No survey_simulation_exact_match_results_*.csv found in: {base_output_dir}"
            )
        results_csv_path = candidates[-1]
    else:
        results_csv_path = Path(results_csv_path)

    if not results_csv_path.exists():
        raise FileNotFoundError(f"Results CSV not found: {results_csv_path}")

    df = pd.read_csv(results_csv_path)
    required_cols = {"question_id", "agent_answer", "expected_answer"}
    missing_cols = required_cols - set(df.columns)
    if missing_cols:
        raise ValueError(f"Results CSV missing required columns: {sorted(missing_cols)}")

    valid_answers = {"A", "B", "C", "D", "E", "F", "G"}
    df["agent_answer"] = df["agent_answer"].astype(str).str.strip().str.upper()
    df["expected_answer"] = df["expected_answer"].astype(str).str.strip().str.upper()
    df = df[
        df["agent_answer"].isin(valid_answers)
        & df["expected_answer"].isin(valid_answers)
    ].copy()

    if df.empty:
        raise ValueError("No valid A-G answer rows found in results CSV.")

    stance_map = {
        "A": "Oppose",
        "B": "Oppose",
        "C": "Oppose",
        "D": "Neutral",
        "E": "Support",
        "F": "Support",
        "G": "Support",
    }
    stance_order = ["Oppose", "Neutral", "Support"]

    df["expected_stance"] = df["expected_answer"].map(stance_map)
    df["predicted_stance"] = df["agent_answer"].map(stance_map)

    expected_counts = (
        df.groupby(["question_id", "expected_stance"])
        .size()
        .rename("expected_count")
        .reset_index()
        .rename(columns={"expected_stance": "stance"})
    )

    predicted_counts = (
        df.groupby(["question_id", "predicted_stance"])
        .size()
        .rename("predicted_count")
        .reset_index()
        .rename(columns={"predicted_stance": "stance"})
    )

    comparison_df = expected_counts.merge(
        predicted_counts,
        on=["question_id", "stance"],
        how="outer",
    ).fillna(0)

    comparison_df["expected_count"] = comparison_df["expected_count"].astype(int)
    comparison_df["predicted_count"] = comparison_df["predicted_count"].astype(int)

    question_totals = (
        df.groupby("question_id").size().rename("n_rows").reset_index()
    )
    comparison_df = comparison_df.merge(question_totals, on="question_id", how="left")
    comparison_df["expected_share"] = comparison_df["expected_count"] / comparison_df["n_rows"]
    comparison_df["predicted_share"] = comparison_df["predicted_count"] / comparison_df["n_rows"]
    comparison_df["share_delta_pred_minus_expected"] = (
        comparison_df["predicted_share"] - comparison_df["expected_share"]
    )

    question_order = list(dict.fromkeys(df["question_id"].astype(str).tolist()))
    comparison_df["question_id"] = comparison_df["question_id"].astype(str)
    comparison_df["stance"] = pd.Categorical(
        comparison_df["stance"],
        categories=stance_order,
        ordered=True,
    )
    comparison_df = comparison_df.sort_values(["question_id", "stance"]).reset_index(drop=True)

    pivot_expected_share_df = (
        comparison_df.pivot_table(
            index="question_id",
            columns="stance",
            values="expected_share",
            aggfunc="first",
            fill_value=0.0,
        )
        .reindex(index=question_order, fill_value=0.0)
        .reset_index()
    )

    pivot_predicted_share_df = (
        comparison_df.pivot_table(
            index="question_id",
            columns="stance",
            values="predicted_share",
            aggfunc="first",
            fill_value=0.0,
        )
        .reindex(index=question_order, fill_value=0.0)
        .reset_index()
    )

    pivot_delta_share_df = (
        comparison_df.pivot_table(
            index="question_id",
            columns="stance",
            values="share_delta_pred_minus_expected",
            aggfunc="first",
            fill_value=0.0,
        )
        .reindex(index=question_order, fill_value=0.0)
        .reset_index()
    )

    print("\nExpected vs Predicted stance mix by question")
    print(f"- Loaded: {results_csv_path}")
    print(f"- Rows used: {len(df)}")
    print("\nTop absolute share gaps (predicted - expected):")
    abs_gap = comparison_df.copy()
    abs_gap["abs_share_gap"] = abs_gap["share_delta_pred_minus_expected"].abs()
    print(
        abs_gap.sort_values("abs_share_gap", ascending=False)[
            ["question_id", "stance", "expected_share", "predicted_share", "share_delta_pred_minus_expected"]
        ]
        .head(12)
        .to_string(index=False)
    )

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    comparison_csv_path = None
    expected_share_csv_path = None
    predicted_share_csv_path = None
    delta_share_csv_path = None
    stance_share_plot_path = None
    stance_delta_plot_path = None

    if save_outputs:
        comparison_csv_path = base_output_dir / f"survey_simulation_expected_vs_predicted_stance_comparison_{timestamp}.csv"
        expected_share_csv_path = base_output_dir / f"survey_simulation_expected_stance_share_by_question_{timestamp}.csv"
        predicted_share_csv_path = base_output_dir / f"survey_simulation_predicted_stance_share_by_question_{timestamp}.csv"
        delta_share_csv_path = base_output_dir / f"survey_simulation_stance_share_delta_by_question_{timestamp}.csv"

        comparison_df.to_csv(comparison_csv_path, index=False)
        pivot_expected_share_df.to_csv(expected_share_csv_path, index=False)
        pivot_predicted_share_df.to_csv(predicted_share_csv_path, index=False)
        pivot_delta_share_df.to_csv(delta_share_csv_path, index=False)

        # Plot 1: expected vs predicted Neutral share by question (quick neutral-focused view)
        neutral_cmp = comparison_df[comparison_df["stance"] == "Neutral"].copy()
        neutral_cmp = neutral_cmp.set_index("question_id").reindex(question_order).reset_index()

        x = np.arange(len(neutral_cmp))
        width = 0.35
        fig, ax = plt.subplots(figsize=(11, 5))
        ax.bar(x - width / 2, neutral_cmp["expected_share"], width=width, label="Expected Neutral share")
        ax.bar(x + width / 2, neutral_cmp["predicted_share"], width=width, label="Predicted Neutral share")
        ax.set_xticks(x)
        ax.set_xticklabels(neutral_cmp["question_id"].astype(str).tolist())
        ax.set_ylim(0.0, 1.0)
        ax.set_xlabel("Question")
        ax.set_ylabel("Share")
        ax.set_title("Expected vs Predicted Neutral Share by Question")
        ax.legend()
        ax.grid(True, axis="y", alpha=0.3)
        plt.tight_layout()
        stance_share_plot_path = base_output_dir / f"survey_simulation_expected_vs_predicted_neutral_share_{timestamp}.png"
        fig.savefig(stance_share_plot_path, dpi=150, bbox_inches="tight")
        plt.close(fig)

        # Plot 2: share deltas by stance and question
        fig, ax = plt.subplots(figsize=(11, 6))
        delta_plot = comparison_df.copy()
        delta_plot["stance"] = delta_plot["stance"].astype(str)
        for stance_name, color, offset in [
            ("Oppose", "tab:red", -0.22),
            ("Neutral", "tab:gray", 0.0),
            ("Support", "tab:green", 0.22),
        ]:
            subset = delta_plot[delta_plot["stance"] == stance_name].set_index("question_id")
            subset = subset.reindex(question_order).reset_index()
            ax.bar(
                np.arange(len(question_order)) + offset,
                subset["share_delta_pred_minus_expected"].astype(float),
                width=0.22,
                label=stance_name,
                color=color,
                alpha=0.85,
            )
        ax.axhline(0.0, color="black", linestyle="--", linewidth=1)
        ax.set_xticks(np.arange(len(question_order)))
        ax.set_xticklabels(question_order)
        ax.set_xlabel("Question")
        ax.set_ylabel("Predicted Share - Expected Share")
        ax.set_title("Stance Share Delta by Question")
        ax.legend()
        ax.grid(True, axis="y", alpha=0.3)
        plt.tight_layout()
        stance_delta_plot_path = base_output_dir / f"survey_simulation_stance_share_delta_by_question_{timestamp}.png"
        fig.savefig(stance_delta_plot_path, dpi=150, bbox_inches="tight")
        plt.close(fig)

        print(f"Saved comparison CSV: {comparison_csv_path}")
        print(f"Saved expected-share CSV: {expected_share_csv_path}")
        print(f"Saved predicted-share CSV: {predicted_share_csv_path}")
        print(f"Saved delta-share CSV: {delta_share_csv_path}")
        print(f"Saved neutral-share comparison PNG: {stance_share_plot_path}")
        print(f"Saved stance-delta PNG: {stance_delta_plot_path}")

    summary = {
        "results_csv": str(results_csv_path),
        "n_rows": int(len(df)),
        "n_questions": int(df["question_id"].nunique()),
    }

    return {
        "summary": summary,
        "comparison_df": comparison_df,
        "expected_share_df": pivot_expected_share_df,
        "predicted_share_df": pivot_predicted_share_df,
        "delta_share_df": pivot_delta_share_df,
        "comparison_csv_path": comparison_csv_path,
        "expected_share_csv_path": expected_share_csv_path,
        "predicted_share_csv_path": predicted_share_csv_path,
        "delta_share_csv_path": delta_share_csv_path,
        "stance_share_plot_path": stance_share_plot_path,
        "stance_delta_plot_path": stance_delta_plot_path,
    }


def report_survey_stance_percentages_by_question(
    survey_csv_path=None,
    output_dir=None,
    save_outputs=True,
):
    """
    Load survey data and report stance percentages per question.

    Uses survey's coded answer scale and maps:
    - 1,2,3 -> Oppose
    - 4     -> Neutral
    - 5,6,7 -> Support

    Parameters:
        survey_csv_path (str | Path | None):
            Path to survey CSV. If None, defaults to
            data/yougov_survey_data/YouGovProcessedData_train.csv
        output_dir (str | Path | None):
            Directory for output CSV. Defaults to
            data/output/experiments/20260306
        save_outputs (bool):
            Whether to save the summary CSV.

    Returns:
        dict: Summary DataFrame and optional CSV path.
    """
    if survey_csv_path is None:
        survey_csv_path = DATA_DIR / "yougov_survey_data" / "YouGovProcessedData_train.csv"
    else:
        survey_csv_path = Path(survey_csv_path)

    survey_data = load_survey_data(survey_csv_path)
    if survey_data is None or survey_data.empty:
        raise ValueError("No survey data available for stance-percentage report.")

    try:
        from survey_dict import SURVEY_QUESTIONS
    except ImportError:
        from sandbox.ajay_sandbox.survey_dict import SURVEY_QUESTIONS

    def code_to_stance(value):
        try:
            ivalue = int(value)
        except Exception:
            return None
        if ivalue in [1, 2, 3]:
            return "Oppose"
        if ivalue == 4:
            return "Neutral"
        if ivalue in [5, 6, 7]:
            return "Support"
        return None

    rows = []
    for q in SURVEY_QUESTIONS:
        question_id = q.get("id", q.get("col_name", "unknown_question"))
        question_text = q.get("text", "")
        col_name = q.get("col_name", "")

        if col_name not in survey_data.columns:
            rows.append(
                {
                    "question_id": question_id,
                    "question_column": col_name,
                    "question_text": question_text,
                    "n_total": 0,
                    "n_valid": 0,
                    "n_oppose": 0,
                    "n_neutral": 0,
                    "n_support": 0,
                    "pct_oppose": np.nan,
                    "pct_neutral": np.nan,
                    "pct_support": np.nan,
                }
            )
            continue

        stances = survey_data[col_name].apply(code_to_stance)
        valid = stances[stances.notna()]
        n_total = int(len(survey_data))
        n_valid = int(len(valid))
        n_oppose = int((valid == "Oppose").sum())
        n_neutral = int((valid == "Neutral").sum())
        n_support = int((valid == "Support").sum())

        pct_oppose = float(n_oppose / n_valid) if n_valid else np.nan
        pct_neutral = float(n_neutral / n_valid) if n_valid else np.nan
        pct_support = float(n_support / n_valid) if n_valid else np.nan

        rows.append(
            {
                "question_id": question_id,
                "question_column": col_name,
                "question_text": question_text,
                "n_total": n_total,
                "n_valid": n_valid,
                "n_oppose": n_oppose,
                "n_neutral": n_neutral,
                "n_support": n_support,
                "pct_oppose": pct_oppose,
                "pct_neutral": pct_neutral,
                "pct_support": pct_support,
            }
        )

    stance_pct_df = pd.DataFrame(rows)

    print("\nSurvey stance percentages by question")
    print(f"- Source survey CSV: {survey_csv_path}")
    print(
        stance_pct_df[
            ["question_id", "pct_oppose", "pct_neutral", "pct_support", "n_valid"]
        ].to_string(index=False)
    )

    output_csv_path = None
    if save_outputs:
        base_output_dir = (
            DATA_DIR / "output" / "experiments" / "20260306"
            if output_dir is None
            else Path(output_dir)
        )
        base_output_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_csv_path = base_output_dir / f"survey_data_stance_percentages_by_question_{timestamp}.csv"
        stance_pct_df.to_csv(output_csv_path, index=False)
        print(f"Saved survey stance-percentage CSV: {output_csv_path}")

    return {
        "stance_pct_df": stance_pct_df,
        "output_csv_path": output_csv_path,
        "survey_csv_path": str(survey_csv_path),
    }


def analyze_per_agent_support_index_from_saved_results(
    results_csv_path=None,
    output_dir=None,
    save_outputs=True,
):
    """
    Build per-agent support index from saved simulation results.

    Support index mapping:
    - A=-3, B=-2, C=-1, D=0, E=1, F=2, G=3

    For each respondent, this computes:
    - mean predicted support index across questions
    - mean expected support index across questions

    Also reports agreement metrics and saves a comparison plot.
    """
    if results_csv_path is None:
        results_csv_path = DATA_DIR / "output" / "experiments" / "20260301" / "survey_simulation_results_20260301_210726.csv"
    else:
        results_csv_path = Path(results_csv_path)

    if not results_csv_path.exists():
        raise FileNotFoundError(f"Results CSV not found: {results_csv_path}")

    df = pd.read_csv(results_csv_path)
    required_cols = {"respondent_id", "question_id", "agent_answer", "expected_answer"}
    missing_cols = required_cols - set(df.columns)
    if missing_cols:
        raise ValueError(f"Results CSV missing required columns: {sorted(missing_cols)}")

    df["agent_answer"] = df["agent_answer"].astype(str).str.strip().str.upper()
    df["expected_answer"] = df["expected_answer"].astype(str).str.strip().str.upper()

    df["predicted_support_score"] = df["agent_answer"].apply(answer_to_score)
    df["expected_support_score"] = df["expected_answer"].apply(answer_to_score)

    valid_df = df[
        df["predicted_support_score"].notna() & df["expected_support_score"].notna()
    ].copy()
    if valid_df.empty:
        raise ValueError("No valid scored rows found in results CSV.")

    per_agent_df = (
        valid_df.groupby("respondent_id", as_index=False)
        .agg(
            n_questions=("question_id", "nunique"),
            predicted_support_index=("predicted_support_score", "mean"),
            expected_support_index=("expected_support_score", "mean"),
        )
    )
    per_agent_df["index_delta_pred_minus_expected"] = (
        per_agent_df["predicted_support_index"] - per_agent_df["expected_support_index"]
    )

    deltas = per_agent_df["index_delta_pred_minus_expected"].astype(float)
    mae = float(np.mean(np.abs(deltas)))
    rmse = float(np.sqrt(np.mean(np.square(deltas))))
    bias = float(np.mean(deltas))

    if len(per_agent_df) >= 2:
        corr = float(
            np.corrcoef(
                per_agent_df["predicted_support_index"].astype(float),
                per_agent_df["expected_support_index"].astype(float),
            )[0, 1]
        )
    else:
        corr = np.nan

    within_05 = float(np.mean(np.abs(deltas) <= 0.5))
    within_10 = float(np.mean(np.abs(deltas) <= 1.0))

    print("\nPer-agent support index analysis")
    print(f"- Source results CSV: {results_csv_path}")
    print(f"- Respondents analyzed: {len(per_agent_df)}")
    print(f"- Mean absolute error (index): {mae:.4f}")
    print(f"- RMSE (index): {rmse:.4f}")
    print(f"- Mean bias (pred - exp): {bias:.4f}")
    if pd.notna(corr):
        print(f"- Correlation(pred, exp): {corr:.4f}")
    print(f"- Within ±0.5 index points: {within_05:.4f}")
    print(f"- Within ±1.0 index points: {within_10:.4f}")

    base_output_dir = (
        DATA_DIR / "output" / "experiments" / "20260301"
        if output_dir is None
        else Path(output_dir)
    )
    base_output_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    per_agent_csv_path = None
    summary_csv_path = None
    plot_path = None

    if save_outputs:
        per_agent_csv_path = base_output_dir / f"survey_simulation_per_agent_support_index_{timestamp}.csv"
        summary_csv_path = base_output_dir / f"survey_simulation_per_agent_support_index_summary_{timestamp}.csv"
        plot_path = base_output_dir / f"survey_simulation_per_agent_support_index_plot_{timestamp}.png"

        per_agent_df.to_csv(per_agent_csv_path, index=False)
        pd.DataFrame([
            {
                "results_csv": str(results_csv_path),
                "n_respondents": int(len(per_agent_df)),
                "mae_index": mae,
                "rmse_index": rmse,
                "mean_bias_pred_minus_exp": bias,
                "correlation_pred_exp": corr,
                "within_0p5": within_05,
                "within_1p0": within_10,
            }
        ]).to_csv(summary_csv_path, index=False)

        fig, axes = plt.subplots(1, 2, figsize=(12, 5))

        # Plot 1: scatter predicted vs expected index per respondent
        axes[0].scatter(
            per_agent_df["expected_support_index"],
            per_agent_df["predicted_support_index"],
            alpha=0.6,
            s=20,
        )
        axes[0].plot([-3, 3], [-3, 3], linestyle="--", linewidth=1)
        axes[0].set_xlim([-3, 3])
        axes[0].set_ylim([-3, 3])
        axes[0].set_xlabel("Expected per-agent support index")
        axes[0].set_ylabel("Predicted per-agent support index")
        axes[0].set_title("Predicted vs Expected Support Index")
        axes[0].grid(True, alpha=0.3)

        # Plot 2: distribution of index delta
        axes[1].hist(per_agent_df["index_delta_pred_minus_expected"], bins=20, alpha=0.8)
        axes[1].axvline(0.0, linestyle="--", linewidth=1)
        axes[1].set_xlabel("Predicted - Expected support index")
        axes[1].set_ylabel("Respondent count")
        axes[1].set_title("Per-agent Index Error Distribution")
        axes[1].grid(True, axis="y", alpha=0.3)

        plt.tight_layout()
        fig.savefig(plot_path, dpi=150, bbox_inches="tight")
        plt.close(fig)

        print(f"Saved per-agent support index CSV: {per_agent_csv_path}")
        print(f"Saved support index summary CSV: {summary_csv_path}")
        print(f"Saved support index plot PNG: {plot_path}")

    return {
        "per_agent_df": per_agent_df,
        "metrics": {
            "mae_index": mae,
            "rmse_index": rmse,
            "mean_bias_pred_minus_exp": bias,
            "correlation_pred_exp": corr,
            "within_0p5": within_05,
            "within_1p0": within_10,
            "n_respondents": int(len(per_agent_df)),
        },
        "per_agent_csv_path": per_agent_csv_path,
        "summary_csv_path": summary_csv_path,
        "plot_path": plot_path,
    }


def analyze_results_by_question_framing(
    results_csv_path=None,
    question_type_map=None,
    output_dir=None,
    save_outputs=True,
):
    """
    Analyze saved simulation results stratified by question framing type.

    Default framing rubric (editable):
    - consensus_positive: Q1, Q4
    - tradeoff_polarized: Q2, Q3, Q5, Q6

    Produces:
    - per-question metrics with framing label
    - per-framing aggregate metrics
    - two-panel plot:
      1) per-question support-score bias (predicted - expected)
      2) aggregate by framing type
    """
    if results_csv_path is None:
        results_csv_path = DATA_DIR / "output" / "experiments" / "20260301" / "survey_simulation_results_20260301_210726.csv"
    else:
        results_csv_path = Path(results_csv_path)

    if not results_csv_path.exists():
        raise FileNotFoundError(f"Results CSV not found: {results_csv_path}")

    if question_type_map is None:
        question_type_map = {
            "Q1": "consensus_positive",
            "Q4": "consensus_positive",
            "Q2": "tradeoff_polarized",
            "Q3": "tradeoff_polarized",
            "Q5": "tradeoff_polarized",
            "Q6": "tradeoff_polarized",
        }

    df = pd.read_csv(results_csv_path)
    required_cols = {
        "question_id", "respondent_id", "agent_answer", "expected_answer", "ordinal_accuracy_score"
    }
    missing_cols = required_cols - set(df.columns)
    if missing_cols:
        raise ValueError(f"Results CSV missing required columns: {sorted(missing_cols)}")

    df["agent_answer"] = df["agent_answer"].astype(str).str.strip().str.upper()
    df["expected_answer"] = df["expected_answer"].astype(str).str.strip().str.upper()
    df["pred_score"] = df["agent_answer"].apply(answer_to_score)
    df["exp_score"] = df["expected_answer"].apply(answer_to_score)
    df = df[df["pred_score"].notna() & df["exp_score"].notna()].copy()
    if df.empty:
        raise ValueError("No valid scored rows found in results CSV.")

    df["question_type"] = df["question_id"].map(question_type_map).fillna("unlabeled")
    df["score_bias_pred_minus_exp"] = df["pred_score"] - df["exp_score"]

    per_question_df = (
        df.groupby(["question_id", "question_type"], as_index=False)
        .agg(
            n_rows=("respondent_id", "size"),
            n_respondents=("respondent_id", "nunique"),
            mean_pred_support_score=("pred_score", "mean"),
            mean_exp_support_score=("exp_score", "mean"),
            mean_score_bias=("score_bias_pred_minus_exp", "mean"),
            mean_abs_error=("score_bias_pred_minus_exp", lambda x: float(np.mean(np.abs(x)))),
            mean_ordinal_accuracy=("ordinal_accuracy_score", "mean"),
        )
        .sort_values("question_id")
        .reset_index(drop=True)
    )

    per_type_df = (
        df.groupby("question_type", as_index=False)
        .agg(
            n_rows=("respondent_id", "size"),
            n_respondents=("respondent_id", "nunique"),
            mean_pred_support_score=("pred_score", "mean"),
            mean_exp_support_score=("exp_score", "mean"),
            mean_score_bias=("score_bias_pred_minus_exp", "mean"),
            mean_abs_error=("score_bias_pred_minus_exp", lambda x: float(np.mean(np.abs(x)))),
            mean_ordinal_accuracy=("ordinal_accuracy_score", "mean"),
        )
        .sort_values("question_type")
        .reset_index(drop=True)
    )

    print("\nFraming-stratified analysis")
    print(f"- Source results CSV: {results_csv_path}")
    print("\nPer-question:")
    print(
        per_question_df[
            [
                "question_id", "question_type", "mean_pred_support_score",
                "mean_exp_support_score", "mean_score_bias", "mean_ordinal_accuracy"
            ]
        ].to_string(index=False)
    )
    print("\nPer-framing aggregate:")
    print(
        per_type_df[
            [
                "question_type", "mean_pred_support_score", "mean_exp_support_score",
                "mean_score_bias", "mean_abs_error", "mean_ordinal_accuracy"
            ]
        ].to_string(index=False)
    )

    base_output_dir = (
        DATA_DIR / "output" / "experiments" / "20260301"
        if output_dir is None
        else Path(output_dir)
    )
    base_output_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    per_question_csv_path = None
    per_type_csv_path = None
    plot_path = None

    if save_outputs:
        per_question_csv_path = base_output_dir / f"survey_simulation_framing_per_question_{timestamp}.csv"
        per_type_csv_path = base_output_dir / f"survey_simulation_framing_per_type_{timestamp}.csv"
        plot_path = base_output_dir / f"survey_simulation_framing_two_panel_{timestamp}.png"

        per_question_df.to_csv(per_question_csv_path, index=False)
        per_type_df.to_csv(per_type_csv_path, index=False)

        fig, axes = plt.subplots(1, 2, figsize=(13, 5))

        # Panel 1: per-question bias
        q_plot = per_question_df.sort_values("question_id")
        axes[0].bar(
            q_plot["question_id"].astype(str),
            q_plot["mean_score_bias"].astype(float),
        )
        axes[0].axhline(0.0, color="black", linestyle="--", linewidth=1)
        axes[0].set_xlabel("Question")
        axes[0].set_ylabel("Mean Predicted - Expected Support Score")
        axes[0].set_title("Per-Question Support-Score Bias")
        axes[0].grid(True, axis="y", alpha=0.3)

        # Panel 2: by framing type
        t_plot = per_type_df.sort_values("question_type")
        axes[1].bar(
            t_plot["question_type"].astype(str),
            t_plot["mean_score_bias"].astype(float),
        )
        axes[1].axhline(0.0, color="black", linestyle="--", linewidth=1)
        axes[1].set_xlabel("Question Type")
        axes[1].set_ylabel("Mean Predicted - Expected Support Score")
        axes[1].set_title("Average Bias by Framing Type")
        axes[1].grid(True, axis="y", alpha=0.3)
        axes[1].tick_params(axis="x", rotation=20)

        plt.tight_layout()
        fig.savefig(plot_path, dpi=150, bbox_inches="tight")
        plt.close(fig)

        print(f"Saved framing per-question CSV: {per_question_csv_path}")
        print(f"Saved framing per-type CSV: {per_type_csv_path}")
        print(f"Saved framing two-panel PNG: {plot_path}")

    return {
        "per_question_df": per_question_df,
        "per_type_df": per_type_df,
        "per_question_csv_path": per_question_csv_path,
        "per_type_csv_path": per_type_csv_path,
        "plot_path": plot_path,
        "question_type_map": question_type_map,
    }


def calibrate_support_scores_by_question_framing(
    results_csv_path=None,
    question_type_map=None,
    output_dir=None,
    calibration_method="linear",
    save_outputs=True,
):
    """
    Post-hoc calibrate predicted support scores by question framing type.

    Calibration is applied on support-index scores derived from A-G:
    A=-3, B=-2, C=-1, D=0, E=1, F=2, G=3.

    Parameters:
        results_csv_path (str | Path | None):
            Path to survey_simulation_results_*.csv. If None, defaults to
            data/output/experiments/20260301/survey_simulation_results_20260301_210726.csv.
        question_type_map (dict | None):
            Mapping like {"Q1": "consensus_positive", ...}. If None, uses
            default rubric from framing analysis.
        output_dir (str | Path | None):
            Where to write outputs. Defaults to data/output/experiments/20260301.
        calibration_method (str):
            "linear" (y = a*x + b) or "mean_shift" (y = x + b), fitted per framing type.
        save_outputs (bool):
            Whether to save CSV/PNG artifacts.

    Returns:
        dict: calibrated row-level data, fit params, and before/after metrics.
    """
    if results_csv_path is None:
        results_csv_path = DATA_DIR / "output" / "experiments" / "20260301" / "survey_simulation_results_20260301_210726.csv"
    else:
        results_csv_path = Path(results_csv_path)

    if not results_csv_path.exists():
        raise FileNotFoundError(f"Results CSV not found: {results_csv_path}")

    if question_type_map is None:
        question_type_map = {
            "Q1": "consensus_positive",
            "Q4": "consensus_positive",
            "Q2": "tradeoff_polarized",
            "Q3": "tradeoff_polarized",
            "Q5": "tradeoff_polarized",
            "Q6": "tradeoff_polarized",
        }

    calibration_method = str(calibration_method).strip().lower()
    if calibration_method not in {"linear", "mean_shift"}:
        raise ValueError("calibration_method must be one of: ['linear', 'mean_shift']")

    df = pd.read_csv(results_csv_path)
    required_cols = {"question_id", "respondent_id", "agent_answer", "expected_answer"}
    missing_cols = required_cols - set(df.columns)
    if missing_cols:
        raise ValueError(f"Results CSV missing required columns: {sorted(missing_cols)}")

    df["agent_answer"] = df["agent_answer"].astype(str).str.strip().str.upper()
    df["expected_answer"] = df["expected_answer"].astype(str).str.strip().str.upper()
    df["pred_score"] = df["agent_answer"].apply(answer_to_score)
    df["exp_score"] = df["expected_answer"].apply(answer_to_score)
    df = df[df["pred_score"].notna() & df["exp_score"].notna()].copy()
    if df.empty:
        raise ValueError("No valid scored rows found in results CSV.")

    df["question_type"] = df["question_id"].map(question_type_map).fillna("unlabeled")

    fit_rows = []
    calibrated_parts = []
    for question_type, group in df.groupby("question_type"):
        x = group["pred_score"].astype(float).to_numpy()
        y = group["exp_score"].astype(float).to_numpy()

        if calibration_method == "mean_shift":
            slope = 1.0
            intercept = float(np.mean(y) - np.mean(x))
            fit_mode = "mean_shift"
        else:
            unique_x = np.unique(x)
            if len(unique_x) < 2:
                slope = 1.0
                intercept = float(np.mean(y) - np.mean(x))
                fit_mode = "linear_fallback_mean_shift"
            else:
                slope, intercept = np.polyfit(x, y, deg=1)
                slope = float(slope)
                intercept = float(intercept)
                fit_mode = "linear"

        part = group.copy()
        part["calibrated_pred_score_raw"] = slope * part["pred_score"].astype(float) + intercept
        part["calibrated_pred_score"] = part["calibrated_pred_score_raw"].clip(-3, 3)

        fit_rows.append(
            {
                "question_type": question_type,
                "n_rows": int(len(group)),
                "fit_mode": fit_mode,
                "slope": slope,
                "intercept": intercept,
                "mean_pred_before": float(np.mean(x)),
                "mean_exp": float(np.mean(y)),
                "mean_pred_after": float(np.mean(part["calibrated_pred_score"].astype(float))),
            }
        )
        calibrated_parts.append(part)

    calibrated_df = pd.concat(calibrated_parts, ignore_index=True)

    letter_map = {-3: "A", -2: "B", -1: "C", 0: "D", 1: "E", 2: "F", 3: "G"}
    rounded = np.rint(calibrated_df["calibrated_pred_score"].astype(float)).astype(int)
    rounded = np.clip(rounded, -3, 3)
    calibrated_df["calibrated_agent_answer"] = [letter_map[v] for v in rounded]

    calibrated_df["error_before"] = calibrated_df["pred_score"].astype(float) - calibrated_df["exp_score"].astype(float)
    calibrated_df["error_after"] = calibrated_df["calibrated_pred_score"].astype(float) - calibrated_df["exp_score"].astype(float)
    calibrated_df["abs_error_before"] = calibrated_df["error_before"].abs()
    calibrated_df["abs_error_after"] = calibrated_df["error_after"].abs()
    calibrated_df["sq_error_before"] = calibrated_df["error_before"] ** 2
    calibrated_df["sq_error_after"] = calibrated_df["error_after"] ** 2
    calibrated_df["ordinal_accuracy_after"] = calibrated_df.apply(
        lambda row: calculate_ordinal_score(
            row["calibrated_agent_answer"],
            row["expected_answer"],
            ["A", "B", "C", "D", "E", "F", "G"],
        ),
        axis=1,
    )

    fit_params_df = pd.DataFrame(fit_rows).sort_values("question_type").reset_index(drop=True)

    def _summarize(group_df):
        before_corr = (
            float(group_df["pred_score"].corr(group_df["exp_score"]))
            if len(group_df) >= 2
            else np.nan
        )
        after_corr = (
            float(group_df["calibrated_pred_score"].corr(group_df["exp_score"]))
            if len(group_df) >= 2
            else np.nan
        )
        return pd.Series(
            {
                "n_rows": int(len(group_df)),
                "n_respondents": int(group_df["respondent_id"].nunique()),
                "bias_before": float(np.mean(group_df["error_before"])),
                "bias_after": float(np.mean(group_df["error_after"])),
                "mae_before": float(np.mean(group_df["abs_error_before"])),
                "mae_after": float(np.mean(group_df["abs_error_after"])),
                "rmse_before": float(np.sqrt(np.mean(group_df["sq_error_before"]))),
                "rmse_after": float(np.sqrt(np.mean(group_df["sq_error_after"]))),
                "mean_pred_before": float(np.mean(group_df["pred_score"])),
                "mean_pred_after": float(np.mean(group_df["calibrated_pred_score"])),
                "mean_exp": float(np.mean(group_df["exp_score"])),
                "corr_before": before_corr,
                "corr_after": after_corr,
                "mean_ordinal_after": float(np.mean(group_df["ordinal_accuracy_after"])),
            }
        )

    per_type_metrics_df = (
        calibrated_df.groupby("question_type", as_index=False)
        .apply(_summarize, include_groups=False)
        .reset_index(drop=True)
    )
    per_type_metrics_df["abs_bias_before"] = per_type_metrics_df["bias_before"].abs()
    per_type_metrics_df["abs_bias_after"] = per_type_metrics_df["bias_after"].abs()
    per_type_metrics_df["mae_delta_after_minus_before"] = (
        per_type_metrics_df["mae_after"] - per_type_metrics_df["mae_before"]
    )
    per_type_metrics_df["abs_bias_delta_after_minus_before"] = (
        per_type_metrics_df["abs_bias_after"] - per_type_metrics_df["abs_bias_before"]
    )

    overall_before_corr = (
        float(calibrated_df["pred_score"].corr(calibrated_df["exp_score"]))
        if len(calibrated_df) >= 2
        else np.nan
    )
    overall_after_corr = (
        float(calibrated_df["calibrated_pred_score"].corr(calibrated_df["exp_score"]))
        if len(calibrated_df) >= 2
        else np.nan
    )
    overall_metrics_df = pd.DataFrame(
        [
            {
                "scope": "overall",
                "n_rows": int(len(calibrated_df)),
                "n_respondents": int(calibrated_df["respondent_id"].nunique()),
                "bias_before": float(np.mean(calibrated_df["error_before"])),
                "bias_after": float(np.mean(calibrated_df["error_after"])),
                "mae_before": float(np.mean(calibrated_df["abs_error_before"])),
                "mae_after": float(np.mean(calibrated_df["abs_error_after"])),
                "rmse_before": float(np.sqrt(np.mean(calibrated_df["sq_error_before"]))),
                "rmse_after": float(np.sqrt(np.mean(calibrated_df["sq_error_after"]))),
                "mean_pred_before": float(np.mean(calibrated_df["pred_score"])),
                "mean_pred_after": float(np.mean(calibrated_df["calibrated_pred_score"])),
                "mean_exp": float(np.mean(calibrated_df["exp_score"])),
                "corr_before": overall_before_corr,
                "corr_after": overall_after_corr,
                "mean_ordinal_after": float(np.mean(calibrated_df["ordinal_accuracy_after"])),
            }
        ]
    )
    overall_metrics_df["abs_bias_before"] = overall_metrics_df["bias_before"].abs()
    overall_metrics_df["abs_bias_after"] = overall_metrics_df["bias_after"].abs()
    overall_metrics_df["mae_delta_after_minus_before"] = (
        overall_metrics_df["mae_after"] - overall_metrics_df["mae_before"]
    )
    overall_metrics_df["abs_bias_delta_after_minus_before"] = (
        overall_metrics_df["abs_bias_after"] - overall_metrics_df["abs_bias_before"]
    )

    print("\nPost-hoc calibration by framing type")
    print(f"- Source results CSV: {results_csv_path}")
    print(f"- Calibration method: {calibration_method}")
    print("\nFitted parameters:")
    print(fit_params_df.to_string(index=False))
    print("\nPer-framing before/after metrics:")
    print(
        per_type_metrics_df[
            [
                "question_type",
                "bias_before",
                "bias_after",
                "mae_before",
                "mae_after",
                "rmse_before",
                "rmse_after",
            ]
        ].to_string(index=False)
    )
    print("\nOverall before/after metrics:")
    print(overall_metrics_df.to_string(index=False))

    base_output_dir = (
        DATA_DIR / "output" / "experiments" / "20260301"
        if output_dir is None
        else Path(output_dir)
    )
    base_output_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    fit_params_csv_path = None
    per_type_metrics_csv_path = None
    overall_metrics_csv_path = None
    calibrated_rows_csv_path = None
    plot_path = None

    if save_outputs:
        fit_params_csv_path = base_output_dir / f"survey_simulation_framing_calibration_fit_params_{timestamp}.csv"
        per_type_metrics_csv_path = base_output_dir / f"survey_simulation_framing_calibration_metrics_by_type_{timestamp}.csv"
        overall_metrics_csv_path = base_output_dir / f"survey_simulation_framing_calibration_metrics_overall_{timestamp}.csv"
        calibrated_rows_csv_path = base_output_dir / f"survey_simulation_framing_calibrated_rows_{timestamp}.csv"
        plot_path = base_output_dir / f"survey_simulation_framing_calibration_before_after_{timestamp}.png"

        fit_params_df.to_csv(fit_params_csv_path, index=False)
        per_type_metrics_df.to_csv(per_type_metrics_csv_path, index=False)
        overall_metrics_df.to_csv(overall_metrics_csv_path, index=False)
        calibrated_df.to_csv(calibrated_rows_csv_path, index=False)

        fig, axes = plt.subplots(1, 2, figsize=(13, 5))

        t_plot = per_type_metrics_df.sort_values("question_type")
        x = np.arange(len(t_plot))
        width = 0.36

        axes[0].bar(x - width / 2, t_plot["abs_bias_before"], width=width, label="Before")
        axes[0].bar(x + width / 2, t_plot["abs_bias_after"], width=width, label="After")
        axes[0].set_xticks(x)
        axes[0].set_xticklabels(t_plot["question_type"].astype(str), rotation=20)
        axes[0].set_ylabel("Absolute Bias")
        axes[0].set_title("Absolute Bias by Framing Type")
        axes[0].grid(True, axis="y", alpha=0.3)
        axes[0].legend()

        axes[1].bar(x - width / 2, t_plot["mae_before"], width=width, label="Before")
        axes[1].bar(x + width / 2, t_plot["mae_after"], width=width, label="After")
        axes[1].set_xticks(x)
        axes[1].set_xticklabels(t_plot["question_type"].astype(str), rotation=20)
        axes[1].set_ylabel("MAE")
        axes[1].set_title("MAE by Framing Type")
        axes[1].grid(True, axis="y", alpha=0.3)
        axes[1].legend()

        plt.tight_layout()
        fig.savefig(plot_path, dpi=150, bbox_inches="tight")
        plt.close(fig)

        print(f"Saved calibration fit params CSV: {fit_params_csv_path}")
        print(f"Saved calibration per-type metrics CSV: {per_type_metrics_csv_path}")
        print(f"Saved calibration overall metrics CSV: {overall_metrics_csv_path}")
        print(f"Saved calibration row-level CSV: {calibrated_rows_csv_path}")
        print(f"Saved calibration before/after PNG: {plot_path}")

    return {
        "calibrated_df": calibrated_df,
        "fit_params_df": fit_params_df,
        "per_type_metrics_df": per_type_metrics_df,
        "overall_metrics_df": overall_metrics_df,
        "fit_params_csv_path": fit_params_csv_path,
        "per_type_metrics_csv_path": per_type_metrics_csv_path,
        "overall_metrics_csv_path": overall_metrics_csv_path,
        "calibrated_rows_csv_path": calibrated_rows_csv_path,
        "plot_path": plot_path,
        "question_type_map": question_type_map,
        "calibration_method": calibration_method,
    }


def run_persona_ablation_stage2(
    respondent_sample_n=100,
    random_state=42,
    provider="gemini",
    model_name=None,
    save_outputs=True,
    n_bootstrap=2000,
    continue_on_error=True,
    max_total_errors=30,
    max_consecutive_errors=8,
    save_partial_every_question=True,
):
    """
    Stage-2 validation via persona ablation.

    Compares three conditions on the same respondent-question pairs:
    - original: true persona mapped to respondent
    - shuffled: persona texts randomly reassigned across respondents
    - neutral: generic non-informative persona text

    Outputs:
    - detailed row-level CSV across conditions
    - condition summary CSV with mean score and bootstrap CI
    - delta summary CSV for original-vs-shuffled and original-vs-neutral

        Notes:
        - Uses the same ordinal scoring function as the main simulation.
        - Holds respondents/questions constant across conditions to isolate
            the impact of persona assignment.
        - Designed as a follow-up validity check after Stage-1 non-random tests.
    """
        # ------------------------------------------------------------------
        # 1) Load and optionally subsample the respondent dataset
        # ------------------------------------------------------------------
    file_path = DATA_DIR / "yougov_survey_data" / "YouGovProcessedData_train.csv"
    survey_data = load_survey_data(file_path)

    if survey_data is None or survey_data.empty:
        raise ValueError("No survey data available for stage-2 ablation.")

    if respondent_sample_n is not None:
        sample_n = min(int(respondent_sample_n), len(survey_data))
        survey_data = survey_data.sample(n=sample_n, replace=False, random_state=random_state)

    # Build the original persona text map keyed by respondent ID.
    all_persona_texts = create_persona_text_for_people_agent(survey_data)
    respondent_ids = list(all_persona_texts.keys())

    # ------------------------------------------------------------------
    # 2) Create ablation conditions
    # ------------------------------------------------------------------
    # Shuffled condition: randomly reassign existing persona texts to different IDs.
    # This keeps persona content realistic while breaking person-persona alignment.
    rng = np.random.default_rng(random_state)
    shuffled_persona_values = [all_persona_texts[rid] for rid in respondent_ids]
    rng.shuffle(shuffled_persona_values)
    shuffled_persona_map = {
        rid: shuffled_persona_values[idx]
        for idx, rid in enumerate(respondent_ids)
    }

    # Neutral condition: same generic profile for all respondents.
    neutral_persona = (
        "I am a survey respondent in the United Kingdom. "
        "I do not hold strong predefined views and I answer based only on the question wording."
    )

    try:
        from survey_dict import SURVEY_QUESTIONS
    except ImportError:
        from survey_dict import SURVEY_QUESTIONS

    # Map dataset numeric codes (1-7) to survey options (A-G).
    options_dict = {
        "1": "A",
        "2": "B",
        "3": "C",
        "4": "D",
        "5": "E",
        "6": "F",
        "7": "G",
    }

    all_rows = []
    error_rows = []
    run_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_start_ts = time.monotonic()
    consecutive_errors = 0
    total_errors = 0
    abort_run = False

    output_dir = None
    partial_detail_csv_path = None
    partial_error_csv_path = None
    if save_outputs:
        output_dir = DATA_DIR / "output"
        output_dir.mkdir(parents=True, exist_ok=True)
        partial_detail_csv_path = output_dir / f"survey_simulation_stage2_ablation_detail_partial_{run_timestamp}.csv"
        partial_error_csv_path = output_dir / f"survey_simulation_stage2_ablation_errors_partial_{run_timestamp}.csv"

    # Condition-specific persona lookup.
    condition_persona_map = {
        "original": all_persona_texts,
        "shuffled": shuffled_persona_map,
    }

    total_questions = len(SURVEY_QUESTIONS)
    total_respondents = len(survey_data)
    total_conditions = 3  # original, shuffled, neutral
    total_calls = total_questions * total_respondents * total_conditions
    completed_calls = 0

    print("\nStage-2 persona ablation run started")
    print(
        f"- Questions: {total_questions} | Respondents: {total_respondents} | "
        f"Conditions: {total_conditions} | Total model calls (before retries): {total_calls}"
    )

    # ------------------------------------------------------------------
    # 3) Run inference for each question/respondent under each condition
    # ------------------------------------------------------------------
    for q_index, q in enumerate(SURVEY_QUESTIONS, start=1):
        question_id = q.get("id", q.get("col_name", "unknown_question"))
        question_text = q.get("text", "")
        question_col = q.get("col_name", "")

        question_start_calls = completed_calls
        question_start_ts = time.monotonic()

        for _, row in survey_data.iterrows():
            respondent_id = int(row["ID"])
            expected = options_dict[str(int(row[question_col]))]

            for condition_name in ["original", "shuffled", "neutral"]:
                # Select persona according to the active ablation condition.
                if condition_name == "neutral":
                    persona_text = neutral_persona
                else:
                    persona_text = condition_persona_map[condition_name][respondent_id]

                # Query the model as the selected persona.
                answer = ask_agent_survey_question_acc(
                    persona_description=persona_text,
                    question_data=q,
                    provider=provider,
                    model_name=model_name,
                )

                # Stop immediately on API/LLM errors (fail-fast).
                if isinstance(answer, str) and answer.startswith("Error:"):
                    total_errors += 1
                    consecutive_errors += 1
                    error_rows.append(
                        {
                            "run_timestamp": run_timestamp,
                            "question_id": question_id,
                            "question_text": question_text,
                            "respondent_id": respondent_id,
                            "condition": condition_name,
                            "error_message": answer,
                            "total_errors_so_far": total_errors,
                            "consecutive_errors_so_far": consecutive_errors,
                        }
                    )

                    print(
                        f"Warning: API error at question {question_id}, respondent {respondent_id}, "
                        f"condition {condition_name} | total_errors={total_errors}, "
                        f"consecutive_errors={consecutive_errors}"
                    )

                    should_abort = (
                        (not continue_on_error)
                        or (total_errors >= max_total_errors)
                        or (consecutive_errors >= max_consecutive_errors)
                    )

                    if should_abort:
                        print(
                            "Aborting stage-2 run due to error safety threshold. "
                            f"continue_on_error={continue_on_error}, "
                            f"total_errors={total_errors}/{max_total_errors}, "
                            f"consecutive_errors={consecutive_errors}/{max_consecutive_errors}"
                        )
                        abort_run = True
                        break

                    continue

                consecutive_errors = 0

                # Convert answer-vs-expected into ordinal accuracy score in [0,1].
                score = calculate_ordinal_score(answer, expected, q["options"].keys())

                # Save one row per respondent-question-condition combination.
                all_rows.append(
                    {
                        "run_timestamp": run_timestamp,
                        "condition": condition_name,
                        "question_id": question_id,
                        "question_text": question_text,
                        "question_column": question_col,
                        "respondent_id": respondent_id,
                        "persona_text": persona_text,
                        "agent_answer": answer,
                        "expected_answer": expected,
                        "ordinal_accuracy_score": float(score),
                        "provider": provider,
                        "model_name": model_name if model_name else "gemini-2.5-flash",
                    }
                )

                completed_calls += 1
                if completed_calls % 100 == 0 or completed_calls == total_calls:
                    elapsed = time.monotonic() - run_start_ts
                    pct = (completed_calls / total_calls) * 100 if total_calls else 100.0
                    print(
                        f"Progress: {completed_calls}/{total_calls} calls "
                        f"({pct:.1f}%) | elapsed: {elapsed:.1f}s"
                    )

            if abort_run:
                break

        if save_outputs and save_partial_every_question:
            pd.DataFrame(all_rows).to_csv(partial_detail_csv_path, index=False)
            pd.DataFrame(error_rows).to_csv(partial_error_csv_path, index=False)
            print(
                f"Saved partial checkpoint after question {q_index}: "
                f"{partial_detail_csv_path}"
            )
            print(f"Saved partial error log: {partial_error_csv_path}")

        question_elapsed = time.monotonic() - question_start_ts
        question_calls = completed_calls - question_start_calls
        run_elapsed = time.monotonic() - run_start_ts
        run_pct = (completed_calls / total_calls) * 100 if total_calls else 100.0
        print(
            f"Completed question {q_index}/{total_questions} ({question_id}) | "
            f"calls this question: {question_calls} | total progress: {completed_calls}/{total_calls} "
            f"({run_pct:.1f}%) | question time: {question_elapsed:.1f}s | total elapsed: {run_elapsed:.1f}s"
        )

        if abort_run:
            break

    # ------------------------------------------------------------------
    # 4) Build per-condition summary with bootstrap confidence intervals
    # ------------------------------------------------------------------
    detail_df = pd.DataFrame(all_rows)
    error_df = pd.DataFrame(error_rows)

    if detail_df.empty:
        raise RuntimeError(
            "Stage-2 run ended with no successful rows. "
            f"Captured errors: {len(error_df)}"
        )

    def bootstrap_ci(values, n_samples=2000):
        """Bootstrap 95% CI for the mean of a 1D numeric array."""
        values = np.array(values, dtype=float)
        if len(values) == 0:
            return np.nan, np.nan
        bootstrap_means = []
        idx = np.arange(len(values))
        for _ in range(n_samples):
            sampled_idx = rng.choice(idx, size=len(idx), replace=True)
            bootstrap_means.append(np.mean(values[sampled_idx]))
        return float(np.percentile(bootstrap_means, 2.5)), float(np.percentile(bootstrap_means, 97.5))

    summary_rows = []
    for condition_name, group in detail_df.groupby("condition"):
        scores = group["ordinal_accuracy_score"].values
        ci_low, ci_high = bootstrap_ci(scores, n_samples=n_bootstrap)
        summary_rows.append(
            {
                "run_timestamp": run_timestamp,
                "condition": condition_name,
                "n_rows": int(len(group)),
                "mean_ordinal_accuracy_score": float(np.mean(scores)),
                "ci_95_low": ci_low,
                "ci_95_high": ci_high,
            }
        )
    summary_df = pd.DataFrame(summary_rows).sort_values("condition").reset_index(drop=True)

    # ------------------------------------------------------------------
    # 5) Paired deltas between conditions on the same respondent-question unit
    # ------------------------------------------------------------------
    pivot_df = detail_df.pivot_table(
        index=["respondent_id", "question_id"],
        columns="condition",
        values="ordinal_accuracy_score",
        aggfunc="mean",
    )

    delta_rows = []
    delta_pairs = [
        ("original", "shuffled", "original_minus_shuffled"),
        ("original", "neutral", "original_minus_neutral"),
    ]
    for left_cond, right_cond, label in delta_pairs:
        if left_cond in pivot_df.columns and right_cond in pivot_df.columns:
            delta_values = (pivot_df[left_cond] - pivot_df[right_cond]).dropna().values
            ci_low, ci_high = bootstrap_ci(delta_values, n_samples=n_bootstrap)
            delta_rows.append(
                {
                    "run_timestamp": run_timestamp,
                    "delta_name": label,
                    "n_pairs": int(len(delta_values)),
                    "mean_delta": float(np.mean(delta_values)) if len(delta_values) else np.nan,
                    "ci_95_low": ci_low,
                    "ci_95_high": ci_high,
                }
            )
    delta_df = pd.DataFrame(delta_rows)

    # Print concise console summary for quick inspection.
    print("\nStage-2 persona ablation summary:")
    for _, row in summary_df.iterrows():
        print(
            f"- {row['condition']}: mean={row['mean_ordinal_accuracy_score']:.6f}, "
            f"95% CI=({row['ci_95_low']:.6f}, {row['ci_95_high']:.6f}), n={int(row['n_rows'])}"
        )

    if not delta_df.empty:
        print("\nStage-2 deltas:")
        for _, row in delta_df.iterrows():
            print(
                f"- {row['delta_name']}: mean_delta={row['mean_delta']:.6f}, "
                f"95% CI=({row['ci_95_low']:.6f}, {row['ci_95_high']:.6f}), n_pairs={int(row['n_pairs'])}"
            )

    detail_csv_path = None
    summary_csv_path = None
    delta_csv_path = None
    error_csv_path = None
    condition_boxplot_path = None
    delta_ci_plot_path = None

    # ------------------------------------------------------------------
    # 6) Persist outputs for downstream analysis/plotting
    # ------------------------------------------------------------------
    if save_outputs:
        output_dir = DATA_DIR / "output"
        output_dir.mkdir(parents=True, exist_ok=True)

        detail_csv_path = output_dir / f"survey_simulation_stage2_ablation_detail_{run_timestamp}.csv"
        summary_csv_path = output_dir / f"survey_simulation_stage2_ablation_summary_{run_timestamp}.csv"
        delta_csv_path = output_dir / f"survey_simulation_stage2_ablation_deltas_{run_timestamp}.csv"
        error_csv_path = output_dir / f"survey_simulation_stage2_ablation_errors_{run_timestamp}.csv"

        detail_df.to_csv(detail_csv_path, index=False)
        summary_df.to_csv(summary_csv_path, index=False)
        delta_df.to_csv(delta_csv_path, index=False)
        error_df.to_csv(error_csv_path, index=False)

        print(f"Saved stage-2 detail CSV: {detail_csv_path}")
        print(f"Saved stage-2 summary CSV: {summary_csv_path}")
        print(f"Saved stage-2 delta CSV: {delta_csv_path}")
        print(f"Saved stage-2 error CSV: {error_csv_path}")

        condition_boxplot_path = output_dir / f"survey_simulation_stage2_ablation_boxplot_{run_timestamp}.png"
        condition_order = ["original", "shuffled", "neutral"]
        boxplot_data = []
        boxplot_labels = []
        for condition_name in condition_order:
            condition_scores = detail_df.loc[
                detail_df["condition"] == condition_name,
                "ordinal_accuracy_score",
            ].dropna().tolist()
            if condition_scores:
                boxplot_data.append(condition_scores)
                boxplot_labels.append(condition_name)

        if boxplot_data:
            fig, ax = plt.subplots(figsize=(10, 6))
            ax.boxplot(boxplot_data, whis=[5, 95], tick_labels=boxplot_labels)
            ax.set_xlabel("Condition")
            ax.set_ylabel("Ordinal Accuracy Score (0 to 1)")
            ax.set_title("Stage-2 Persona Ablation: Score Distribution by Condition")
            ax.set_ylim(-0.05, 1.05)
            ax.grid(True, axis="y", alpha=0.3)
            plt.tight_layout()
            fig.savefig(condition_boxplot_path, dpi=150, bbox_inches="tight")
            plt.close(fig)
            print(f"Saved stage-2 condition boxplot PNG: {condition_boxplot_path}")
        else:
            condition_boxplot_path = None

        if not delta_df.empty:
            delta_ci_plot_path = output_dir / f"survey_simulation_stage2_ablation_deltas_ci_{run_timestamp}.png"
            x_positions = np.arange(len(delta_df))
            means = delta_df["mean_delta"].to_numpy(dtype=float)
            ci_lows = delta_df["ci_95_low"].to_numpy(dtype=float)
            ci_highs = delta_df["ci_95_high"].to_numpy(dtype=float)
            yerr = np.vstack([
                np.clip(means - ci_lows, a_min=0, a_max=None),
                np.clip(ci_highs - means, a_min=0, a_max=None),
            ])

            fig, ax = plt.subplots(figsize=(10, 5))
            ax.errorbar(
                x_positions,
                means,
                yerr=yerr,
                fmt="o",
                capsize=6,
                linewidth=1.5,
                color="tab:blue",
            )
            ax.axhline(0.0, color="gray", linestyle="--", linewidth=1)
            ax.set_xticks(x_positions)
            ax.set_xticklabels(delta_df["delta_name"].tolist(), rotation=0)
            ax.set_ylabel("Mean Delta in Ordinal Accuracy Score")
            ax.set_title("Stage-2 Persona Ablation: Condition Deltas with 95% CI")
            ax.grid(True, axis="y", alpha=0.3)
            plt.tight_layout()
            fig.savefig(delta_ci_plot_path, dpi=150, bbox_inches="tight")
            plt.close(fig)
            print(f"Saved stage-2 delta CI PNG: {delta_ci_plot_path}")
        else:
            delta_ci_plot_path = None

    # Return both in-memory DataFrames and file paths for flexible downstream use.
    return {
        "detail_df": detail_df,
        "summary_df": summary_df,
        "delta_df": delta_df,
        "error_df": error_df,
        "detail_csv_path": detail_csv_path,
        "summary_csv_path": summary_csv_path,
        "delta_csv_path": delta_csv_path,
        "error_csv_path": error_csv_path,
        "partial_detail_csv_path": partial_detail_csv_path,
        "partial_error_csv_path": partial_error_csv_path,
        "condition_boxplot_path": condition_boxplot_path,
        "delta_ci_plot_path": delta_ci_plot_path,
    }


def plot_stage2_ablation_from_saved_results(
    detail_csv_path=None,
    delta_csv_path=None,
    output_dir=None,
    whis=(5, 95),
    condition_order=("original", "shuffled", "neutral"),
):
    """
    Rebuild Stage-2 ablation plots from saved CSV files (no API calls).

    Parameters:
        detail_csv_path (str | Path | None):
            Path to stage-2 detail CSV. If None, the newest
            survey_simulation_stage2_ablation_detail_*.csv is used.
        delta_csv_path (str | Path | None):
            Path to stage-2 delta CSV. If None, the newest
            survey_simulation_stage2_ablation_deltas_*.csv is used.
        output_dir (str | Path | None):
            Destination directory for generated PNGs. Defaults to data/output.
        whis (tuple): Whisker range for boxplot (default (5,95)).
        condition_order (tuple[str,...]): Condition display order.

    Returns:
        dict: Loaded DataFrames and generated plot paths.
    """
    base_output_dir = DATA_DIR / "output" if output_dir is None else Path(output_dir)
    base_output_dir.mkdir(parents=True, exist_ok=True)

    if detail_csv_path is None:
        detail_candidates = sorted(
            base_output_dir.glob("survey_simulation_stage2_ablation_detail_*.csv")
        )
        if not detail_candidates:
            raise FileNotFoundError(
                f"No survey_simulation_stage2_ablation_detail_*.csv found in: {base_output_dir}"
            )
        detail_csv_path = detail_candidates[-1]
    else:
        detail_csv_path = Path(detail_csv_path)

    if delta_csv_path is None:
        delta_candidates = sorted(
            base_output_dir.glob("survey_simulation_stage2_ablation_deltas_*.csv")
        )
        if not delta_candidates:
            raise FileNotFoundError(
                f"No survey_simulation_stage2_ablation_deltas_*.csv found in: {base_output_dir}"
            )
        delta_csv_path = delta_candidates[-1]
    else:
        delta_csv_path = Path(delta_csv_path)

    if not detail_csv_path.exists():
        raise FileNotFoundError(f"Stage-2 detail CSV not found: {detail_csv_path}")
    if not delta_csv_path.exists():
        raise FileNotFoundError(f"Stage-2 delta CSV not found: {delta_csv_path}")

    detail_df = pd.read_csv(detail_csv_path)
    delta_df = pd.read_csv(delta_csv_path)

    required_detail_cols = {"condition", "ordinal_accuracy_score"}
    missing_detail_cols = required_detail_cols - set(detail_df.columns)
    if missing_detail_cols:
        raise ValueError(
            f"Detail CSV missing required columns: {sorted(missing_detail_cols)}"
        )

    required_delta_cols = {"delta_name", "mean_delta", "ci_95_low", "ci_95_high"}
    missing_delta_cols = required_delta_cols - set(delta_df.columns)
    if missing_delta_cols:
        raise ValueError(
            f"Delta CSV missing required columns: {sorted(missing_delta_cols)}"
        )

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    condition_boxplot_path = base_output_dir / f"survey_simulation_stage2_ablation_boxplot_from_saved_{timestamp}.png"
    delta_ci_plot_path = base_output_dir / f"survey_simulation_stage2_ablation_deltas_ci_from_saved_{timestamp}.png"

    boxplot_data = []
    boxplot_labels = []
    for condition_name in condition_order:
        condition_scores = detail_df.loc[
            detail_df["condition"] == condition_name,
            "ordinal_accuracy_score",
        ].dropna().tolist()
        if condition_scores:
            boxplot_data.append(condition_scores)
            boxplot_labels.append(condition_name)

    if not boxplot_data:
        raise ValueError("No valid Stage-2 condition score values found to plot.")

    fig, ax = plt.subplots(figsize=(10, 6))
    ax.boxplot(boxplot_data, whis=list(whis), tick_labels=boxplot_labels)
    ax.set_xlabel("Condition")
    ax.set_ylabel("Ordinal Accuracy Score (0 to 1)")
    ax.set_title("Stage-2 Persona Ablation: Score Distribution by Condition")
    ax.set_ylim(-0.05, 1.05)
    ax.grid(True, axis="y", alpha=0.3)
    plt.tight_layout()
    fig.savefig(condition_boxplot_path, dpi=150, bbox_inches="tight")
    plt.close(fig)

    if not delta_df.empty:
        x_positions = np.arange(len(delta_df))
        means = delta_df["mean_delta"].to_numpy(dtype=float)
        ci_lows = delta_df["ci_95_low"].to_numpy(dtype=float)
        ci_highs = delta_df["ci_95_high"].to_numpy(dtype=float)
        yerr = np.vstack([
            np.clip(means - ci_lows, a_min=0, a_max=None),
            np.clip(ci_highs - means, a_min=0, a_max=None),
        ])

        fig, ax = plt.subplots(figsize=(10, 5))
        ax.errorbar(
            x_positions,
            means,
            yerr=yerr,
            fmt="o",
            capsize=6,
            linewidth=1.5,
            color="tab:blue",
        )
        ax.axhline(0.0, color="gray", linestyle="--", linewidth=1)
        ax.set_xticks(x_positions)
        ax.set_xticklabels(delta_df["delta_name"].tolist(), rotation=0)
        ax.set_ylabel("Mean Delta in Ordinal Accuracy Score")
        ax.set_title("Stage-2 Persona Ablation: Condition Deltas with 95% CI")
        ax.grid(True, axis="y", alpha=0.3)
        plt.tight_layout()
        fig.savefig(delta_ci_plot_path, dpi=150, bbox_inches="tight")
        plt.close(fig)
    else:
        delta_ci_plot_path = None

    print(f"Loaded stage-2 detail CSV: {detail_csv_path}")
    print(f"Loaded stage-2 delta CSV: {delta_csv_path}")
    print(f"Saved stage-2 condition boxplot PNG: {condition_boxplot_path}")
    if delta_ci_plot_path is not None:
        print(f"Saved stage-2 delta CI PNG: {delta_ci_plot_path}")
    else:
        print("Saved stage-2 delta CI PNG: skipped (empty delta CSV)")

    return {
        "detail_df": detail_df,
        "delta_df": delta_df,
        "detail_csv_path": detail_csv_path,
        "delta_csv_path": delta_csv_path,
        "condition_boxplot_path": condition_boxplot_path,
        "delta_ci_plot_path": delta_ci_plot_path,
    }


def resume_persona_ablation_stage2_from_partial(
    partial_detail_csv_path=None,
    respondent_sample_n=100,
    random_state=42,
    provider="gemini",
    model_name=None,
    save_outputs=True,
    n_bootstrap=2000,
    continue_on_error=True,
    max_total_errors=30,
    max_consecutive_errors=8,
):
    """
    Resume Stage-2 ablation from a saved partial detail CSV.

    This function loads existing successful rows, identifies missing
    (question_id, respondent_id, condition) tuples, runs only those, and then
    rebuilds summary/delta outputs and plots.
    """
    output_dir = DATA_DIR / "output"
    output_dir.mkdir(parents=True, exist_ok=True)

    if partial_detail_csv_path is None:
        candidates = sorted(output_dir.glob("survey_simulation_stage2_ablation_detail_partial_*.csv"))
        if not candidates:
            raise FileNotFoundError(
                f"No survey_simulation_stage2_ablation_detail_partial_*.csv found in: {output_dir}"
            )
        partial_detail_csv_path = candidates[-1]
    else:
        partial_detail_csv_path = Path(partial_detail_csv_path)

    if not partial_detail_csv_path.exists():
        raise FileNotFoundError(f"Partial detail CSV not found: {partial_detail_csv_path}")

    existing_detail_df = pd.read_csv(partial_detail_csv_path)
    required_cols = {"question_id", "respondent_id", "condition"}
    missing_cols = required_cols - set(existing_detail_df.columns)
    if missing_cols:
        raise ValueError(
            f"Partial detail CSV missing required columns: {sorted(missing_cols)}"
        )

    file_path = DATA_DIR / "yougov_survey_data" / "YouGovProcessedData_train.csv"
    survey_data = load_survey_data(file_path)
    if survey_data is None or survey_data.empty:
        raise ValueError("No survey data available for Stage-2 resume.")

    if respondent_sample_n is not None:
        sample_n = min(int(respondent_sample_n), len(survey_data))
        survey_data = survey_data.sample(n=sample_n, replace=False, random_state=random_state)

    all_persona_texts = create_persona_text_for_people_agent(survey_data)
    respondent_ids = list(all_persona_texts.keys())

    rng = np.random.default_rng(random_state)
    shuffled_persona_values = [all_persona_texts[rid] for rid in respondent_ids]
    rng.shuffle(shuffled_persona_values)
    shuffled_persona_map = {
        rid: shuffled_persona_values[idx]
        for idx, rid in enumerate(respondent_ids)
    }

    neutral_persona = (
        "I am a survey respondent in the United Kingdom. "
        "I do not hold strong predefined views and I answer based only on the question wording."
    )

    try:
        from survey_dict import SURVEY_QUESTIONS
    except ImportError:
        from survey_dict import SURVEY_QUESTIONS

    options_dict = {
        "1": "A",
        "2": "B",
        "3": "C",
        "4": "D",
        "5": "E",
        "6": "F",
        "7": "G",
    }

    completed_keys = set(
        zip(
            existing_detail_df["question_id"].astype(str).tolist(),
            existing_detail_df["respondent_id"].astype(int).tolist(),
            existing_detail_df["condition"].astype(str).tolist(),
        )
    )

    condition_persona_map = {
        "original": all_persona_texts,
        "shuffled": shuffled_persona_map,
    }

    work_items = []
    for q in SURVEY_QUESTIONS:
        question_id = q.get("id", q.get("col_name", "unknown_question"))
        question_text = q.get("text", "")
        question_col = q.get("col_name", "")
        for _, row in survey_data.iterrows():
            respondent_id = int(row["ID"])
            expected = options_dict[str(int(row[question_col]))]
            for condition_name in ["original", "shuffled", "neutral"]:
                key = (str(question_id), respondent_id, condition_name)
                if key in completed_keys:
                    continue
                work_items.append(
                    {
                        "question_id": str(question_id),
                        "question_text": question_text,
                        "question_col": question_col,
                        "respondent_id": respondent_id,
                        "expected": expected,
                        "condition": condition_name,
                        "question_data": q,
                    }
                )

    print("\nStage-2 resume started")
    print(f"- Loaded partial file: {partial_detail_csv_path}")
    print(f"- Existing completed rows: {len(existing_detail_df)}")
    print(f"- Missing calls to run: {len(work_items)}")

    run_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_start_ts = time.monotonic()
    new_rows = []
    error_rows = []
    total_errors = 0
    consecutive_errors = 0

    for idx, item in enumerate(work_items, start=1):
        condition_name = item["condition"]
        respondent_id = item["respondent_id"]

        if condition_name == "neutral":
            persona_text = neutral_persona
        else:
            persona_text = condition_persona_map[condition_name][respondent_id]

        answer = ask_agent_survey_question_acc(
            persona_description=persona_text,
            question_data=item["question_data"],
            provider=provider,
            model_name=model_name,
        )

        if isinstance(answer, str) and answer.startswith("Error:"):
            total_errors += 1
            consecutive_errors += 1
            error_rows.append(
                {
                    "run_timestamp": run_timestamp,
                    "question_id": item["question_id"],
                    "question_text": item["question_text"],
                    "respondent_id": respondent_id,
                    "condition": condition_name,
                    "error_message": answer,
                    "resume_item_index": idx,
                    "total_errors_so_far": total_errors,
                    "consecutive_errors_so_far": consecutive_errors,
                }
            )

            should_abort = (
                (not continue_on_error)
                or (total_errors >= max_total_errors)
                or (consecutive_errors >= max_consecutive_errors)
            )
            if should_abort:
                print(
                    "Aborting resume due to error safety threshold. "
                    f"continue_on_error={continue_on_error}, "
                    f"total_errors={total_errors}/{max_total_errors}, "
                    f"consecutive_errors={consecutive_errors}/{max_consecutive_errors}"
                )
                break
            continue

        consecutive_errors = 0
        score = calculate_ordinal_score(answer, item["expected"], item["question_data"]["options"].keys())

        new_rows.append(
            {
                "run_timestamp": run_timestamp,
                "condition": condition_name,
                "question_id": item["question_id"],
                "question_text": item["question_text"],
                "question_column": item["question_col"],
                "respondent_id": respondent_id,
                "persona_text": persona_text,
                "agent_answer": answer,
                "expected_answer": item["expected"],
                "ordinal_accuracy_score": float(score),
                "provider": provider,
                "model_name": model_name if model_name else "gemini-2.5-flash",
            }
        )

        if idx % 100 == 0 or idx == len(work_items):
            elapsed = time.monotonic() - run_start_ts
            pct = (idx / len(work_items)) * 100 if work_items else 100.0
            print(f"Resume progress: {idx}/{len(work_items)} ({pct:.1f}%) | elapsed: {elapsed:.1f}s")

    new_df = pd.DataFrame(new_rows)
    error_df = pd.DataFrame(error_rows)

    combined_detail_df = pd.concat([existing_detail_df, new_df], ignore_index=True)
    combined_detail_df["respondent_id"] = combined_detail_df["respondent_id"].astype(int)
    combined_detail_df["question_id"] = combined_detail_df["question_id"].astype(str)
    combined_detail_df["condition"] = combined_detail_df["condition"].astype(str)
    combined_detail_df = combined_detail_df.drop_duplicates(
        subset=["question_id", "respondent_id", "condition"], keep="first"
    ).reset_index(drop=True)

    if combined_detail_df.empty:
        raise RuntimeError("Resume finished with no successful data rows.")

    def bootstrap_ci(values, n_samples=2000):
        values = np.array(values, dtype=float)
        if len(values) == 0:
            return np.nan, np.nan
        means = []
        idxs = np.arange(len(values))
        for _ in range(n_samples):
            sampled_idx = rng.choice(idxs, size=len(idxs), replace=True)
            means.append(np.mean(values[sampled_idx]))
        return float(np.percentile(means, 2.5)), float(np.percentile(means, 97.5))

    summary_rows = []
    for condition_name, group in combined_detail_df.groupby("condition"):
        scores = group["ordinal_accuracy_score"].astype(float).values
        ci_low, ci_high = bootstrap_ci(scores, n_samples=n_bootstrap)
        summary_rows.append(
            {
                "run_timestamp": run_timestamp,
                "condition": condition_name,
                "n_rows": int(len(group)),
                "mean_ordinal_accuracy_score": float(np.mean(scores)),
                "ci_95_low": ci_low,
                "ci_95_high": ci_high,
            }
        )
    summary_df = pd.DataFrame(summary_rows).sort_values("condition").reset_index(drop=True)

    pivot_df = combined_detail_df.pivot_table(
        index=["respondent_id", "question_id"],
        columns="condition",
        values="ordinal_accuracy_score",
        aggfunc="mean",
    )

    delta_rows = []
    for left_cond, right_cond, label in [
        ("original", "shuffled", "original_minus_shuffled"),
        ("original", "neutral", "original_minus_neutral"),
    ]:
        if left_cond in pivot_df.columns and right_cond in pivot_df.columns:
            delta_values = (pivot_df[left_cond] - pivot_df[right_cond]).dropna().values
            ci_low, ci_high = bootstrap_ci(delta_values, n_samples=n_bootstrap)
            delta_rows.append(
                {
                    "run_timestamp": run_timestamp,
                    "delta_name": label,
                    "n_pairs": int(len(delta_values)),
                    "mean_delta": float(np.mean(delta_values)) if len(delta_values) else np.nan,
                    "ci_95_low": ci_low,
                    "ci_95_high": ci_high,
                }
            )
    delta_df = pd.DataFrame(delta_rows)

    detail_csv_path = None
    summary_csv_path = None
    delta_csv_path = None
    error_csv_path = None
    condition_boxplot_path = None
    delta_ci_plot_path = None

    if save_outputs:
        detail_csv_path = output_dir / f"survey_simulation_stage2_ablation_detail_resumed_{run_timestamp}.csv"
        summary_csv_path = output_dir / f"survey_simulation_stage2_ablation_summary_resumed_{run_timestamp}.csv"
        delta_csv_path = output_dir / f"survey_simulation_stage2_ablation_deltas_resumed_{run_timestamp}.csv"
        error_csv_path = output_dir / f"survey_simulation_stage2_ablation_errors_resumed_{run_timestamp}.csv"

        combined_detail_df.to_csv(detail_csv_path, index=False)
        summary_df.to_csv(summary_csv_path, index=False)
        delta_df.to_csv(delta_csv_path, index=False)
        error_df.to_csv(error_csv_path, index=False)

        condition_order = ["original", "shuffled", "neutral"]
        boxplot_data = []
        boxplot_labels = []
        for condition_name in condition_order:
            values = combined_detail_df.loc[
                combined_detail_df["condition"] == condition_name,
                "ordinal_accuracy_score",
            ].dropna().tolist()
            if values:
                boxplot_data.append(values)
                boxplot_labels.append(condition_name)

        if boxplot_data:
            condition_boxplot_path = output_dir / f"survey_simulation_stage2_ablation_boxplot_resumed_{run_timestamp}.png"
            fig, ax = plt.subplots(figsize=(10, 6))
            ax.boxplot(boxplot_data, whis=[5, 95], tick_labels=boxplot_labels)
            ax.set_xlabel("Condition")
            ax.set_ylabel("Ordinal Accuracy Score (0 to 1)")
            ax.set_title("Stage-2 Persona Ablation (Resumed): Score Distribution by Condition")
            ax.set_ylim(-0.05, 1.05)
            ax.grid(True, axis="y", alpha=0.3)
            plt.tight_layout()
            fig.savefig(condition_boxplot_path, dpi=150, bbox_inches="tight")
            plt.close(fig)

        if not delta_df.empty:
            delta_ci_plot_path = output_dir / f"survey_simulation_stage2_ablation_deltas_ci_resumed_{run_timestamp}.png"
            x_positions = np.arange(len(delta_df))
            means = delta_df["mean_delta"].to_numpy(dtype=float)
            ci_lows = delta_df["ci_95_low"].to_numpy(dtype=float)
            ci_highs = delta_df["ci_95_high"].to_numpy(dtype=float)
            yerr = np.vstack([
                np.clip(means - ci_lows, a_min=0, a_max=None),
                np.clip(ci_highs - means, a_min=0, a_max=None),
            ])

            fig, ax = plt.subplots(figsize=(10, 5))
            ax.errorbar(
                x_positions,
                means,
                yerr=yerr,
                fmt="o",
                capsize=6,
                linewidth=1.5,
                color="tab:blue",
            )
            ax.axhline(0.0, color="gray", linestyle="--", linewidth=1)
            ax.set_xticks(x_positions)
            ax.set_xticklabels(delta_df["delta_name"].tolist(), rotation=0)
            ax.set_ylabel("Mean Delta in Ordinal Accuracy Score")
            ax.set_title("Stage-2 Persona Ablation (Resumed): Condition Deltas with 95% CI")
            ax.grid(True, axis="y", alpha=0.3)
            plt.tight_layout()
            fig.savefig(delta_ci_plot_path, dpi=150, bbox_inches="tight")
            plt.close(fig)

        print(f"Saved resumed detail CSV: {detail_csv_path}")
        print(f"Saved resumed summary CSV: {summary_csv_path}")
        print(f"Saved resumed delta CSV: {delta_csv_path}")
        print(f"Saved resumed error CSV: {error_csv_path}")
        if condition_boxplot_path is not None:
            print(f"Saved resumed condition boxplot PNG: {condition_boxplot_path}")
        if delta_ci_plot_path is not None:
            print(f"Saved resumed delta CI PNG: {delta_ci_plot_path}")

    return {
        "detail_df": combined_detail_df,
        "summary_df": summary_df,
        "delta_df": delta_df,
        "error_df": error_df,
        "detail_csv_path": detail_csv_path,
        "summary_csv_path": summary_csv_path,
        "delta_csv_path": delta_csv_path,
        "error_csv_path": error_csv_path,
        "condition_boxplot_path": condition_boxplot_path,
        "delta_ci_plot_path": delta_ci_plot_path,
        "partial_detail_csv_path": partial_detail_csv_path,
        "new_rows_added": int(len(new_df)),
        "existing_rows_loaded": int(len(existing_detail_df)),
        "final_rows_total": int(len(combined_detail_df)),
    }


def analyze_stage2_diagnostics_from_saved_results(
    detail_csv_path=None,
    output_dir=None,
    n_bootstrap=2000,
    random_state=42,
    save_outputs=True,
):
    """
    Analyze Stage-2 ablation results with per-question diagnostics.

    Produces:
    - per-question condition metrics (mean ordinal score + exact-match rate)
    - per-question paired deltas with bootstrap CIs
    - condition answer-distribution table
    - diagnostic PNG plots for quick interpretation
    """
    base_output_dir = DATA_DIR / "output" if output_dir is None else Path(output_dir)
    base_output_dir.mkdir(parents=True, exist_ok=True)

    if detail_csv_path is None:
        candidates = sorted(base_output_dir.glob("survey_simulation_stage2_ablation_detail*_*.csv"))
        candidates = [c for c in candidates if "partial" not in c.name]
        if not candidates:
            raise FileNotFoundError(
                f"No stage-2 detail CSV found in: {base_output_dir}"
            )
        detail_csv_path = candidates[-1]
    else:
        detail_csv_path = Path(detail_csv_path)

    if not detail_csv_path.exists():
        raise FileNotFoundError(f"Stage-2 detail CSV not found: {detail_csv_path}")

    detail_df = pd.read_csv(detail_csv_path)
    required_cols = {
        "question_id",
        "respondent_id",
        "condition",
        "agent_answer",
        "expected_answer",
        "ordinal_accuracy_score",
    }
    missing_cols = required_cols - set(detail_df.columns)
    if missing_cols:
        raise ValueError(f"Detail CSV missing required columns: {sorted(missing_cols)}")

    valid_answers = set(["A", "B", "C", "D", "E", "F", "G"])
    detail_df["agent_answer"] = detail_df["agent_answer"].astype(str).str.strip().str.upper()
    detail_df["expected_answer"] = detail_df["expected_answer"].astype(str).str.strip().str.upper()
    detail_df = detail_df[
        detail_df["agent_answer"].isin(valid_answers)
        & detail_df["expected_answer"].isin(valid_answers)
    ].copy()

    if detail_df.empty:
        raise ValueError("No valid A-G rows found in Stage-2 detail CSV.")

    detail_df["ordinal_accuracy_score"] = pd.to_numeric(
        detail_df["ordinal_accuracy_score"], errors="coerce"
    )
    detail_df = detail_df[detail_df["ordinal_accuracy_score"].notna()].copy()

    detail_df["exact_match"] = (
        detail_df["agent_answer"] == detail_df["expected_answer"]
    ).astype(float)

    condition_order = ["original", "shuffled", "neutral"]
    question_order = list(dict.fromkeys(detail_df["question_id"].astype(str).tolist()))
    detail_df["question_id"] = detail_df["question_id"].astype(str)

    per_question_rows = []
    for question_id in question_order:
        q_df = detail_df[detail_df["question_id"] == question_id]
        for condition_name in condition_order:
            subset = q_df[q_df["condition"] == condition_name]
            if subset.empty:
                continue
            per_question_rows.append(
                {
                    "question_id": question_id,
                    "condition": condition_name,
                    "n_rows": int(len(subset)),
                    "mean_ordinal_accuracy_score": float(subset["ordinal_accuracy_score"].mean()),
                    "exact_match_rate": float(subset["exact_match"].mean()),
                }
            )
    per_question_df = pd.DataFrame(per_question_rows)

    rng = np.random.default_rng(random_state)

    def bootstrap_ci(values, n_samples=2000):
        values = np.array(values, dtype=float)
        if len(values) == 0:
            return np.nan, np.nan
        idx = np.arange(len(values))
        means = []
        for _ in range(n_samples):
            sampled_idx = rng.choice(idx, size=len(idx), replace=True)
            means.append(np.mean(values[sampled_idx]))
        return float(np.percentile(means, 2.5)), float(np.percentile(means, 97.5))

    delta_rows = []
    for question_id in question_order:
        q_df = detail_df[detail_df["question_id"] == question_id]
        pivot = q_df.pivot_table(
            index="respondent_id",
            columns="condition",
            values="ordinal_accuracy_score",
            aggfunc="mean",
        )
        for left_cond, right_cond, delta_name in [
            ("original", "shuffled", "original_minus_shuffled"),
            ("original", "neutral", "original_minus_neutral"),
        ]:
            if left_cond in pivot.columns and right_cond in pivot.columns:
                deltas = (pivot[left_cond] - pivot[right_cond]).dropna().values
                ci_low, ci_high = bootstrap_ci(deltas, n_samples=n_bootstrap)
                delta_rows.append(
                    {
                        "question_id": question_id,
                        "delta_name": delta_name,
                        "n_pairs": int(len(deltas)),
                        "mean_delta": float(np.mean(deltas)) if len(deltas) else np.nan,
                        "ci_95_low": ci_low,
                        "ci_95_high": ci_high,
                    }
                )
    per_question_delta_df = pd.DataFrame(delta_rows)

    distribution_df = (
        detail_df.groupby(["condition", "agent_answer"]).size().rename("count").reset_index()
    )
    totals = distribution_df.groupby("condition")["count"].transform("sum")
    distribution_df["proportion"] = distribution_df["count"] / totals

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    per_question_csv_path = None
    per_question_delta_csv_path = None
    distribution_csv_path = None
    per_question_means_png_path = None
    per_question_deltas_png_path = None

    if save_outputs:
        per_question_csv_path = base_output_dir / f"survey_simulation_stage2_per_question_metrics_{timestamp}.csv"
        per_question_delta_csv_path = base_output_dir / f"survey_simulation_stage2_per_question_deltas_{timestamp}.csv"
        distribution_csv_path = base_output_dir / f"survey_simulation_stage2_answer_distribution_{timestamp}.csv"

        per_question_df.to_csv(per_question_csv_path, index=False)
        per_question_delta_df.to_csv(per_question_delta_csv_path, index=False)
        distribution_df.to_csv(distribution_csv_path, index=False)

        # Plot 1: per-question mean ordinal score by condition
        mean_table = per_question_df.pivot_table(
            index="question_id",
            columns="condition",
            values="mean_ordinal_accuracy_score",
            aggfunc="mean",
        ).reindex(index=question_order)

        x = np.arange(len(mean_table.index))
        width = 0.25
        fig, ax = plt.subplots(figsize=(12, 6))
        for i, condition_name in enumerate(condition_order):
            if condition_name in mean_table.columns:
                ax.bar(
                    x + (i - 1) * width,
                    mean_table[condition_name].values,
                    width=width,
                    label=condition_name,
                )
        ax.set_xticks(x)
        ax.set_xticklabels(mean_table.index.tolist())
        ax.set_ylim(0.0, 1.0)
        ax.set_xlabel("Question")
        ax.set_ylabel("Mean Ordinal Accuracy Score")
        ax.set_title("Stage-2 Per-Question Mean Ordinal Score by Condition")
        ax.legend()
        ax.grid(True, axis="y", alpha=0.3)
        plt.tight_layout()
        per_question_means_png_path = base_output_dir / f"survey_simulation_stage2_per_question_means_{timestamp}.png"
        fig.savefig(per_question_means_png_path, dpi=150, bbox_inches="tight")
        plt.close(fig)

        # Plot 2: per-question deltas with 95% CI
        if not per_question_delta_df.empty:
            q_labels = question_order
            fig, ax = plt.subplots(figsize=(12, 6))
            for delta_name, color, offset in [
                ("original_minus_shuffled", "tab:blue", -0.08),
                ("original_minus_neutral", "tab:orange", 0.08),
            ]:
                sub = per_question_delta_df[per_question_delta_df["delta_name"] == delta_name]
                if sub.empty:
                    continue
                sub = sub.set_index("question_id").reindex(q_labels).reset_index()
                x_vals = np.arange(len(q_labels), dtype=float) + offset
                means = sub["mean_delta"].to_numpy(dtype=float)
                lows = sub["ci_95_low"].to_numpy(dtype=float)
                highs = sub["ci_95_high"].to_numpy(dtype=float)
                yerr = np.vstack([
                    np.clip(means - lows, a_min=0, a_max=None),
                    np.clip(highs - means, a_min=0, a_max=None),
                ])
                ax.errorbar(
                    x_vals,
                    means,
                    yerr=yerr,
                    fmt="o",
                    capsize=5,
                    label=delta_name,
                    color=color,
                )

            ax.axhline(0.0, color="gray", linestyle="--", linewidth=1)
            ax.set_xticks(np.arange(len(q_labels)))
            ax.set_xticklabels(q_labels)
            ax.set_xlabel("Question")
            ax.set_ylabel("Mean Delta in Ordinal Accuracy Score")
            ax.set_title("Stage-2 Per-Question Deltas with 95% CI")
            ax.legend()
            ax.grid(True, axis="y", alpha=0.3)
            plt.tight_layout()
            per_question_deltas_png_path = base_output_dir / f"survey_simulation_stage2_per_question_deltas_{timestamp}.png"
            fig.savefig(per_question_deltas_png_path, dpi=150, bbox_inches="tight")
            plt.close(fig)

        print(f"Loaded Stage-2 detail CSV: {detail_csv_path}")
        print(f"Saved per-question metrics CSV: {per_question_csv_path}")
        print(f"Saved per-question deltas CSV: {per_question_delta_csv_path}")
        print(f"Saved answer distribution CSV: {distribution_csv_path}")
        print(f"Saved per-question means PNG: {per_question_means_png_path}")
        if per_question_deltas_png_path is not None:
            print(f"Saved per-question deltas PNG: {per_question_deltas_png_path}")

    return {
        "detail_df": detail_df,
        "per_question_df": per_question_df,
        "per_question_delta_df": per_question_delta_df,
        "distribution_df": distribution_df,
        "detail_csv_path": detail_csv_path,
        "per_question_csv_path": per_question_csv_path,
        "per_question_delta_csv_path": per_question_delta_csv_path,
        "distribution_csv_path": distribution_csv_path,
        "per_question_means_png_path": per_question_means_png_path,
        "per_question_deltas_png_path": per_question_deltas_png_path,
    }


# def run_simulation():

#     # Create a GenAIService instance
#     from gabm.io.llm.genai import GenAIService
#     genai_service = GenAIService()
    
#     file_path = DATA_DIR / "yougov_survey_data" / "YouGovProcessedData.csv"
#     survey_data = load_survey_data(file_path)
#     survey_data = survey_data.head(10)
#     all_persona_texts = create_persona_text_for_people_agent(survey_data)
#     influencer_personas = create_persona_text_for_influencer_agent()
#     G_people_agent = create_networkx_graph_between_people_agents(all_persona_texts)
#     create_networkx_graph_between_people_and_influencer_agents(G_people_agent, influencer_personas)
#     memory_store = AgentMemoryStore(max_turns=8)

#     try:
#         from survey_dict import SURVEY_QUESTIONS
#     except ImportError:
#         from survey_dict import SURVEY_QUESTIONS

#     for question_data in SURVEY_QUESTIONS:
#         question_id = question_data.get('id')
#         print(f"\n{'='*70}")
#         print(f"QUESTION: {question_id} - {question_data['text'][:60]}...")
#         print(f"{'='*70}")

#         question_results = {}

#         for n_rounds in range(1, 2):
#             print(f"\n--- ROUND {n_rounds} ---")
#             question_results[n_rounds] = {}

#             for influencer_name, influencer_persona in influencer_personas.items():
#                 print(f"\nExposing agents to: {influencer_name}")

#                 topic = strip_after_colon(question_data["text"])
#                 influencer_message = draft_influencer_persuasive_message(
#                     influencer_name,
#                     influencer_persona,
#                     topic,
#                     provider="gemini",
#                     model_name=None
#                 )
#                 print(f"Message: {influencer_message[:80]}...")
#                 influencer_agent_answers = {}
#                 for people_node, persona_description in all_persona_texts.items():
#                     agent_answer = ask_agent_survey_question(
#                         persona_description=persona_description,
#                         question_data=question_data,
#                         provider='gemini',
#                         agent_id=people_node,
#                         influencer_message=influencer_message,
#                         memory_store=memory_store,
#                         question_id=question_id
#                     )

#                     influencer_agent_answers[people_node] = agent_answer

#                 question_results[n_rounds][influencer_name] = influencer_agent_answers

#                 answer_counts = {}
#                 for ans in influencer_agent_answers.values():
#                     answer_counts[ans] = answer_counts.get(ans, 0) + 1
#                 print(f"Answers from all agents: {answer_counts}")
#         print(f"\n{'='*70}")
#         print(f"Generating visualization for {question_id}...")
#         print(f"{'='*70}")
#         fig = plot_question_results(question_results, question_id)
#         fig.savefig(f"data/output/question_{question_id}_results.png", dpi=150, bbox_inches='tight')
#         print(f"Saved plot to: data/output/question_{question_id}_results.png")

#         break

# from gabm.io.llm.openai import OpenAIService
# api_keys = get_api_keys_df()
# openai_key = api_keys.loc[api_keys["api"] == "openai", "key"].iloc[0]
# openai_service = OpenAIService()
# result = openai_service.send(api_key=openai_key, message="Hello, this is a test message to check if the OpenAIService is working correctly.")
if __name__ == "__main__":
    # survey_simulation_test()
    # run_neutral_calibrated_persona_ablation_experiment(respondent_sample_n=30, temperature=0.0)
    run_neutral_calibration_sweep_full_persona(respondent_sample_n=30, random_state=1, calibration_levels=['baseline','soft','strong'], temperature=0.0, save_outputs=True)
    # plot_ordinal_boxplot_from_saved_results(
    # results_csv_path="data/output/survey_simulation_results_20260301_210726.csv",
    # output_png_path=None,
    # whis=(5, 95),
    # figsize=(12, 6))

    # evaluate_non_random_signal_from_saved_results(
    # results_csv_path="data/output/survey_simulation_results_20260301_210726.csv",
    # output_dir=None,
    # n_baseline_sims=5000,
    # n_permutations=5000,
    # n_bootstrap=2000,
    # random_state=42,
    # save_outputs=True,)
    # run_persona_ablation_stage2(respondent_sample_n=100, n_bootstrap=2000, save_outputs=True)
    # analyze_stage2_diagnostics_from_saved_results(detail_csv_path="data/output/survey_simulation_stage2_ablation_detail_20260301_224713.csv")
    
    # #Compare ordinal vs exact-match (global)
    # m = pd.read_csv("data/output/survey_simulation_stage2_per_question_metrics_20260301_234411.csv")
    # print(m.groupby("condition")[["mean_ordinal_accuracy_score", "exact_match_rate"]].mean())
    
    
    # # Test midpoint-bias hypothesis
    # dist = pd.read_csv("data/output/survey_simulation_stage2_answer_distribution_20260301_234411.csv")
    # mid = dist[dist["agent_answer"].isin(["D"])].groupby("condition")["proportion"].sum()
    # near_mid = dist[dist["agent_answer"].isin(["C","D","E"])].groupby("condition")["proportion"].sum()
    # print("D share:", mid); print("CDE share:", near_mid)