"""Multi-provider LLM rotation with rich logging.

Ported from the legacy src/utilities/llm_provider_v2 implementation so we
retain the same provider rotation behaviour and console visibility.
"""
from __future__ import annotations

import asyncio
import os
from typing import Dict, List, Optional

import google.generativeai as genai
from groq import AsyncGroq
from openai import AsyncOpenAI
from app.services.llm.key_provider import get_llm_api_key

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

    async def generate(self, prompt: str) -> Optional[str]:
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

    async def generate(self, prompt: str) -> Optional[str]:
        if not self.is_healthy():
            return None
        try:
            model = genai.GenerativeModel(self.model_name)
            resp = await model.generate_content_async(prompt)
            result = getattr(resp, "text", None) or str(resp)
            if result and "quota" not in result.lower():
                return result
        except Exception as primary_error:
            if "quota" in str(primary_error).lower():
                print("⚠️ Gemini quota exceeded, trying fallback model")
                try:
                    model = genai.GenerativeModel(self.fallback_model)
                    resp = await model.generate_content_async(prompt)
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
            self.client = AsyncGroq(api_key=api_key)
            self.model_name = "llama-3.3-70b-versatile"

    async def generate(self, prompt: str) -> Optional[str]:
        if not self.is_healthy():
            return None
        try:
            response = await self.client.chat.completions.create(
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
            self.client = AsyncOpenAI(
                api_key=api_key,
                base_url="https://api.deepseek.com/v1",
            )
            self.model_name = "deepseek-chat"

    async def generate(self, prompt: str) -> Optional[str]:
        if not self.is_healthy():
            return None
        try:
            response = await self.client.chat.completions.create(
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
        self.is_initialized = False

    async def _setup(self) -> None:
        # Get the API key from the centralized provider
        api_key = get_llm_api_key()
        
        # If we have an API key, try to initialize providers with it
        if api_key:
            # Try to initialize all providers with the same key
            # They'll validate if the key works for their service
            providers = [
                (GeminiProvider, "Gemini"),
                (GroqProvider, "Groq"),
                (DeepSeekProvider, "DeepSeek")
            ]
            
            for provider_class, name in providers:
                try:
                    provider = provider_class(api_key)
                    if provider.is_available:
                        self.providers.append(provider)
                        print(f"✅ {name} provider initialized")
                except Exception as e:
                    print(f"⚠️  Failed to initialize {name} provider: {str(e)}")
        
        # Fall back to environment variables if no providers were initialized
        if not self.providers:
            print("⚠️  No valid providers found with LLM_API_KEY, checking individual provider keys...")
            gemini_key = os.getenv("GEMINI_API_KEY")
            groq_key = os.getenv("GROQ_API_KEY")
            deepseek_key = os.getenv("DEEPSEEK_API_KEY")

            if gemini_key:
                self.providers.append(GeminiProvider(gemini_key))
                print("✅ Gemini provider initialized (legacy key)")
            if groq_key:
                self.providers.append(GroqProvider(groq_key))
                print("✅ Groq provider initialized (legacy key)")
            if deepseek_key:
                self.providers.append(DeepSeekProvider(deepseek_key))
                print("✅ DeepSeek provider initialized (legacy key)")

        print(f"🚀 Initialized {len(self.providers)} LLM providers")
        if not self.providers:
            print("🚨 No LLM providers available – configure at least one API key.")
        self.is_initialized = True

    def _healthy_providers(self) -> List[LLMProvider]:
        return [p for p in self.providers if p.is_healthy()]

    async def get_next_provider(self) -> Optional[LLMProvider]:
        healthy_providers = self._healthy_providers()
        if not healthy_providers:
            print("❌ No healthy providers available")
            return None
        
        provider = healthy_providers[self.current_index % len(healthy_providers)]
        self.current_index = (self.current_index + 1) % len(healthy_providers)
        return provider

    async def generate_with_rotation(self, prompt: str, max_attempts: int = 3) -> Optional[str]:
        """Generate content using async rotation across providers."""
        if not self.is_initialized:
            await self._setup()

        attempts = 0
        while attempts < max_attempts:
            provider = await self.get_next_provider()
            if not provider:
                print("❌ No healthy providers available to handle the request.")
                break

            print(f"🔄 Trying {provider.name} (attempt {attempts + 1})")
            try:
                result = await provider.generate(prompt)
                if result:
                    print(f"✅ Success with {provider.name}")
                    return result
            except Exception as e:
                provider.record_error(e)

            attempts += 1
            if attempts < max_attempts:
                print("⏳ Waiting 2 seconds before retry...")
                await asyncio.sleep(2)

        print("❌ All providers failed after multiple attempts")
        return None

    async def get_status(self) -> Dict[str, object]:
        healthy_providers = self._healthy_providers()
        return {
            "total_providers": len(self.providers),
            "healthy_providers": len(healthy_providers),
            "providers": [
                {
                    "name": p.name,
                    "available": p.is_available,
                    "healthy": p.is_healthy(),
                    "error_count": p.error_count,
                    "last_error": p.last_error,
                }
                for p in self.providers
            ],
        }


_rotator: Optional[LLMRotator] = None


async def get_rotator() -> LLMRotator:
    global _rotator
    if _rotator is None:
        _rotator = LLMRotator()
    # Ensure setup is complete before returning the rotator
    if not _rotator.is_initialized:
        await _rotator._setup()
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


async def generate_doc_for_file(filename: str, code: str) -> str:
    rotator = await get_rotator()
    prompt = make_prompt(filename, code)
    try:
        result = await rotator.generate_with_rotation(prompt)
        if result:
            return result
        return create_fallback_doc(filename, code, rotator.get_status())
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
