import os

try:
    import google.generativeai as genai
except ImportError:  # pragma: no cover - optional at runtime
    genai = None


class LLMClient:
    """
    LLM client locked to Google Gemini 2.5 Flash.

    This project intentionally uses a single provider/model for all agents.
    """

    def __init__(self) -> None:
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            raise RuntimeError("GOOGLE_API_KEY environment variable is required for Google Gemini.")
        if genai is None:
            raise RuntimeError("google-generativeai is not installed. Add it to requirements.txt.")
        genai.configure(api_key=api_key)
        # Hard‑code default; still allow override via GOOGLE_MODEL if needed.
        self.model_name = os.getenv("GOOGLE_MODEL", "gemini-2.5-flash")

    def generate(self, system_prompt: str, user_prompt: str, max_tokens: int = 512) -> str:
        """
        Generate a completion using Google Gemini.
        """
        model = genai.GenerativeModel(self.model_name)
        # Gemini expects roles "user" and "model" only. We fold the system prompt
        # into the user content instead of using a separate "system" role.
        combined_prompt = f"{system_prompt}\n\nUser query:\n{user_prompt}"
        response = model.generate_content(
            combined_prompt,
            generation_config={"max_output_tokens": max_tokens, "temperature":0.1}
        )

        # Read from candidates/parts defensively to avoid `.text` errors.
        try:
            candidates = getattr(response, "candidates", None) or []
            for cand in candidates:
                content = getattr(cand, "content", None)
                if not content:
                    continue
                parts = getattr(content, "parts", []) or []
                texts = []
                for p in parts:
                    t = getattr(p, "text", None)
                    if t:
                        texts.append(t)
                if texts:
                    return "\n".join(texts)
        except Exception:
            # If anything goes wrong, fall through to a generic message.
            pass

        # Final safe fallback so the app does not crash.
        return "The model could not generate a response for this query."

