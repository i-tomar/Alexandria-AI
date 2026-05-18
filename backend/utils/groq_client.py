"""
Groq AI client implementation.
"""
import os
from groq import Groq

_client = None

def _get_api_key() -> str | None:
    return os.getenv("GROQ_API_KEY")

def _get_model_name() -> str:
    return os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")

def _get_client():
    global _client
    if _client:
        return _client
    api_key = _get_api_key()
    if not api_key:
        return None
    try:
        _client = Groq(api_key=api_key)
        return _client
    except Exception as e:
        print(f"ERROR: Failed to initialise Groq client: {e}")
        return None

def groq_available() -> bool:
    return _get_api_key() is not None

def generate_text(prompt: str, *, temperature: float = 0.2, max_output_tokens: int = 512) -> str | None:
    client = _get_client()
    if not client:
        return None
    try:
        completion = client.chat.completions.create(
            model=_get_model_name(),
            messages=[{"role": "user", "content": prompt}],
            temperature=temperature,
            max_tokens=max_output_tokens,
        )
        return completion.choices[0].message.content
    except Exception as e:
        print(f"DEBUG: Groq call failed: {e}")
        return None

def generate_text_stream(prompt: str, *, temperature: float = 0.2, max_output_tokens: int = 1024):
    client = _get_client()
    if not client:
        return
    try:
        stream = client.chat.completions.create(
            model=_get_model_name(),
            messages=[{"role": "user", "content": prompt}],
            temperature=temperature,
            max_tokens=max_output_tokens,
            stream=True,
        )
        for chunk in stream:
            if chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content
    except Exception as e:
        print(f"DEBUG: Groq streaming failed: {e}")
        return
