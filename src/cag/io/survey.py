"""
Loader for loading survey data for the Climate-Action-GABM application.
"""
# Metadata
__author__ = ["Ajaykumar Manivannan <ashwamanivannan@gmail.com>", "Andy Turner <agdturner@gmail.com>"]
__version__ = "0.7.0"
__copyright__ = "Copyright (c) 2026 Climate-Action-GABM contributors, University of Leeds"

# Standard library imports
import logging
from pathlib import Path
# Data handling
import pandas as pd

def load(file_path: str | Path, required_columns: list[str] = None) -> 'pd.DataFrame | None':
    """
    Load survey data from a CSV file, validate columns, and clean data.

    Pars:
        file_path (str | Path): Path to the CSV file containing survey data.
        required_columns (list[str]): List of columns required for processing.

    Returns:
        pd.DataFrame | None: Cleaned DataFrame, or None if loading fails.
    """
    file_path = Path(file_path)
    if not file_path.exists():
        logging.error(f"Survey data file not found: {file_path}")
        return None
    # If required_columns is empty
    if not required_columns:
        required_columns = [
            'ID',
            'age', # Used to determine year of birth
            'male_dummy', # Used to determine gender 0 = female, 1 = male
            'tprofile_GOR', # Used to determine region
            "profile_education_level", # Used to determine education level
            'tprofile_gross_household', # Used to determine income level
            'ethnicity_R', # Used to determine ethnicity
            'parent_dummy', # Used to determine family status
            'Vote2019R', # Used to determine UK General Election 2019 vote
            'pastvote_EURef', # Used to determine Brexit referendum vote
            'Political_Left_Right', # Used to determine political views
            'Selftransc_Val',
            'Selfenh_Values',
            'Openness',
            'ConformTrad',
            'SDO',
            'EDO',
            'RWA',
            'page5posttreatment6_1',
            'page5posttreatment6_4',
            'page5posttreatment6_5',
            'page5posttreatment6_7',
            'page5posttreatment6_9',
            'page5posttreatment6_11',
            'ProClimatePolSupp'
        ]

    # Read the CSV file into a Pandas DataFrame
    df = None
    try:
        df = pd.read_csv(file_path)
    except Exception as e:
        logging.error(f"Error reading survey data file '{file_path}': {e}")
        return None
    # Validate that required columns are present
    missing_cols = [col for col in required_columns if col not in df.columns]
    if missing_cols:
        logging.error(f"Missing required columns in survey data: {missing_cols}")
        return None
    # Select only the required columns for further processing
    df2 = df[required_columns]
    del df  # Free memory
    # Check for NaN values in the selected columns and log counts
    nan_counts = df2.isna().sum().sort_values(ascending=False)
    nan_report = nan_counts[nan_counts > 0]
    if not nan_report.empty:
        logging.info(f"Columns with NaN counts (before filtering):\n{nan_report}")
        max_nan_col = nan_counts.idxmax()
        logging.info(f"Column with most NaNs: {max_nan_col} ({nan_counts[max_nan_col]} NaNs)")
    else:
        logging.info("No NaNs found in selected columns.")
    # Drop rows with NaN values in any of the required columns
    df3 = df2.dropna(subset=df2.columns.values)
    del df2  # Free memory
    try:
        df3['ID'] = df3['ID'].astype(int)
    except Exception as e:
        logging.warning(f"Could not convert 'ID' column to int: {e}")
    # Filter out rows with unmapped attribute values (would crash on map lookup).
    # Education 19="Don't know", 20="Prefer not to say" → no SurveyEducationMap entry.
    # Ethnicity 6="Other" (codebook) → no SurveyEthnicityMap entry.
    # pastvote_EURef 4="Can't remember" → no BrexitVoteID entry.
    # Political_Left_Right: all values 1-8 are mapped (incl. 8="Don't know").
    # Education 18="Other technical…" IS mapped; ethnicity 5="Refused" IS mapped.
    try:
        df4 = df3[
            (df3['profile_education_level'] <= 18) &
            (df3['ethnicity_R'] <= 5) &
            (df3['pastvote_EURef'] < 4)
        ]
    except Exception as e:
        logging.warning(f"Error filtering survey data rows: {e}")
    del df3  # Free memory
    # Log the number of rows remaining after filtering
    logging.info(f"{len(df4)} rows after filtering.")
    return df4 if not df4.empty else None

def get_narrative(score, attribute_name):
    """
    Converts a numerical score into a first-person narrative description 
    based on the attribute.
    Args:
        score (float):
            The numerical score to convert.
        attribute_name (str):
            The name of the attribute for which the score is given.
    Returns:
        str: A narrative description corresponding to the score and attribute.
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