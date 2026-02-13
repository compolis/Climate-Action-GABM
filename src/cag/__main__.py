#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
This is the entry point for running the Climate-Action-GABM application.
To run, use the command:
    python3 -m cag
"""
# Metadata
__author__ = ["Andy Turner <agdturner@gmail.com>"]
__version__ = "0.1.0"
__copyright__ = "Copyright (c) 2026 Climate-Action-GABM contributors, University of Leeds"

# Standard library imports
import re
import sys
import logging
from pathlib import Path

def check_model_in_txt(models_txt_path, model_name):
    """
    Check if the specified model name exists in the models TXT file.
    Args:
        models_txt_path (Path): Path to the models TXT file.
        model_name (str): The model name to check.
    Returns:
        bool: True if the model is found or file does not exist, False otherwise.
    """
    if not models_txt_path.exists():
        logging.warning(f"Model list file not found: {models_txt_path}")
        return True  # Allow if no list exists
    with models_txt_path.open("r", encoding="utf-8") as f:
        content = f.read()
    # Look for exact model name in the file
    if re.search(rf"Model ID: (?:models/)?{re.escape(model_name)}\\b", content):
        return True
    logging.warning(f"Model '{model_name}' not found in {models_txt_path}. Please check available models.")
    return False

def main():
    """
    Main function for Climate-Action-GABM.
    """
    logging.info("Running cag...")
    # Get the api keys
    from gabm.io.read_data import read_api_keys
    # Read API keys from the default location
    api_keys = read_api_keys(file_path='data/api_key.csv')
    # Print the API keys
    logging.info(f"API Keys: {api_keys}")
    
    if not api_keys:
        logging.error("No API keys found. Exiting.")
        return

if __name__ == "__main__":
    """
    Entry point for the script. Calls the main function.
    """
    # Set up logging to file and console
    log_dir = Path("data/logs")
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / "run_main.log"
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[
            logging.FileHandler(log_file, mode="w"),
            logging.StreamHandler(sys.stdout)
        ]
    )
    main()
    