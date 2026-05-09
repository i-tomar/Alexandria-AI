import os

try:
    import google.generativeai as genai
except ImportError:
    genai = None


def _get_api_key() -> str | None:
    return os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")


def gemini_available() -> bool:
    return genai is not None and bool(_get_api_key())


def _configure_model():
    api_key = _get_api_key()
    if not genai or not api_key:
        return None
    genai.configure(api_key=api_key)
    return genai.GenerativeModel("gemini-1.5-flash")


def generate_text(prompt: str, *, temperature: float = 0.2, max_output_tokens: int = 512) -> str | None:
    model = _configure_model()
    if model is None:
        return None
    response = model.generate_content(
        prompt,
        generation_config={
            "temperature": temperature,
            "max_output_tokens": max_output_tokens,
        },
    )
    text = getattr(response, "text", None)
    if text:
        return text.strip()
    return None