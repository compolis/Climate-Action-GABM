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

Notes:
- API keys are loaded from `data/api_key.csv`.
- Survey question definitions are imported from `survey_dict`.
"""
# Metadata
__author__ = ["Ajaykumar Manivannan <ashwamanivannan@gmail.com>"]
__version__ = "0.1.0"
__copyright__ = "Copyright (c) 2026 GABM contributors, University of Leeds"

# Standard library imports
from collections import defaultdict
from pathlib import Path

import pandas as pd
from google import genai
from google.genai import types

import networkx as nx

PROJECT_ROOT = Path(__file__).resolve().parents[2] if "__file__" in globals() else Path.cwd()
DATA_DIR = PROJECT_ROOT / "data"

_API_KEYS_DF = None
_GEMINI_CLIENT = None


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
            'page5posttreatment6_1','page5posttreatment6_4','page5posttreatment6_5','page5posttreatment6_7',\
                'page5posttreatment6_9','page5posttreatment6_11','ProClimatePolSupp']


        survey_data= survey_data[col_list]
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
    

def format_persona_from_row(row):
    """
    Takes a dataframe row (dict) and formats it into the specific 
    persona string structure requested.
    """
    return (f"Demographically, I am a {row['age']}-year-old {row['male_dummy']} living in the {row['tprofile_GOR']}, United Kingdom. My ethnic background is {row['ethnicity_R']}, and I hold a {row['profile_education_level']}. Financially, my gross household income falls into the {row['tprofile_gross_household']} bracket. Regarding my family status, I {row['parent_dummy']} a parent. Politically, I position myself on the {row['Political_Left_Right']} of the spectrum. In the 2019 General Election, I cast my vote for the {row['Vote2019R']}. Looking back at the EU Referendum, {row['pastvote_EURef']}.")
    

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
    'Political_Left_Right']
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
            # For 'age', we can directly use the value without conversion
            if x=='age':
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
        genai_client = get_gemini_client()
    except Exception as e:
        return f"Error loading API key: {e}"
    
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
            response = genai_client.models.generate_content(
                model=model_name if model_name else "gemini-2.0-flash",
                contents=prompt,
                config=config
            )
            raw_content = response.text

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
        genai_client = get_gemini_client()
    except Exception as e:
        return f"Error loading API key: {e}"

    try:
        if provider.lower() != "gemini":
            return "Error: Unknown Provider"

        config = types.GenerateContentConfig(
            temperature=0.7,
            max_output_tokens=140,
            system_instruction=system_instruction,
        )

        response = genai_client.models.generate_content(
            model=model_name if model_name else "gemini-2.0-flash",
            contents=prompt,
            config=config,
        )

        return response.text.strip()

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



def run_simulation():
    file_path = DATA_DIR / "yougov_survey_data" / "YouGovProcessedData.csv"
    survey_data = load_survey_data(file_path)
    survey_data = survey_data.head(10)
    all_persona_texts = create_persona_text_for_people_agent(survey_data)
    influencer_personas = create_persona_text_for_influencer_agent()
    G_people_agent = create_networkx_graph_between_people_agents(all_persona_texts)
    create_networkx_graph_between_people_and_influencer_agents(G_people_agent, influencer_personas)
    memory_store = AgentMemoryStore(max_turns=8)

    try:
        from survey_dict import SURVEY_QUESTIONS
    except ImportError:
        from survey_dict import SURVEY_QUESTIONS

    for question_data in SURVEY_QUESTIONS:
        question_id = question_data.get('id')
        print(f"\n{'='*70}")
        print(f"QUESTION: {question_id} - {question_data['text'][:60]}...")
        print(f"{'='*70}")

        question_results = {}

        for n_rounds in range(1, 7):
            print(f"\n--- ROUND {n_rounds} ---")
            question_results[n_rounds] = {}

            for influencer_name, influencer_persona in influencer_personas.items():
                print(f"\nExposing agents to: {influencer_name}")

                topic = strip_after_colon(question_data["text"])
                influencer_message = draft_influencer_persuasive_message(
                    influencer_name,
                    influencer_persona,
                    topic,
                    provider="gemini",
                    model_name=None
                )
                print(f"Message: {influencer_message[:80]}...")

                influencer_agent_answers = {}
                for people_node, persona_description in all_persona_texts.items():
                    agent_answer = ask_agent_survey_question(
                        persona_description=persona_description,
                        question_data=question_data,
                        provider='gemini',
                        agent_id=people_node,
                        influencer_message=influencer_message,
                        memory_store=memory_store,
                        question_id=question_id
                    )

                    influencer_agent_answers[people_node] = agent_answer

                question_results[n_rounds][influencer_name] = influencer_agent_answers

                answer_counts = {}
                for ans in influencer_agent_answers.values():
                    answer_counts[ans] = answer_counts.get(ans, 0) + 1
                print(f"Answers from all agents: {answer_counts}")

        print(f"\n{'='*70}")
        print(f"Generating visualization for {question_id}...")
        print(f"{'='*70}")
        fig = plot_question_results(question_results, question_id)
        fig.savefig(f"question_{question_id}_results.png", dpi=150, bbox_inches='tight')
        print(f"Saved plot to: question_{question_id}_results.png")

        break


if __name__ == "__main__":
    run_simulation()
        