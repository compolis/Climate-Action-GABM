"""
Thin wrapper for sending chat-style prompts to LLM providers.

Provides three functions:
    send_chat          — send a system + user message pair and get a response string
    load_api_key       — read an API key from CSV or environment variable
    parse_letter_response — extract a single A-G letter from free-text LLM output

Supported providers: ``openai``, ``genai``, ``anthropic``, ``local``.

The ``local`` provider routes calls to any OpenAI-compatible HTTP server
(mlx-lm, Ollama, vLLM, sglang, llama.cpp/llama-server, LM Studio, ...).
Server location and per-call quirks are configured via :func:`configure_local`
or environment variables — see that function's docstring for details.
"""

__version__ = "0.9.0"

import csv
import logging
import os
import re

from pathlib import Path
_REPO_ROOT = Path(__file__).resolve().parents[3]
_DEFAULT_KEY_CSV = _REPO_ROOT / "data" / "api_key.csv"


# ---------------------------------------------------------------------------
# Local-provider runtime config (settable by sim.py at startup)
# ---------------------------------------------------------------------------

_DEFAULT_LOCAL_BASE_URL = "http://localhost:8080/v1"
_DEFAULT_LOCAL_TIMEOUT_S = 600.0

_LOCAL_CONFIG: dict = {
    "base_url": None,    # None → resolved from env or default
    "extra_body": None,  # user-supplied dict merged on top of model registry entry
    "timeout_s": None,   # None → default
}


def configure_local(base_url=None, extra_body=None, timeout_s=None):
    """Set process-wide defaults for the ``local`` provider.

    Called once by ``sim.py`` at simulation start. Any value left as ``None``
    falls back to (in order): the matching ``CAG_LOCAL_*`` environment
    variable, then a built-in default.

    Parameters
    ----------
    base_url : str or None
        OpenAI-compatible endpoint, e.g. ``http://localhost:8080/v1``.
    extra_body : dict or None
        Extra request-body keys merged on top of the model registry entry.
        Use this to override sampling presets or pass server-specific knobs
        (e.g. ``{"chat_template_kwargs": {"enable_thinking": False}}``).
    timeout_s : float or None
        Per-call HTTP timeout in seconds. Local thinking calls can run for
        90+ s, so the default is much higher than the OpenAI client default.
    """
    if base_url is not None:
        _LOCAL_CONFIG["base_url"] = base_url
    if extra_body is not None:
        _LOCAL_CONFIG["extra_body"] = dict(extra_body)
    if timeout_s is not None:
        _LOCAL_CONFIG["timeout_s"] = float(timeout_s)


def _resolve_local_base_url():
    return (
        _LOCAL_CONFIG.get("base_url")
        or os.environ.get("CAG_LOCAL_BASE_URL")
        or _DEFAULT_LOCAL_BASE_URL
    )


def _resolve_local_timeout():
    cfg = _LOCAL_CONFIG.get("timeout_s")
    if cfg is not None:
        return cfg
    env = os.environ.get("CAG_LOCAL_TIMEOUT_S")
    if env:
        try:
            return float(env)
        except ValueError:
            pass
    return _DEFAULT_LOCAL_TIMEOUT_S


# ---------------------------------------------------------------------------
# Per-model defaults for local servers
# ---------------------------------------------------------------------------
#
# Substring-keyed (lowercase). First match wins. Each entry may set:
#   sampling_non_thinking : dict merged into request kwargs when thinking=False
#   sampling_thinking     : dict merged into request kwargs when thinking=True
#   extra_body            : dict merged into extra_body for *all* calls
#   thinking_extra_body   : callable(thinking_bool) -> extra_body dict
#   max_tokens_msg        : default max_tokens for non-thinking calls
#   max_tokens_thinking   : default max_tokens for thinking calls
#
# Unknown models fall through to bare defaults (no special handling). Users
# can always override via ``configure_local(extra_body=...)``.

_MODEL_REGISTRY = [
    # Qwen3 family — toggles `enable_thinking` via Jinja chat-template kwarg.
    {
        "match": "qwen3",
        "sampling_non_thinking": {"temperature": 0.7, "top_p": 0.8},
        "sampling_thinking":     {"temperature": 0.6, "top_p": 0.95},
        "thinking_extra_body":   lambda thk: {"chat_template_kwargs": {"enable_thinking": bool(thk)}},
        "max_tokens_msg":        2048,
        "max_tokens_thinking":   16384,
    },
    # DeepSeek-R1 distills always reason; no toggle exposed.
    {
        "match": "deepseek-r1",
        "sampling_non_thinking": {"temperature": 0.6, "top_p": 0.95},
        "sampling_thinking":     {"temperature": 0.6, "top_p": 0.95},
        "max_tokens_msg":        4096,
        "max_tokens_thinking":   16384,
    },
    # Llama 3.x family.
    {
        "match": "llama",
        "sampling_non_thinking": {"temperature": 0.7, "top_p": 0.9},
        "sampling_thinking":     {"temperature": 0.7, "top_p": 0.9},
        "max_tokens_msg":        2048,
        "max_tokens_thinking":   4096,
    },
    # Apertus.
    {
        "match": "apertus",
        "sampling_non_thinking": {"temperature": 0.7, "top_p": 0.9},
        "sampling_thinking":     {"temperature": 0.7, "top_p": 0.9},
        "max_tokens_msg":        2048,
        "max_tokens_thinking":   4096,
    },
    # Mistral / Mixtral.
    {
        "match": "mistral",
        "sampling_non_thinking": {"temperature": 0.7, "top_p": 0.9},
        "sampling_thinking":     {"temperature": 0.7, "top_p": 0.9},
        "max_tokens_msg":        2048,
        "max_tokens_thinking":   4096,
    },
]


def _resolve_model_profile(model):
    """Return the first matching entry from ``_MODEL_REGISTRY``, or {}."""
    if not model:
        return {}
    needle = model.lower()
    for entry in _MODEL_REGISTRY:
        if entry["match"] in needle:
            return entry
    return {}


# ---------------------------------------------------------------------------
# send_chat
# ---------------------------------------------------------------------------

def send_chat(system_prompt, user_prompt, api_key=None, model="gpt-5-mini",
              provider="openai", temperature=0.5, thinking=False):
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
        Model identifier (e.g. "gpt-5-mini", "gemini-2.0-flash").
    provider : str
        ``"openai"``, ``"genai"``, ``"anthropic"``, or ``"local"``. Raises
        ValueError for anything else. The ``local`` provider routes to any
        OpenAI-compatible HTTP server — see :func:`configure_local`.
    temperature : float
        Sampling temperature (default 0.5).
    thinking : bool
        Enable model thinking / reasoning when supported (default False).
        If a model does not support thinking, the call automatically falls
        back to a standard (non-thinking) request — no hardcoded model
        lists required.

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
        return _send_openai(system_prompt, user_prompt, api_key, model, temperature, thinking)
    elif provider == "genai":
        return _send_genai(system_prompt, user_prompt, api_key, model, temperature, thinking)
    elif provider == "anthropic":
        return _send_anthropic(system_prompt, user_prompt, api_key, model, temperature, thinking)
    elif provider == "local":
        return _send_local(system_prompt, user_prompt, model, temperature, thinking)
    else:
        raise ValueError(
            f"Unsupported provider '{provider}'. "
            f"Supported: 'openai', 'genai', 'anthropic', 'local'."
        )


# ---------------------------------------------------------------------------
# Generic resilient API call helper
# ---------------------------------------------------------------------------

_logger = logging.getLogger(__name__)

# Regex patterns for extracting the rejected parameter name from error messages.
# Each provider uses a different format, so we try them in order.
_PARAM_PATTERNS = [
    # OpenAI: "'temperature' does not support ..." or "'param': 'temperature'"
    re.compile(r"'param':\s*'(\w+)'"),
    re.compile(r"'(\w+)'\s+does not support"),
    # Anthropic: "thinking.adaptive.budget_tokens: ..." or "adaptive thinking is not supported"
    re.compile(r"^(\w+)[\.\[]", re.MULTILINE),
    re.compile(r"(\w+)\s+(?:thinking\s+)?is not supported"),    # GenAI: "... parameter 'temperature' ..." or "... field 'thinking_config' ..."
    re.compile(r"(?:parameter|field)\s+'(\w+)'"),]


# Cache of params known to be unsupported for a given (provider, model).
# Populated lazily on the first 400 from each model and consulted on every
# subsequent call so the offending param is stripped before the request is
# sent — saves a round-trip and stops the warning re-firing every call.
_KNOWN_UNSUPPORTED: dict[tuple[str, str], set[str]] = {}


def _extract_rejected_param(error_msg):
    """Try to extract the offending parameter name from a 400 error message.

    Returns the top-level kwarg name (e.g. "temperature", "thinking",
    "reasoning_effort") or *None* if the message cannot be parsed.
    """
    for pattern in _PARAM_PATTERNS:
        m = pattern.search(error_msg)
        if m:
            # Map sub-keys to their top-level kwarg.
            param = m.group(1).lower()
            if param in ("adaptive", "budget_tokens"):
                return "thinking"
            if param in ("thinking_config", "thinking_budget", "include_thoughts"):
                return "thinking_config"
            return param
    return None


def _resilient_call(api_fn, kwargs, provider_label, max_retries=3,
                    on_strip=None):
    """Call *api_fn* with *kwargs*, automatically stripping rejected params.

    On a 400 / invalid-request error the helper extracts the offending
    parameter name from the error message, removes it from *kwargs*, and
    retries — up to *max_retries* times.  Non-parameter errors (auth, rate
    limit, 500) raise immediately.

    Parameters
    ----------
    api_fn : callable
        The provider SDK method (e.g. ``client.chat.completions.create``).
    kwargs : dict
        Mutable dict of keyword arguments.  Modified in-place on retries.
    provider_label : str
        Used in error messages (e.g. "OpenAI", "Anthropic").
    max_retries : int
        Maximum number of params to strip before giving up.
    on_strip : callable or None
        Optional ``on_strip(kwargs, stripped_param)`` hook called after a
        param is removed.  Useful for coupled-parameter fixups (e.g.
        Anthropic: when "thinking" is stripped, re-add temperature).
    """
    last_exc = None
    cache_key = (provider_label, kwargs.get("model"))
    # Pre-emptively strip params already known to be unsupported for this
    # (provider, model). Silent: the warning fired on the first encounter.
    for cached_param in tuple(_KNOWN_UNSUPPORTED.get(cache_key, ())):
        if cached_param in kwargs:
            del kwargs[cached_param]
            if on_strip:
                on_strip(kwargs, cached_param)
    for _ in range(1 + max_retries):
        try:
            return api_fn(**kwargs)
        except Exception as exc:
            error_msg = str(exc)
            # Only retry on 400 / invalid-request style errors.
            if "400" not in error_msg and "invalid_request" not in error_msg:
                raise RuntimeError(
                    f"{provider_label} API call failed: {exc}"
                ) from exc

            param = _extract_rejected_param(error_msg)
            if param and param in kwargs:
                _logger.warning(
                    "%s: model does not support '%s', retrying without it",
                    provider_label, param,
                )
                del kwargs[param]
                _KNOWN_UNSUPPORTED.setdefault(cache_key, set()).add(param)
                if on_strip:
                    on_strip(kwargs, param)
                last_exc = exc
            else:
                raise RuntimeError(
                    f"{provider_label} API call failed: {exc}"
                ) from exc

    raise RuntimeError(
        f"{provider_label} API call failed after {max_retries} retries: "
        f"{last_exc}"
    ) from last_exc


# ---------------------------------------------------------------------------
# Provider backends
# ---------------------------------------------------------------------------

def _send_openai(system_prompt, user_prompt, api_key, model, temperature, thinking):
    """Call the OpenAI chat completions API."""
    try:
        from openai import OpenAI
    except ImportError as exc:
        raise ImportError("The 'openai' package is required for provider='openai'.") from exc

    client = OpenAI(api_key=api_key)
    kwargs = dict(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=temperature,
    )
    if thinking:
        kwargs["reasoning_effort"] = "medium"
    elif model.startswith(("gpt-5", "o1", "o3", "o4")):
        # Reasoning models default to medium effort, which adds 5-15s/call.
        # When extended thinking is off, force minimal effort for low latency.
        # If a future model rejects this kwarg, _resilient_call will strip it.
        kwargs["reasoning_effort"] = "minimal"

    response = _resilient_call(
        client.chat.completions.create, kwargs, "OpenAI",
    )
    return response.choices[0].message.content


def _send_genai(system_prompt, user_prompt, api_key, model, temperature, thinking):
    """Call the Google GenAI (Gemini) API."""
    try:
        from google import genai
    except ImportError as exc:
        raise ImportError(
            "The 'google-genai' package is required for provider='genai'."
        ) from exc

    client = genai.Client(api_key=api_key)
    config_kwargs = dict(
        system_instruction=system_prompt,
        temperature=temperature,
    )
    if not thinking:
        config_kwargs["thinking_config"] = genai.types.ThinkingConfig(
            include_thoughts=False,
        )

    def _call(**kw):
        cfg = genai.types.GenerateContentConfig(**kw)
        return client.models.generate_content(
            model=model, contents=user_prompt, config=cfg,
        )

    response = _resilient_call(_call, config_kwargs, "Google GenAI")
    return response.text


def _send_anthropic(system_prompt, user_prompt, api_key, model, temperature, thinking):
    """Call the Anthropic Messages API."""
    try:
        import anthropic
    except ImportError as exc:
        raise ImportError(
            "The 'anthropic' package is required for provider='anthropic'."
        ) from exc

    client = anthropic.Anthropic(api_key=api_key)
    kwargs = dict(
        model=model,
        max_tokens=256,
        system=system_prompt,
        messages=[{"role": "user", "content": user_prompt}],
    )
    if thinking:
        kwargs["max_tokens"] = 16000
        kwargs["thinking"] = {"type": "adaptive"}
    elif temperature is not None:
        kwargs["temperature"] = temperature

    def _on_strip(kw, stripped):
        """Coupled-param fixup: when thinking is stripped, restore defaults."""
        if stripped == "thinking":
            kw["max_tokens"] = 256
            if temperature is not None:
                kw["temperature"] = temperature

    response = _resilient_call(
        client.messages.create, kwargs, "Anthropic", on_strip=_on_strip,
    )

    # With thinking enabled, response may contain thinking blocks before the text.
    for block in response.content:
        if block.type == "text":
            return block.text
    return response.content[0].text


# ---------------------------------------------------------------------------
# Local OpenAI-compatible backend (mlx-lm, Ollama, vLLM, sglang, llama.cpp, ...)
# ---------------------------------------------------------------------------

_LOGGED_UNKNOWN_LOCAL_MODELS: set[str] = set()


def _merge_extra_body(*sources):
    """Shallow-merge dicts in order, later sources override earlier ones."""
    out: dict = {}
    for src in sources:
        if src:
            out.update(src)
    return out


def _send_local(system_prompt, user_prompt, model, temperature, thinking):
    """Send a chat completion to an OpenAI-compatible local server.

    Server location, request timeout, and per-call extras are read from the
    process-wide config set by :func:`configure_local` (with environment
    variable and built-in default fallbacks).

    Per-model defaults (sampling presets, ``enable_thinking`` for Qwen3,
    sensible ``max_tokens``) are applied from :data:`_MODEL_REGISTRY`.
    Unknown models fall through to bare defaults and trigger a one-time
    INFO log so the user can spot the gap.
    """
    try:
        from openai import OpenAI
    except ImportError as exc:
        raise ImportError(
            "The 'openai' package is required for provider='local' "
            "(it implements the OpenAI-compatible HTTP client)."
        ) from exc

    base_url = _resolve_local_base_url()
    timeout_s = _resolve_local_timeout()
    profile = _resolve_model_profile(model)

    if not profile and model and model not in _LOGGED_UNKNOWN_LOCAL_MODELS:
        _logger.info(
            "local: no MODEL_REGISTRY entry for %r — using bare defaults. "
            "Pass extra_body via configure_local() to tune sampling.",
            model,
        )
        _LOGGED_UNKNOWN_LOCAL_MODELS.add(model)

    client = OpenAI(base_url=base_url, api_key="not-needed", timeout=timeout_s)

    # Sampling: profile-supplied preset, else fall back to caller temperature.
    if thinking and profile.get("sampling_thinking"):
        sampling = dict(profile["sampling_thinking"])
    elif (not thinking) and profile.get("sampling_non_thinking"):
        sampling = dict(profile["sampling_non_thinking"])
    else:
        sampling = {"temperature": temperature}

    # Token cap: profile-supplied default, very generous on thinking calls.
    if thinking:
        max_tokens = profile.get("max_tokens_thinking", 16384)
    else:
        max_tokens = profile.get("max_tokens_msg", 2048)

    # Extra body: model-registry static + thinking-aware + user override.
    user_extra = _LOCAL_CONFIG.get("extra_body") or {}
    profile_extra_static = profile.get("extra_body") or {}
    profile_extra_thk = (
        profile["thinking_extra_body"](thinking)
        if profile.get("thinking_extra_body")
        else {}
    )
    extra_body = _merge_extra_body(profile_extra_static, profile_extra_thk, user_extra)

    def _do_call(use_thinking, tok_budget, samp):
        kwargs = dict(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            max_tokens=tok_budget,
            **samp,
        )
        # Re-derive extra_body so the retry can flip enable_thinking.
        if profile.get("thinking_extra_body"):
            local_extra = _merge_extra_body(
                profile_extra_static,
                profile["thinking_extra_body"](use_thinking),
                user_extra,
            )
        else:
            local_extra = extra_body
        if local_extra:
            kwargs["extra_body"] = local_extra
        try:
            resp = client.chat.completions.create(**kwargs)
        except Exception as exc:  # noqa: BLE001
            raise RuntimeError(f"Local server call failed: {exc}") from exc
        return (resp.choices[0].message.content or "")

    text = _do_call(thinking, max_tokens, sampling)

    # Thinking-mode truncation guard: when the model burns its budget on
    # reasoning and emits no answer, retry once with thinking disabled so
    # the simulation makes progress instead of failing the day.
    if thinking and not text.strip():
        _logger.warning(
            "local: thinking-mode call returned empty content "
            "(likely truncated by max_tokens=%d). Retrying without thinking.",
            max_tokens,
        )
        fallback_sampling = (
            dict(profile["sampling_non_thinking"])
            if profile.get("sampling_non_thinking")
            else {"temperature": temperature}
        )
        fallback_max = profile.get("max_tokens_msg", 2048)
        text = _do_call(False, fallback_max, fallback_sampling)

    text = re.sub(r"<think>.*?</think>\s*", "", text, flags=re.DOTALL)
    return text


def ping_local(base_url=None, timeout=5.0):
    """Check that the configured local LLM server is reachable.

    Performs a ``GET {base_url}/models`` request. Raises ``RuntimeError`` with
    a remediation message on failure. Returns the parsed JSON response on
    success.

    Call this at simulation start when ``provider="local"`` to fail fast
    instead of mid-run.
    """
    try:
        import requests
    except ImportError as exc:
        raise ImportError("The 'requests' package is required for ping_local().") from exc

    url = (base_url or _resolve_local_base_url()).rstrip("/") + "/models"
    try:
        r = requests.get(url, timeout=timeout)
        r.raise_for_status()
        return r.json()
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError(
            f"Local LLM server not reachable at {url}. Start a server "
            f"speaking the OpenAI Chat Completions protocol on this URL "
            f"(e.g. `mlx_lm.server --model <model> --port 8080`, "
            f"`ollama serve`, `vllm serve <model>`). "
            f"Override the URL via configure_local(base_url=...) or the "
            f"CAG_LOCAL_BASE_URL environment variable.\n"
            f"Underlying error: {exc}"
        ) from exc


# ---------------------------------------------------------------------------
# load_api_key
# ---------------------------------------------------------------------------

def load_api_key(provider, csv_path=_DEFAULT_KEY_CSV):
    """Load an API key from the project CSV or an environment variable.

    The CSV file has two columns (api, key) with no header row.  Each row
    maps a provider name to its key.

    If the CSV cannot be read the function falls back to environment
    variables: OPENAI_API_KEY for openai, GENAI_API_KEY for genai,
    ANTHROPIC_API_KEY for anthropic.

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

    # The local OpenAI-compatible servers (mlx-lm, Ollama, vLLM, ...) do not
    # require authentication. Return a sentinel so call sites do not need to
    # special-case the local provider when wiring api_key through.
    if provider == "local":
        return "not-needed"

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
        "anthropic": "ANTHROPIC_API_KEY",
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
    model = "gpt-5-mini"
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


