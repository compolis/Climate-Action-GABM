"""
Thin wrapper for sending chat-style prompts to LLM providers.

Provides three functions:
    send_chat          — send a system + user message pair and get a response string
    load_api_key       — read an API key from CSV or environment variable
    parse_letter_response — extract a single A-G letter from free-text LLM output
"""

import csv
import os
import re

from pathlib import Path
_REPO_ROOT = Path(__file__).resolve().parents[3]
_DEFAULT_KEY_CSV = _REPO_ROOT / "data" / "api_key.csv"


# ---------------------------------------------------------------------------
# send_chat
# ---------------------------------------------------------------------------

def send_chat(system_prompt, user_prompt, api_key=None, model="gpt-4o-mini",
              provider="openai", temperature=0.7):
    """Send a chat completion request and return the assistant's text.

    Parameters
    ----------
    system_prompt : str
        The system message (persona / context).
    user_prompt : str
        The user message (task / question).
    api_key : str
        API key for the provider.
    model : str
        Model identifier (e.g. "gpt-4o-mini", "gemini-2.0-flash").
    provider : str
        "openai" or "genai".  Raises ValueError for anything else.
    temperature : float
        Sampling temperature (default 0.7).

    Returns
    -------
    str
        The assistant's text response.

    Raises
    ------
    ValueError
        If *provider* is not supported, or if *api_key* is missing/empty.
    RuntimeError
        If the API call fails.
    """
    if not api_key:
        api_key = load_api_key(provider)

    provider = provider.lower()

    if provider == "openai":
        return _send_openai(system_prompt, user_prompt, api_key, model, temperature)
    elif provider == "genai":
        return _send_genai(system_prompt, user_prompt, api_key, model, temperature)
    else:
        raise ValueError(
            f"Unsupported provider '{provider}'. Supported: 'openai', 'genai'."
        )


# ---------------------------------------------------------------------------
# Provider backends
# ---------------------------------------------------------------------------

def _send_openai(system_prompt, user_prompt, api_key, model, temperature):
    """Call the OpenAI chat completions API."""
    try:
        from openai import OpenAI
    except ImportError as exc:
        raise ImportError("The 'openai' package is required for provider='openai'.") from exc

    client = OpenAI(api_key=api_key)
    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=temperature,
        )
    except Exception as exc:
        raise RuntimeError(f"OpenAI API call failed: {exc}") from exc

    return response.choices[0].message.content


def _send_genai(system_prompt, user_prompt, api_key, model, temperature):
    """Call the Google GenAI (Gemini) API."""
    try:
        from google import genai
    except ImportError as exc:
        raise ImportError(
            "The 'google-genai' package is required for provider='genai'."
        ) from exc

    client = genai.Client(api_key=api_key)
    try:
        response = client.models.generate_content(
            model=model,
            contents=user_prompt,
            config=genai.types.GenerateContentConfig(
                system_instruction=system_prompt,
                temperature=temperature,
            ),
        )
    except Exception as exc:
        raise RuntimeError(f"Google GenAI API call failed: {exc}") from exc

    return response.text


# ---------------------------------------------------------------------------
# load_api_key
# ---------------------------------------------------------------------------

def load_api_key(provider, csv_path=_DEFAULT_KEY_CSV):
    """Load an API key from the project CSV or an environment variable.

    The CSV file has two columns (api, key) with no header row.  Each row
    maps a provider name to its key.

    If the CSV cannot be read the function falls back to environment
    variables: OPENAI_API_KEY for openai, GENAI_API_KEY for genai.

    Parameters
    ----------
    provider : str
        Provider name (e.g. "openai", "genai").
    csv_path : str
        Path to the API-key CSV file.

    Returns
    -------
    str
        The API key.

    Raises
    ------
    ValueError
        If no key is found from either source.
    """
    provider = provider.lower()


    # Try CSV first.
    try:
        with open(csv_path, newline="") as fh:
            reader = csv.reader(fh)
            for row in reader:
                if len(row) >= 2 and row[0].strip().lower() == provider:
                    return row[1].strip()
    except FileNotFoundError:
        pass

    # Fallback to environment variables.
    env_map = {
        "openai": "OPENAI_API_KEY",
        "genai": "GENAI_API_KEY",
    }
    env_var = env_map.get(provider)
    if env_var:
        key = os.environ.get(env_var)
        if key:
            return key

    raise ValueError(
        f"No API key found for provider '{provider}' "
        f"(checked '{csv_path}' and environment variables)."
    )


# ---------------------------------------------------------------------------
# parse_letter_response
# ---------------------------------------------------------------------------

_VALID_LETTERS = set("ABCDEFG")


def parse_letter_response(response):
    """Extract a single letter A-G from a free-text LLM response.

    Handles common patterns:
        "B"
        "B."  /  "B,"
        "My answer is B - Somewhat oppose"
        "E. I slightly support..."
        "G\\n\\nI strongly support..."

    Parameters
    ----------
    response : str
        Raw text returned by the LLM.

    Returns
    -------
    str
        A single uppercase letter A-G.

    Raises
    ------
    ValueError
        If no valid letter can be extracted.
    """
    text = response.strip()
    if not text:
        raise ValueError("Empty response — cannot extract a letter A-G.")

    # 1. Exact single letter (possibly with trailing punctuation / whitespace).
    if text[0].upper() in _VALID_LETTERS and (
        len(text) == 1 or text[1] in ".,;:)\n\r\t -"
    ):
        return text[0].upper()

    # 2. Patterns like "answer is X", "choice is X", "choose X".
    match = re.search(
        r"(?:answer|choice|choose|select|option)\s*(?:is\s*)?([A-Ga-g])\b",
        text,
        re.IGNORECASE,
    )
    if match:
        return match.group(1).upper()

    # 3. Standalone letter bounded by word boundaries.
    match = re.search(r"\b([A-G])\b", text)
    if match:
        letter = match.group(1).upper()
        if letter in _VALID_LETTERS:
            return letter

    raise ValueError(
        f"Could not extract a valid letter A-G from response: {text!r}"
    )


# ---------------------------------------------------------------------------
# Quick smoke-test when run directly.
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    provider = "openai"
    model = "gpt-4o-mini"
    try:
        api_key = load_api_key(provider)
        print(f"API key for {provider}: {api_key}")
    except ValueError as exc:
        print(exc)

    response = send_chat("You are a healthy eating promoter.", 
                         "I made a sandwich, ham and cheese, how is it?", 
                         api_key, 
                         model, provider)
    print(f"LLM response: {response}")


