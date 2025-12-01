#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri Nov 28 19:31:14 2025

@author: ajaykumar
"""

import pandas as pd

#%%

df_surveys = pd.read_csv('data/YouGovProcessedData.csv') 

print('length: ', len(df_surveys))

#%%
col_list=['age','male_dummy',
  'tprofile_GOR',
  "profile_education_level",
  'tprofile_gross_household',
  'ethnicity_R',
  'parent_dummy',
  'Vote2019R',
  'pastvote_EURef',
  'new_socgrade',
  'Political_Left_Right',\
      'page5posttreatment6_4','page5posttreatment6_3','page5posttreatment6_8','page5posttreatment6_11',\
          'page5posttreatment6_9','page5posttreatment6_7']

"""
Remov 
education>17
ethnicity>4
Eu referendum>3

"""
    
    
df_fil= df_surveys[col_list]

df_fil = df_fil.dropna(subset=df_fil.columns.values)

df_fil=df_fil[(df_fil['profile_education_level']<18) & (df_fil['ethnicity_R']<5) & (df_fil['pastvote_EURef']<4) ]

    
    
"""
Age
Gender
Region in UK
Education level
Gross household income
Ethnicity
are you a Parent
Party voted for in 2019
EU referendum voter
Social grade/status
Political leaning
"""

"Age: , Gender: , Home region in United Kingdom: , Education level: , \
Gross household income range: ,Ethnicity: , Are you a parent: , Party voted for in 2019: ,\
 EU referendum vote: , Social status: , political leaning: " 


#%%

from openai import OpenAI
import anthropic
import google.generativeai as genai

# ==============================================================================
# 1. CLIENT INITIALIZATION (Configure your keys here)
# ==============================================================================

# OPENAI
client_openai = OpenAI(api_key="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")

# DEEPSEEK (Uses OpenAI Client with DeepSeek Base URL)
client_deepseek = OpenAI(
    api_key="sk-aeefd6a06957471cb1f956d542f4bafb", 
    base_url="https://api.deepseek.com"
)

# LLAMA (Using Groq for fast inference, uses OpenAI Client structure)
# Alternatively, you can use TogetherAI or local Ollama here.
client_llama = OpenAI(
    api_key="YOUR_GROQ_KEY", 
    base_url="https://api.groq.com/openai/v1"
)

# CLAUDE (Anthropic)
client_claude = anthropic.Anthropic(api_key="YOUR_ANTHROPIC_KEY")

# GEMINI (Google)
genai.configure(api_key="AIzaSyAEdZHe-1ZKELNguASmB1qxwqMHb5uoxos")


# import json
# import os
# from openai import OpenAI

# # ------------------------------------------------------------------
# # CONFIGURATION
# # ------------------------------------------------------------------
# #client = OpenAI(api_key="YOUR_API_KEY_HERE") 
# client = OpenAI(api_key="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") 


# ------------------------------------------------------------------
# 1. HELPER: PERSONA FORMATTER
# ------------------------------------------------------------------
def format_persona_from_row(row):
    """
    Takes a dataframe row (dict) and formats it into the specific 
    persona string structure requested.
    """
    return (
        f"Age: {row['age']} , "
        f"Gender: {row['male_dummy']} , "
        f"Home region in United Kingdom: {row['tprofile_GOR']}, "
        f"Education level: {row['profile_education_level']}, "
        f"Gross household income range: {row['tprofile_gross_household']}, "
        f"Ethnicity: {row['ethnicity_R']}, " 
        f"Are you a parent?: {row['parent_dummy']} , "
        f"Party voted for in 2019: {row['Vote2019R']}, "
        f"EU referendum vote: {row['pastvote_EURef']}, "
        f"UK NRS social grade: {row['new_socgrade']}, "
        f"Political leaning: {row['Political_Left_Right']}"
    )


#%%

profile_dict = {
  "male_dummy" : {
    "1" : "Male",
    "0" : "Female"
  },
  "tprofile_GOR" : {
    '1':	'North East',
    '2':	'North West',
    '3':	'Yorkshire and the Humber',
    '4':	'East Midlands',
    '5':	'West Midlands',
    '6':	'East of England',
    '7':	'London',
    '8':	'South East',
    '9':	'South West',
    '10':	'Wales',
    '11':	'Scotland',
    '12':	'Northern Ireland',
    '13':	'Non UK'
  },
  "profile_education_level" : {
    '1'	:'No formal qualifications',
    '2':	'Youth training certificate/skillseekers',
    '3'	:'Recognised trade apprenticeship completed',
    '4'	:'Clerical and commercial',
    '5':	'City & Guilds certificate',
    '6':	'City & Guilds certificate - advanced',
    '7':	'ONC',
    '8'	:'CSE grades 2-5',
    '9'	:'CSE grade 1, GCE O level, GCSE, School Certificate',
    '10':	'Scottish Ordinary/ Lower Certificate',
    '11':	'GCE A level or Higher Certificate',
    '12':	'Scottish Higher Certificate',
    '13':	'Nursing qualification (e.g. SEN, SRN, SCM, RGN)',
    '14':	'Teaching qualification (not degree)',
    '15':	'University diploma',
    '16':	'University or CNAA first degree (e.g. BA, B.Sc, B.Ed)',
    '17':	'University or CNAA higher degree (e.g. M.Sc, Ph.D)',
    '18':	'Other technical, professional or higher qualification'
  },
  "tprofile_gross_household" : {
    '1'	:'under £5,000 per year',
    '2'	:'£5,000 to £9,999 per year',
    '3'	:'£10,000 to £14,999 per year',
    '4'	:'£15,000 to £19,999 per year',
    '5'	:'£20,000 to £24,999 per year',
    '6'	:'£25,000 to £29,999 per year',
    '7'	:'£30,000 to £34,999 per year',
    '8'	:'£35,000 to £39,999 per year',
    '9'	:'£40,000 to £44,999 per year',
    '10':	'£45,000 to £49,999 per year',
    '11':	'£50,000 to £59,999 per year',
    '12':	'£60,000 to £69,999 per year',
    '13':	'£70,000 to £99,999 per year',
    '14':	'£100,000 to £149,999 per year',
    '15':	'£150,000 and over'
  },
  "ethnicity_R" : {
    '1':	'White',
    '2':	'Asian',
    '3':	'Black',
    '4':	'Mixed'
  },
  "parent_dummy" : {
    "1" : "Yes",
    "0" : 'No'
  },
  "Vote2019R" : {
    '1'	:'Conservative Party',
    '2':	'Labour Party',
    '3'	:'Libieral Democrats Party',
    '4':	'Brexit',
    '5':	'Green',
    '6'	:'Other',
    '7'	:'Dont know / Didnt vote'
  },
  "pastvote_EURef" : {
    '1'	:'I voted to Remain',
    '2'	:'I voted to Leave',
    '3'	:'I did not vote',
  },
  "new_socgrade" : {
    "1" : "A, B, or C1",
    "2" : "C2, D, or E"
  },
  "Political_Left_Right" : {
    '1'	:'Very left-wing',
    '2'	:'Fairly left-wing',
    '3'	:'Slightly left-of-centre',
    '4'	:'Centre',
    '5'	:'Slightly right-of-centre',
    '6'	:'Fairly right-wing',
    '7'	:'Very right-wing',
    '8'	:'Don’t know'
  }
}


#%% sandbox

# p_list=['age','male_dummy',
#   'tprofile_GOR',
#   "profile_education_level",
#   'tprofile_gross_household',
#   'ethnicity_R',
#   'parent_dummy',
#   'Vote2019R',
#   'pastvote_EURef',
#   'new_socgrade',
#   'Political_Left_Right']
# id_profile_dict={}
# for index, row in df_surveys.iterrows(): 
    
#     for x in p_list:
#         if x=='age':
#             id_profile_dict[x]=row[x]
#         else:
#             id_profile_dict[x]=profile_dict[x][str(int(row[x]))]
    
    
#     print(format_persona_from_row(id_profile_dict))
#     break

#%%

# ------------------------------------------------------------------
# 3. DEFINE THE SURVEY QUESTIONS
# ------------------------------------------------------------------

SURVEY_QUESTIONS = [
    {
        "id": "Q1",
        'col_name': 'page5posttreatment6_4',
        "text": "Please say how much you support or oppose government policies that do the following: Ban new oil/gas/coal licenses.",\
        "options": {
            "A": 'Strongly oppose',
            "B":'Somewhat oppose',
            "C":'Slightly oppose',
            "D":'Neutral',
            "E":'Slightly support',
            "F":'Somewhat support',
            "G":'Strongly support'
        }
    },
    {
        "id": "Q2", 
        'col_name':'page5posttreatment6_3',
        "text": "Please say how much you support or oppose government policies that do the following: Invest in and expand UK- based oil and gas production",
        "options": {
            "A": 'Strongly oppose',
            "B":'Somewhat oppose',
            "C":'Slightly oppose',
            "D":'Neutral',
            "E":'Slightly support',
            "F":'Somewhat support',
            "G":'Strongly support'
        }
    },
    {
        "id": "Q3",
        'col_name': 'page5posttreatment6_8',
        "text": "Please say how much you support or oppose government policies that do the following: Remove environmental regulations on new housing developments",
        "options": {
            "A": 'Strongly oppose',
            "B":'Somewhat oppose',
            "C":'Slightly oppose',
            "D":'Neutral',
            "E":'Slightly support',
            "F":'Somewhat support',
            "G":'Strongly support'
        }
    },
    {
        "id": "Q4", 
        'col_name': 'page5posttreatment6_11',
        "text": "Please say how much you support or oppose government policies that do the following: Compensate people in other countries, who are impacted by climate change",
        "options": {
            "A": 'Strongly oppose',
            "B":'Somewhat oppose',
            "C":'Slightly oppose',
            "D":'Neutral',
            "E":'Slightly support',
            "F":'Somewhat support',
            "G":'Strongly support'
        }
    },
    {
        "id": "Q5",
        'col_name': 'page5posttreatment6_9',
        "text": "Please say how much you support or oppose government policies that do the following: Impose a carbon tax on fossil fuel sale and distribute the tax revenues to the public (i.e. carbon fee and dividend)",
        "options": {
            "A": 'Strongly oppose',
            "B":'Somewhat oppose',
            "C":'Slightly oppose',
            "D":'Neutral',
            "E":'Slightly support',
            "F":'Somewhat support',
            "G":'Strongly support'
        }
    },
    {
        "id": "Q6", 
        'col_name': 'page5posttreatment6_7',
        "text": "Please say how much you support or oppose government policies that do the following: Mandate that all new housing developments should have non-fossil fuel heating systems, roof-top solar panels, high-level of insulation",
        "options": {
            "A": 'Strongly oppose',
            "B":'Somewhat oppose',
            "C":'Slightly oppose',
            "D":'Neutral',
            "E":'Slightly support',
            "F":'Somewhat support',
            "G":'Strongly support'
        }
    }
]

#%%
# ------------------------------------------------------------------
# 4. CONDUCT SURVEY FUNCTION
# ------------------------------------------------------------------

# def ask_agent_survey_question(persona_description, question_data):
#     """
#     Prompts the LLM to answer a single survey question as a specific persona.
#     """
    
#     prompt = f"""
#     You are participating in a demographic survey.
    
#     YOUR PERSONA:
#     {persona_description}
    
#     INSTRUCTIONS:
#     1. Read the question below.
#     2. Select the option (A, B, C, D, E, F or G) that ALIGNS BEST with your persona's worldview.
#     3. You MUST output ONLY the letter of your choice. Do not explain.
    
#     QUESTION: {question_data['text']}
    
#     OPTIONS:
#     A) {question_data['options']['A']}
#     B) {question_data['options']['B']}
#     C) {question_data['options']['C']}
#     D) {question_data['options']['D']}
#     E) {question_data['options']['E']}
#     F) {question_data['options']['F']}
#     G) {question_data['options']['G']}
    
#     YOUR CHOICE (Letter Only):
#     """

#     try:
#         response = client.chat.completions.create(
#             model="gpt-4o-mini",#"gpt-5.1", #"gpt-4o-mini", 
#             messages=[
#                 {"role": "system", "content": "You are a survey respondent. You strictly follow persona instructions."},
#                 {"role": "user", "content": prompt}
#             ],
#             temperature=0.3
#         )
        
#         answer = response.choices[0].message.content.strip().upper()
#         if len(answer) > 1:
#             answer = answer[0]
            
#         return answer

#     except Exception as e:
#         return f"Error: {e}"

#%%
# ==============================================================================
# 2. THE MULTI-MODEL SURVEY FUNCTION
# ==============================================================================

def ask_agent_survey_question(persona_description, question_data, provider="openai", model_name=None):
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
            model = model_name if model_name else "gemini-2.0-flash"
            # Gemini defines system instruction at model init
            gemini_model = genai.GenerativeModel(
                model_name=model,
                system_instruction=system_instruction
            )
            response = gemini_model.generate_content(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=0.3,
                    max_output_tokens=5
                )
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
        
        return answer

    except Exception as e:
        return f"Error: {e}"
#%%
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

#%%
# ------------------------------------------------------------------
# 5. MAIN VALIDATION LOOP
# ------------------------------------------------------------------

p_list=['age','male_dummy',
  'tprofile_GOR',
  "profile_education_level",
  'tprofile_gross_household',
  'ethnicity_R',
  'parent_dummy',
  'Vote2019R',
  'pastvote_EURef',
  'new_socgrade',
  'Political_Left_Right']


options_dict={'1':	'A','2':	'B',
'3':	'C',
'4':	'D',
'5':	'E',
'6':	'F',
'7':	'G'}
# def run_validation():
# print(f"{'='*60}")
# print(f"PERSONA VALIDATION PROTOCOL (DATAFRAME MODE)")
# print(f"{'='*60}\n")
it=0
#######3
"""
Randomly sample from df
"""
df_sample=df_fil.sample(n=100, replace=True, random_state=1)


save_list=[]
# In a real scenario, this would be: for index, row in df.iterrows():
for index,row in df_fil.iterrows():
    
    # if row['age']>65:
    #     continue
    id_profile_dict={}
    for x in p_list:
        if x=='age':
            id_profile_dict[x]=row[x]
        else:
            id_profile_dict[x]=profile_dict[x][str(int(row[x]))]
    # 1. Generate the Persona String dynamically
    persona_text = format_persona_from_row(id_profile_dict)
    
    # print(f"Testing ID: {index}")
    # print(f"Persona: {persona_text}...") # Print first 100 chars
    # print(f"{'-'*40}")
    
    
    score = 0
    total = len(SURVEY_QUESTIONS)
    
    for q in SURVEY_QUESTIONS:
        # 1. Get Expected Answer (Ground Truth from dataframe)
        #expected = row['expected_answers'][q['id']]
        expected=row[q['col_name']]
        expected=options_dict[str(int(expected))]
        # 2. Ask Agent
        agent_answer = ask_agent_survey_question(persona_text, q,provider='openai')
        
        # # 3. Compare
        # match = (agent_answer == expected)
        # result_str = "MATCH ✅" if match else "MISMATCH ❌"
        # if match:
        #     score += 1
        
        # print(f"  Q{q['id']} ({expected} vs {agent_answer}) -> {result_str}")
    # --- NEW SCORING LOGIC START ---
        
        # Extract keys (A, B, C) from the question options
        option_keys = list(q['options'].keys())
        
        # Calculate the distance-based score (0.0 to 1.0)
        q_score = calculate_ordinal_score(agent_answer, expected, option_keys)
        
        # Add to total score
        score += q_score
        
        # Visual feedback
        #print(f"  Q{q['id']} ({expected} vs {agent_answer}) -> Score: {q_score:.2f}")
        
        # --- NEW SCORING LOGIC END ---
    accuracy = (score / total) * 100
    print(str(it)+' '+f"  > Validity Score: {accuracy:.1f}%\n")
    
    save_list.append([index,persona_text, accuracy])
    it+=1
    if it==100:
        break
print(f"{'='*60}\n")

# if __name__ == "__main__":
#     if client.api_key == "YOUR_API_KEY_HERE":
#         print("ERROR: Please insert your OpenAI API Key in the script.")
#     else:
#         run_validation()
        
#%%

y=[x[2] for x in save_list]

plt.figure()
plt.boxplot(y,whis=[5,95])
plt.show()
        
        
#%%

"""
To do:
    
Try:
    
Different models, advanced to simple.

Where is it less accurate?

Improve Persona description: Check Gemini

Compare output value with Average in the population group!

"""


#%%

import matplotlib.pyplot as plt
plt.figure()
plt.boxplot(df_sample['age'],whis=[5,95])
plt.show()
#%%
"""

Testing ID: 55
Persona: Age: 39.0 , Gender: Female , Home region in United Kingdom: London, Education level: University or CNAA higher degree (e.g. M.Sc, Ph.D), Gross household income range: £70,000 to £99,999 per year, Ethnicity: White, Are you a parent?: No , Party voted for in 2019: Labour Party, EU referendum vote: I voted to Remain, UK NRS social grade: A, B, or C1, Political leaning: Fairly left-wing...
----------------------------------------
  QQ1 (F vs G) -> Score: 0.83
  QQ2 (A vs A) -> Score: 1.00
  QQ3 (B vs A) -> Score: 0.83
  QQ4 (F vs G) -> Score: 0.83
  QQ5 (E vs G) -> Score: 0.67
  QQ6 (F vs G) -> Score: 0.83
  > Validity Score: 83.3%

Testing ID: 63
Persona: Age: 39.0 , Gender: Male , Home region in United Kingdom: East of England, Education level: GCE A level or Higher Certificate, Gross household income range: £45,000 to £49,999 per year, Ethnicity: White, Are you a parent?: Yes , Party voted for in 2019: Conservative Party, EU referendum vote: I did not vote, UK NRS social grade: A, B, or C1, Political leaning: Don’t know...
----------------------------------------
  QQ1 (F vs D) -> Score: 0.67
  QQ2 (D vs E) -> Score: 0.83
  QQ3 (B vs A) -> Score: 0.83
  QQ4 (D vs D) -> Score: 1.00
  QQ5 (G vs D) -> Score: 0.50
  QQ6 (F vs D) -> Score: 0.67
  > Validity Score: 75.0%

Testing ID: 79
Persona: Age: 38.0 , Gender: Male , Home region in United Kingdom: South East, Education level: No formal qualifications, Gross household income range: £5,000 to £9,999 per year, Ethnicity: Mixed, Are you a parent?: No , Party voted for in 2019: Libieral Democrats Party, EU referendum vote: I voted to Remain, UK NRS social grade: C2, D, or E, Political leaning: Fairly left-wing...
----------------------------------------
  QQ1 (G vs G) -> Score: 1.00
  QQ2 (A vs A) -> Score: 1.00
  QQ3 (A vs A) -> Score: 1.00
  QQ4 (D vs G) -> Score: 0.50
  QQ5 (F vs G) -> Score: 0.83
  QQ6 (F vs G) -> Score: 0.83
  > Validity Score: 86.1%

Testing ID: 129
Persona: Age: 33.0 , Gender: Female , Home region in United Kingdom: South East, Education level: University or CNAA first degree (e.g. BA, B.Sc, B.Ed), Gross household income range: £100,000 to £149,999 per year, Ethnicity: White, Are you a parent?: No , Party voted for in 2019: Labour Party, EU referendum vote: I voted to Remain, UK NRS social grade: A, B, or C1, Political leaning: Slightly left-of-centre...
----------------------------------------
  QQ1 (G vs G) -> Score: 1.00
  QQ2 (B vs A) -> Score: 0.83
  QQ3 (A vs A) -> Score: 1.00
  QQ4 (C vs F) -> Score: 0.50
  QQ5 (E vs F) -> Score: 0.83
  QQ6 (G vs G) -> Score: 1.00
  > Validity Score: 86.1%

Testing ID: 131
Persona: Age: 40.0 , Gender: Female , Home region in United Kingdom: South East, Education level: CSE grade 1, GCE O level, GCSE, School Certificate, Gross household income range: £30,000 to £34,999 per year, Ethnicity: White, Are you a parent?: Yes , Party voted for in 2019: Labour Party, EU referendum vote: I voted to Remain, UK NRS social grade: C2, D, or E, Political leaning: Slightly left-of-centre...
----------------------------------------
  QQ1 (G vs F) -> Score: 0.83
  QQ2 (D vs B) -> Score: 0.67
  QQ3 (B vs A) -> Score: 0.83
  QQ4 (E vs F) -> Score: 0.83
  QQ5 (G vs F) -> Score: 0.83
  QQ6 (G vs F) -> Score: 0.83
  > Validity Score: 80.6%

Testing ID: 157
Persona: Age: 38.0 , Gender: Female , Home region in United Kingdom: London, Education level: University or CNAA first degree (e.g. BA, B.Sc, B.Ed), Gross household income range: £70,000 to £99,999 per year, Ethnicity: Black, Are you a parent?: No , Party voted for in 2019: Dont know / Didnt vote, EU referendum vote: I did not vote, UK NRS social grade: A, B, or C1, Political leaning: Fairly left-wing...
----------------------------------------
  QQ1 (D vs G) -> Score: 0.50
  QQ2 (B vs A) -> Score: 0.83
  QQ3 (C vs A) -> Score: 0.67
  QQ4 (D vs G) -> Score: 0.50
  QQ5 (E vs G) -> Score: 0.67
  QQ6 (D vs G) -> Score: 0.50
  > Validity Score: 61.1%

Testing ID: 165
Persona: Age: 37.0 , Gender: Female , Home region in United Kingdom: Wales, Education level: No formal qualifications, Gross household income range: £5,000 to £9,999 per year, Ethnicity: White, Are you a parent?: No , Party voted for in 2019: Labour Party, EU referendum vote: I voted to Remain, UK NRS social grade: C2, D, or E, Political leaning: Very left-wing...
----------------------------------------
  QQ1 (G vs G) -> Score: 1.00
  QQ2 (A vs A) -> Score: 1.00
  QQ3 (A vs A) -> Score: 1.00
  QQ4 (E vs G) -> Score: 0.67
  QQ5 (D vs G) -> Score: 0.50
  QQ6 (E vs G) -> Score: 0.67
  > Validity Score: 80.6%

Testing ID: 170
Persona: Age: 36.0 , Gender: Female , Home region in United Kingdom: South West, Education level: University or CNAA higher degree (e.g. M.Sc, Ph.D), Gross household income range: £5,000 to £9,999 per year, Ethnicity: White, Are you a parent?: No , Party voted for in 2019: Conservative Party, EU referendum vote: I did not vote, UK NRS social grade: C2, D, or E, Political leaning: Slightly left-of-centre...
----------------------------------------
  QQ1 (D vs E) -> Score: 0.83
  QQ2 (C vs C) -> Score: 1.00
  QQ3 (D vs A) -> Score: 0.50
  QQ4 (C vs E) -> Score: 0.67
  QQ5 (E vs E) -> Score: 1.00
  QQ6 (E vs F) -> Score: 0.83
  > Validity Score: 80.6%

Testing ID: 193
Persona: Age: 38.0 , Gender: Female , Home region in United Kingdom: Wales, Education level: University or CNAA first degree (e.g. BA, B.Sc, B.Ed), Gross household income range: £60,000 to £69,999 per year, Ethnicity: White, Are you a parent?: Yes , Party voted for in 2019: Conservative Party, EU referendum vote: I voted to Remain, UK NRS social grade: A, B, or C1, Political leaning: Slightly right-of-centre...
----------------------------------------
  QQ1 (E vs C) -> Score: 0.67
  QQ2 (C vs E) -> Score: 0.67
  QQ3 (B vs B) -> Score: 1.00
  QQ4 (D vs C) -> Score: 0.83
  QQ5 (D vs E) -> Score: 0.83
  QQ6 (E vs E) -> Score: 1.00
  > Validity Score: 83.3%

Testing ID: 197
Persona: Age: 34.0 , Gender: Male , Home region in United Kingdom: East Midlands, Education level: University or CNAA higher degree (e.g. M.Sc, Ph.D), Gross household income range: £40,000 to £44,999 per year, Ethnicity: White, Are you a parent?: No , Party voted for in 2019: Labour Party, EU referendum vote: I voted to Remain, UK NRS social grade: C2, D, or E, Political leaning: Centre...
----------------------------------------
  QQ1 (D vs F) -> Score: 0.67
  QQ2 (D vs B) -> Score: 0.67
  QQ3 (B vs A) -> Score: 0.83
  QQ4 (D vs F) -> Score: 0.67
  QQ5 (D vs F) -> Score: 0.67
  QQ6 (E vs G) -> Score: 0.67
  > Validity Score: 69.4%

============================================================
"""














   
