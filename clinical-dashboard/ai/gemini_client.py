import os
import re
import sys
import time
from dotenv import load_dotenv
from google import genai

# Load env variables
load_dotenv()

API_KEY = os.getenv("GEMINI_API_KEY")
if not API_KEY:
    raise RuntimeError("GEMINI_API_KEY missing")

# Create client (module-level, kept alive for the process — do not chain off a
# throwaway genai.Client(...), that self-closes and breaks the next call)
client = genai.Client(api_key=API_KEY)

MODEL_NAME = "models/gemini-3.5-flash-lite"  # FREE & FAST

# Transient statuses worth retrying: 429 rate limit, 500 internal, 503 overload
_TRANSIENT = {429, 500, 503}


def _status_code(err: Exception):
    """Best-effort HTTP status for a google-genai error."""
    code = getattr(err, "code", None)
    if isinstance(code, int):
        return code
    s = str(err)
    if "429" in s or "RESOURCE_EXHAUSTED" in s:
        return 429
    if "503" in s or "UNAVAILABLE" in s:
        return 503
    if "500" in s or "INTERNAL" in s:
        return 500
    return None


def _retry_delay_seconds(err: Exception):
    """Pull the server-suggested wait out of a 429 (e.g. 'retry in 14.87s')."""
    s = str(err)
    for pat in (r"retry in\s*([\d.]+)\s*s",
                r"retryDelay['\"]?\s*:?\s*['\"]?([\d.]+)\s*s"):
        m = re.search(pat, s, re.IGNORECASE)
        if m:
            try:
                return float(m.group(1))
            except ValueError:
                pass
    return None


def generate_with_retry(contents, config=None, model=None,
                        max_retries=3, base_wait=2.0, max_wait=30.0):
    """
    client.models.generate_content with backoff on transient errors (429/503/500).

    On a 429 it respects Google's own retryDelay (the 'retry in 14.87s' the free
    tier hands back); otherwise it backs off exponentially. Waits are capped at
    max_wait so a demo never freezes for minutes. Non-transient errors (bad key,
    bad request) are raised immediately — no point retrying those. Both agents
    call this: gemini_call() below, and the NLQ function-calling agent.
    """
    model = model or MODEL_NAME
    last_err = None
    for attempt in range(max_retries + 1):
        try:
            return client.models.generate_content(
                model=model, contents=contents, config=config
            )
        except Exception as e:
            last_err = e
            code = _status_code(e)
            if code not in _TRANSIENT or attempt == max_retries:
                raise
            suggested = _retry_delay_seconds(e)
            wait = suggested if suggested is not None else base_wait * (2 ** attempt)
            wait = min(wait, max_wait) + 0.5  # small buffer past the window
            print(f"[gemini] {code} transient, waiting {wait:.1f}s "
                  f"(attempt {attempt + 1}/{max_retries})", file=sys.stderr)
            time.sleep(wait)
    raise last_err  # unreachable, but keeps type-checkers happy


def gemini_call(prompt: str) -> str:
    """
    Calls Gemini using the google.genai SDK, with transient-error retry.
    Returns the text, or a '[Gemini Error] ...' sentinel on final failure
    (the review agent detects that sentinel and degrades gracefully).
    """
    try:
        response = generate_with_retry(prompt)
        return response.text
    except Exception as e:
        return f"[Gemini Error] {str(e)}"