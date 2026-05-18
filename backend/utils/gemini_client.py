"""
AI client router supporting Gemini and Groq.
"""
import os
from . import groq_client

_client = None
_client_attempted = False


def reset_client():
    """Force re-initialisation of the client (call after .env changes)."""
    global _client, _client_attempted
    _client = None
    _client_attempted = False


def get_active_provider() -> str:
    return _get_provider()


def _get_provider() -> str:
    return os.getenv("AI_PROVIDER", "gemini").lower()


def _get_client():
    """Lazily initialise the AI client (singleton)."""
    global _client, _client_attempted
    
    provider = _get_provider()
    if provider == "groq":
        return groq_client._get_client()

    if _client_attempted:
        return _client
    _client_attempted = True
    try:
        from google import genai
        api_key = _get_api_key()
        if not api_key:
            print("DEBUG: No Gemini API key found in environment.")
            _client = None
            return None
        _client = genai.Client(api_key=api_key)
        print("DEBUG: Gemini client initialised successfully (google-genai SDK).")
    except ImportError:
        print("ERROR: `google-genai` package not installed. Run: pip install google-genai")
        _client = None
    except Exception as e:
        print(f"ERROR: Failed to initialise Gemini client: {e}")
        _client = None
    return _client


def _get_api_key() -> str | None:
    provider = _get_provider()
    if provider == "groq":
        return os.getenv("GROQ_API_KEY")
    return os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")


def heavy_ai_enabled() -> bool:
    value = os.getenv("ENABLE_GEMINI")
    if value is None:
        return False
    return value.strip().lower() in {"1", "true", "yes", "on"}


def gemini_available() -> bool:
    if not heavy_ai_enabled():
        return False
    
    provider = _get_provider()
    if provider == "groq":
        return groq_client.groq_available()

    if not _get_api_key():
        return False
    # Try importing the package without crashing
    try:
        from google import genai  # noqa: F401
        return True
    except ImportError:
        return False


def _get_model_name() -> str:
    provider = _get_provider()
    if provider == "groq":
        return groq_client._get_model_name()
    return os.getenv("GEMINI_MODEL", "gemini-2.5-flash")


def generate_text(prompt: str, *, temperature: float = 0.2, max_output_tokens: int = 512) -> str | None:
    provider = _get_provider()
    if provider == "groq":
        return groq_client.generate_text(prompt, temperature=temperature, max_output_tokens=max_output_tokens)

    print(f"DEBUG: Calling Gemini (prompt length: {len(prompt)} chars)...")
    client = _get_client()
    if client is None:
        print("DEBUG: Gemini client not available. Check API key and package installation.")
        return None
    try:
        from google.genai import types
        response = client.models.generate_content(
            model=_get_model_name(),
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=temperature,
                max_output_tokens=max_output_tokens,
            ),
        )
        text = response.text
        if text:
            print(f"DEBUG: Gemini success ({len(text)} chars).")
            return text.strip()
        print("DEBUG: Gemini returned empty text.")
        return None
    except Exception as e:
        error_msg = str(e)
        if "API_KEY_INVALID" in error_msg or "invalid api key" in error_msg.lower():
            print("CRITICAL: Gemini API Key is INVALID. Go to aistudio.google.com and get a fresh key.")
            return "ERROR: INVALID_API_KEY"
        if "quota" in error_msg.lower() or "429" in error_msg:
            print("WARNING: Gemini quota exceeded. Wait a minute or upgrade your plan.")
            return "ERROR: QUOTA_EXCEEDED"
        print(f"DEBUG: Gemini call failed: {e}")
        return None


def generate_text_stream(prompt: str, *, temperature: float = 0.2, max_output_tokens: int = 1024):
    """Generator that yields text tokens as Gemini/Groq produces them."""
    provider = _get_provider()
    if provider == "groq":
        yield from groq_client.generate_text_stream(prompt, temperature=temperature, max_output_tokens=max_output_tokens)
        return

    client = _get_client()
    if client is None:
        print("DEBUG: Gemini client not available for streaming.")
        return
    try:
        from google.genai import types
        for chunk in client.models.generate_content_stream(
            model=_get_model_name(),
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=temperature,
                max_output_tokens=max_output_tokens,
            ),
        ):
            if chunk.text:
                yield chunk.text
    except Exception as e:
        print(f"DEBUG: Gemini streaming failed: {e}")
        return
