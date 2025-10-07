# llm_provider.py
import os
import google.generativeai as genai
from dotenv import load_dotenv
load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
genai.configure(api_key=GEMINI_API_KEY)

# Use a safe default that exists in current google-generativeai releases.
# Allow override via env GEMINI_MODEL; fallback to flash if pro-latest is unavailable.
DEFAULT_MODEL = "gemini-1.5-pro-latest"
FALLBACK_MODEL = "gemini-1.5-flash-latest"
MODEL = os.getenv("GEMINI_MODEL", DEFAULT_MODEL)

MAX_CHARS = 12000

def make_prompt(filename, code):
    if len(code) > MAX_CHARS:
        code = code[:MAX_CHARS] + "\n\n# TRUNCATED\n"
    return f"""
You are DocAI. Output only MARKDOWN.
Filename: {filename}

Code: 
Produce:
- 1-2 line purpose
- For each function/class: signature + 1-line summary + params + return
- Example usage if possible
- Short TODOs/notes
Output a single markdown doc.
"""

def _try_generate(model_name, prompt):
    model = genai.GenerativeModel(model_name)
    resp = model.generate_content(prompt)
    return getattr(resp, "text", None) or str(resp)


def generate_doc_for_file(filename, code):
    """Generate markdown docs. Never raise; return a fallback doc on error."""
    prompt = make_prompt(filename, code)
    try:
        return _try_generate(MODEL, prompt)
    except Exception as e1:
        # Retry with a known fast fallback model
        try:
            return _try_generate(FALLBACK_MODEL, prompt)
        except Exception as e2:
            # Final fallback: emit a minimal doc so the pipeline continues
            return (
                f"# {filename}\n\n"
                f"_Automatic doc generation failed._\n\n"
                f"Error: {type(e2).__name__}: {e2}\n\n"
                f"## Code (truncated)\n\n````\n{code[:1000]}\n````\n"
            )