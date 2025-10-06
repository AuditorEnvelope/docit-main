# llm_provider.py
import os
import google.generativeai as genai
from dotenv import load_dotenv
load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
genai.configure(api_key=GEMINI_API_KEY)
MODEL = "gemini-1.5-pro"

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

def generate_doc_for_file(filename, code):
    prompt = make_prompt(filename, code)
    model = genai.GenerativeModel(MODEL)
    resp = model.generate_content(prompt)
    # response may be .text or nested
    text = getattr(resp, "text", None) or str(resp)
    return text