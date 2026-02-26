"""
Define the profile dictionary and survey questions.
"""
# Metadata
__author__ = ["Ajaykumar Manivannan <ashwamanivannan@gmail.com>"]
__version__ = "0.1.0"
__copyright__ = "Copyright (c) 2026 GABM contributors, University of Leeds"

# ------------------------------------------------------------------
# DEFINE THE PROFILE DICTIONARY
# ------------------------------------------------------------------


PROFILE_DICT = {
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
    "1" : "am",
    "0" : 'am not'
  },
  "Vote2019R" : {
    '1'	:'Conservative Party',
    '2':	'Labour Party',
    '3'	:'Liberal Democrats Party',
    '4':	'Brexit Party',
    '5':	'Green Party',
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

# ------------------------------------------------------------------
# DEFINE THE SURVEY QUESTIONS
# ------------------------------------------------------------------

SURVEY_QUESTIONS = [
    {
        "id": "Q1",
        'col_name': 'page5posttreatment6_1',
        "text": "Please say how much you support or oppose government policies that do the following: Accelerate the roll-out of renewable energy production, (e.g. more offshore and onshore wind parks)",\
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
        'col_name':'page5posttreatment6_4',
        "text": "Please say how much you support or oppose government policies that do the following: Ban new oil/gas/coal licenses",
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
        'col_name': 'page5posttreatment6_5',
        "text": "Please say how much you support or oppose government policies that do the following: Ban the sale of new petrol cars by no later than 2030",
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
    },    {
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
]

__all__ = ["PROFILE_DICT", "SURVEY_QUESTIONS"]