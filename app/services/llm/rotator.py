"""Multi-provider LLM rotation with rich logging.

Ported from the legacy src/utilities/llm_provider_v2 implementation so we
retain the same provider rotation behaviour and console visibility.
"""
from __future__ import annotations

import os
import time
from typing import Dict, List, Optional

import google.generativeai as genai
from groq import Groq
import openai

# No rate limiting needed (like old codebase)


class LLMProvider:
    """Base class for LLM providers (synchronous interface)."""

    max_errors = 3

    def __init__(self, name: str, api_key: str):
        self.name = name
        self.api_key = api_key
        self.is_available = bool(api_key)
        self.last_error: Optional[str] = None
        self.error_count = 0

    def generate(self, prompt: str) -> Optional[str]:
        raise NotImplementedError

    def is_healthy(self) -> bool:
        return self.is_available and self.error_count < self.max_errors

    def record_error(self, error: Exception) -> None:
        self.error_count += 1
        self.last_error = str(error)
        print(f"❌ {self.name} error #{self.error_count}: {error}")


class GeminiProvider(LLMProvider):
    def __init__(self, api_key: str):
        super().__init__("Gemini", api_key)
        if self.is_available:
            genai.configure(api_key=api_key)
            self.model_name = "models/gemini-2.5-flash"
            self.fallback_model = "models/gemini-2.0-flash"

    def generate(self, prompt: str) -> Optional[str]:
        if not self.is_healthy():
            return None
        try:
            model = genai.GenerativeModel(self.model_name)
            resp = model.generate_content(prompt)
            result = getattr(resp, "text", None) or str(resp)
            if result and "quota" not in result.lower():
                return result
        except Exception as primary_error:
            if "quota" in str(primary_error).lower():
                print("⚠️ Gemini quota exceeded, trying fallback model")
                try:
                    model = genai.GenerativeModel(self.fallback_model)
                    resp = model.generate_content(prompt)
                    return getattr(resp, "text", None) or str(resp)
                except Exception as fallback_error:
                    self.record_error(fallback_error)
                    return None
            self.record_error(primary_error)
            return None
        return None


class GroqProvider(LLMProvider):
    def __init__(self, api_key: str):
        super().__init__("Groq", api_key)
        if self.is_available:
            self.client = Groq(api_key=api_key)
            self.model_name = "llama-3.3-70b-versatile"

    def generate(self, prompt: str) -> Optional[str]:
        if not self.is_healthy():
            return None
        try:
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=4000,
                temperature=0.1,
            )
            return response.choices[0].message.content
        except Exception as error:
            self.record_error(error)
            return None


class DeepSeekProvider(LLMProvider):
    def __init__(self, api_key: str):
        super().__init__("DeepSeek", api_key)
        if self.is_available:
            self.client = openai.OpenAI(
                api_key=api_key,
                base_url="https://api.deepseek.com/v1",
            )
            self.model_name = "deepseek-chat"

    def generate(self, prompt: str) -> Optional[str]:
        if not self.is_healthy():
            return None
        try:
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=4000,
                temperature=0.1,
            )
            return response.choices[0].message.content
        except Exception as error:
            self.record_error(error)
            return None


class LLMRotator:
    """Round-robin provider rotation with verbose logging."""

    def __init__(self) -> None:
        self.providers: List[LLMProvider] = []
        self.current_index = 0
        # Don't use AsyncLimiter - old codebase doesn't use rate limiting (like old codebase)
        self._setup()

    def _setup(self) -> None:
        gemini_key = os.getenv("GEMINI_API_KEY")
        groq_key = os.getenv("GROQ_API_KEY")
        deepseek_key = os.getenv("DEEPSEEK_API_KEY")

        if gemini_key:
            self.providers.append(GeminiProvider(gemini_key))
            print("✅ Gemini provider initialized")
        if groq_key:
            self.providers.append(GroqProvider(groq_key))
            print("✅ Groq provider initialized")
        if deepseek_key:
            self.providers.append(DeepSeekProvider(deepseek_key))
            print("✅ DeepSeek provider initialized")

        print(f"🚀 Initialized {len(self.providers)} LLM providers")
        if not self.providers:
            raise RuntimeError("No LLM providers available – configure at least one API key.")

    def _healthy_providers(self) -> List[LLMProvider]:
        return [provider for provider in self.providers if provider.is_healthy()]

    def get_next_provider(self) -> Optional[LLMProvider]:
        healthy = self._healthy_providers()
        if not healthy:
            print("❌ No healthy providers available")
            return None
        provider = healthy[self.current_index % len(healthy)]
        self.current_index += 1
        return provider

    def generate_with_rotation(self, prompt: str, max_attempts: int = 3) -> Optional[str]:
        """Generate content using rotation across providers (like old codebase - no rate limiter)"""
        attempts = 0
        
        while attempts < max_attempts:
            provider = self.get_next_provider()
            if not provider:
                break
                
            print(f"🔄 Trying {provider.name} (attempt {attempts + 1})")
            result = provider.generate(prompt)
            
            if result:
                print(f"✅ Success with {provider.name}")
                return result
            
            attempts += 1
            if attempts < max_attempts:
                print("⏳ Waiting 2 seconds before retry...")
                time.sleep(2)
        
        print("❌ All providers failed")
        return None

    def get_status(self) -> Dict[str, object]:
        return {
            "total_providers": len(self.providers),
            "healthy_providers": len(self._healthy_providers()),
            "providers": [
                {
                    "name": provider.name,
                    "available": provider.is_available,
                    "healthy": provider.is_healthy(),
                    "error_count": provider.error_count,
                    "last_error": provider.last_error,
                }
                for provider in self.providers
            ],
        }


_rotator: Optional[LLMRotator] = None


def get_rotator() -> LLMRotator:
    global _rotator
    if _rotator is None:
        _rotator = LLMRotator()
    return _rotator

def create_fallback_doc(filename: str, code: str, status: Dict[str, object]) -> str:
    snippet = code[:1000]
    if len(code) > 1000:
        snippet += "..."
    provider_lines = [
        f"- {'✅' if info['healthy'] else '❌'} {info['name']} (errors: {info['error_count']})"
        + (f"\n  - Last error: {info['last_error']}" if info['last_error'] else "")
        for info in status.get("providers", [])
    ]
    provider_block = "\n".join(provider_lines) if provider_lines else "No providers available"
    return (
        f"# {filename}\n\n"
        "_Automatic documentation generation failed._\n\n"
        "## Provider Status\n"
        f"Total providers: {status.get('total_providers', 0)}\n"
        f"Healthy providers: {status.get('healthy_providers', 0)}\n"
        f"{provider_block}\n\n"
        "## Code (truncated)\n"
        f"```\n{snippet}\n```\n"
        "\n## Manual Documentation Needed\n"
        "Please add proper documentation manually.\n"
    )

def generate_doc_for_file(filename: str, code: str) -> str:
    prompt = make_prompt(filename, code)
    try:
        result = get_rotator().generate_with_rotation(prompt)
        if result:
            return result
        return create_fallback_doc(filename, code, get_rotator().get_status())
    except Exception as error:  # pragma: no cover - defensive
        print(f"❌ LLM generation failed: {error}")
        return create_fallback_doc(filename, code, {"error": str(error)})

def make_prompt(filename: str, code: str) -> str:
    language = filename.split(".")[-1] if "." in filename else "text"
    if len(code) > 12000:
        code = code[:12000] + "\n\n# TRUNCATED\n"
    return (
        "You are DocAI, an expert documentation generator. Generate comprehensive markdown documentation for the "
        "following code.\n\n"
        f"Filename: {filename}\n\n"
        "Code:\n"
        f"```{language}\n{code}\n```\n\n"
        "Please provide:\n"
        "1. **Purpose** – 1-2 line description of what this code does\n"
        "2. **Functions/Classes** – signature, summary, parameters, return value\n"
        "3. **Example Usage** – how to use the main functions\n"
        "4. **Notes/TODOs** – important notes or improvements\n"
        "Output only markdown."
    )
