"""
LLM Provider Module

This module provides a unified interface for multiple LLM providers with rotation and fallback support.
"""

import asyncio
import os
import random
import time
from typing import List, Dict, Optional, Tuple, Any

# Import providers
import google.generativeai as genai
from groq import Groq
import openai
from aiolimiter import AsyncLimiter

# Define a module-level rate limiter for LLM calls
try:
    llm_rate_limiter = AsyncLimiter(50, 60)
except Exception:
    # Fallback no-op limiter if aiolimiter is not available
    class _NoopLimiter:
        async def __aenter__(self): return None
        async def __aexit__(self, *args): return False
    llm_rate_limiter = _NoopLimiter()

class LLMProvider:
    """Base class for LLM providers"""
    
    def __init__(self, name: str, api_key: str):
        self.name = name
        self.api_key = api_key
        self.is_available = bool(api_key)
        self.last_error = None
        self.error_count = 0
        self.total_requests = 0
        self.total_tokens = 0
        self.model_name = ""
        
    async def generate(self, prompt: str, **kwargs) -> str:
        """Generate text using the provider's API"""
        raise NotImplementedError("Subclasses must implement generate()")
        
    def get_metrics(self) -> Dict[str, Any]:
        """Get provider metrics"""
        return {
            "name": self.name,
            "is_available": self.is_available,
            "error_count": self.error_count,
            "last_error": str(self.last_error) if self.last_error else None,
            "total_requests": self.total_requests,
            "total_tokens": self.total_tokens,
            "model": self.model_name
        }


class GeminiProvider(LLMProvider):
    """Google Gemini provider"""
    
    def __init__(self, api_key: str):
        super().__init__("Gemini", api_key)
        if self.is_available:
            genai.configure(api_key=api_key)
            self.model_name = "models/gemini-2.5-flash"
            self.fallback_model = "models/gemini-2.0-flash"
    
    async def generate(self, prompt: str, **kwargs) -> str:
        if not self.is_available:
            raise ValueError("Gemini provider is not available")
            
        try:
            model = genai.GenerativeModel(self.model_name)
            response = await asyncio.to_thread(
                model.generate_content,
                prompt,
                generation_config={
                    "temperature": 0.7,
                    "top_p": 0.95,
                    "top_k": 40,
                    "max_output_tokens": 2048,
                },
                **kwargs
            )
            
            self.total_requests += 1
            self.total_tokens += len(response.text)  # Approximate token count
            return response.text
            
        except Exception as e:
            self.error_count += 1
            self.last_error = str(e)
            
            # Try fallback model if available
            if hasattr(self, 'fallback_model'):
                try:
                    model = genai.GenerativeModel(self.fallback_model)
                    response = await asyncio.to_thread(
                        model.generate_content,
                        prompt,
                        **kwargs
                    )
                    return response.text
                except Exception as fallback_error:
                    self.last_error = f"Primary: {e}, Fallback: {fallback_error}"
                    raise
            
            raise


class GroqProvider(LLMProvider):
    """Groq provider"""
    
    def __init__(self, api_key: str):
        super().__init__("Groq", api_key)
        if self.is_available:
            self.client = Groq(api_key=api_key)
            self.model_name = "llama-3.3-70b-versatile"
    
    async def generate(self, prompt: str, **kwargs) -> str:
        if not self.is_available:
            raise ValueError("Groq provider is not available")
            
        try:
            async with llm_rate_limiter:
                response = await asyncio.to_thread(
                    self.client.chat.completions.create,
                    messages=[{"role": "user", "content": prompt}],
                    model=self.model_name,
                    temperature=0.7,
                    max_tokens=2048,
                    **kwargs
                )
                
                self.total_requests += 1
                if hasattr(response, 'usage') and hasattr(response.usage, 'total_tokens'):
                    self.total_tokens += response.usage.total_tokens
                return response.choices[0].message.content
                
        except Exception as e:
            self.error_count += 1
            self.last_error = str(e)
            raise


class DeepSeekProvider(LLMProvider):
    """DeepSeek provider (using OpenAI-compatible API)"""
    
    def __init__(self, api_key: str):
        super().__init__("DeepSeek", api_key)
        if self.is_available:
            self.client = openai.OpenAI(
                api_key=api_key,
                base_url="https://api.deepseek.com/v1"
            )
            self.model_name = "deepseek-chat"
    
    async def generate(self, prompt: str, **kwargs) -> str:
        if not self.is_available:
            raise ValueError("DeepSeek provider is not available")
            
        try:
            async with llm_rate_limiter:
                response = await asyncio.to_thread(
                    self.client.chat.completions.create,
                    messages=[{"role": "user", "content": prompt}],
                    model=self.model_name,
                    temperature=0.7,
                    max_tokens=2048,
                    **kwargs
                )
                
                self.total_requests += 1
                if hasattr(response, 'usage') and hasattr(response.usage, 'total_tokens'):
                    self.total_tokens += response.usage.total_tokens
                return response.choices[0].message.content
                
        except Exception as e:
            self.error_count += 1
            self.last_error = str(e)
            raise


class LLMRotator:
    """Manages multiple LLM providers with rotation and fallback"""
    
    def __init__(self):
        self.providers: List[LLMProvider] = []
        self.current_index = 0
        self.setup_providers()
    
    def setup_providers(self) -> None:
        """Initialize all available providers"""
        # Add Gemini provider if API key is available
        gemini_key = os.getenv("GEMINI_API_KEY")
        if gemini_key:
            self.providers.append(GeminiProvider(gemini_key))
        
        # Add Groq provider if API key is available
        groq_key = os.getenv("GROQ_API_KEY")
        if groq_key:
            self.providers.append(GroqProvider(groq_key))
        
        # Add DeepSeek provider if API key is available
        deepseek_key = os.getenv("DEEPSEEK_API_KEY")
        if deepseek_key:
            self.providers.append(DeepSeekProvider(deepseek_key))
        
        if not self.providers:
            raise ValueError("No LLM providers configured. Please set at least one API key.")
    
    def get_next_provider(self) -> Optional[LLMProvider]:
        """Get the next healthy provider in rotation"""
        if not self.providers:
            return None
            
        # Try up to all providers once
        for _ in range(len(self.providers)):
            provider = self.providers[self.current_index]
            self.current_index = (self.current_index + 1) % len(self.providers)
            
            if provider.is_available:
                return provider
                
        return None
    
    async def generate_with_rotation(self, prompt: str, max_attempts: int = 3) -> str:
        """Generate content using rotation across providers"""
        attempts = 0
        last_error = None
        
        while attempts < max_attempts * len(self.providers):
            provider = self.get_next_provider()
            if not provider:
                break
                
            try:
                return await provider.generate(prompt)
            except Exception as e:
                last_error = f"{provider.name} error: {str(e)}"
                attempts += 1
                
                # Exponential backoff
                await asyncio.sleep(min(2 ** attempts, 10))
        
        raise Exception(f"All providers failed after {attempts} attempts. Last error: {last_error}")
    
    def get_status(self) -> Dict[str, Any]:
        """Get status of all providers"""
        return {
            "providers": [p.get_metrics() for p in self.providers],
            "total_requests": sum(p.total_requests for p in self.providers),
            "total_tokens": sum(p.total_tokens for p in self.providers),
        }


# Global rotator instance
_rotator = None


def get_rotator() -> LLMRotator:
    """Get the global LLM rotator instance"""
    global _rotator
    if _rotator is None:
        _rotator = LLMRotator()
    return _rotator


async def generate_doc_for_file(filename: str, code: str) -> str:
    """Generate markdown docs using the shared rotator (async wrapper)."""

    prompt = sync_make_prompt(filename, code)
    rotator = get_rotator()

    def _invoke() -> str:
        result = rotator.generate_with_rotation(prompt)
        if result:
            return result
        return sync_create_fallback_doc(filename, code, rotator.get_status())

    try:
        return await asyncio.to_thread(_invoke)
    except Exception as exc:  # pragma: no cover - defensive
        return sync_create_fallback_doc(filename, code, {"error": str(exc)})


def make_prompt(filename: str, code: str) -> str:
    """Create a prompt for documentation generation"""
    return f"""
    Please generate comprehensive documentation for the following code file:
    
    File: {filename}
    ```
    {code}
    ```
    
    The documentation should include:
    1. A clear description of what the code does
    2. Function/method signatures with parameters and return values
    3. Any important implementation details
    4. Example usage if applicable
    5. Any potential edge cases or gotchas
    
    Format the output in clear, well-structured markdown.
    """


def create_fallback_doc(filename: str, code: str, status: Dict) -> str:
    """Create a fallback documentation when all providers fail"""
    return f"""# Documentation Generation Failed

    ## {filename}
    
    **Error**: Failed to generate documentation using LLM providers.
    
    **Status**: {status.get('error', 'Unknown error')}
    
    ## Code
    ```python
    {code}
    ```
    """


def format_status(status: Dict) -> str:
    """Format provider status for display"""
    output = ["## LLM Provider Status\n"]
    
    for provider in status.get('providers', []):
        output.append(f"### {provider['name']} ({'✅ Available' if provider['is_available'] else '❌ Unavailable'})")
        output.append(f"- Model: {provider.get('model', 'N/A')}")
        output.append(f"- Requests: {provider.get('total_requests', 0)}")
        output.append(f"- Tokens: {provider.get('total_tokens', 0)}")
        
        if provider.get('error_count', 0) > 0:
            output.append(f"- Errors: {provider['error_count']} (Last: {provider.get('last_error', 'None')})")
        
        output.append("")
    
    output.append(f"\n**Total Requests**: {status.get('total_requests', 0)}")
    output.append(f"**Total Tokens**: {status.get('total_tokens', 0)}")
    
    return "\n".join(output)


# Backward compatibility functions
def get_available_models() -> list:
    """Get available models for backward compatibility"""
    return ["gemini-pro", "llama-3.3-70b-versatile", "deepseek-chat"]


def check_model_availability(model_name: str) -> bool:
    """Check model availability for backward compatibility"""
    return model_name in get_available_models()
