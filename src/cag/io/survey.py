"""
Loader for loading survey data for the Climate-Action-GABM application.
"""
# Metadata
__author__ = ["Ajaykumar Manivannan <ashwamanivannan@gmail.com>", "Andy Turner <agdturner@gmail.com>"]
__version__ = "0.1.0"
__copyright__ = "Copyright (c) 2026 Climate-Action-GABM contributors, University of Leeds"

# Standard library imports
import logging
from pathlib import Path
# Data handling
import pandas as pd

def load(file_path: str | Path, required_columns: list[str]) -> 'pd.DataFrame | None':
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
    # Filter out rows based on specified conditions (skipped or invalid responses)
    try:
        df4 = df3[
            (df3['profile_education_level'] < 18) &
            (df3['ethnicity_R'] < 5) &
            (df3['pastvote_EURef'] < 4) &
            (df3['Political_Left_Right'] < 8)
        ]
    except Exception as e:
        logging.warning(f"Error filtering survey data rows: {e}")
    del df3  # Free memory
    # Log the number of rows remaining after filtering
    logging.info(f"{len(df4)} rows after filtering.")
    return df4 if not df4.empty else None
