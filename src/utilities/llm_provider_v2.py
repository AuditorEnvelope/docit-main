# llm_provider_v2.py - Multi-provider LLM with rotation support
import os
import random
import time
import asyncio
from typing import List, Dict, Optional, Tuple
from dotenv import load_dotenv
load_dotenv()

# Import providers
import google.generativeai as genai
from groq import Groq
import openai

# Rate limiting (imported from smart_processor to share global limiter)
try:
    from aiolimiter import AsyncLimiter
    llm_rate_limiter = AsyncLimiter(50, 60)  # 50 requests per minute
    HAS_RATE_LIMITER = True
except ImportError:
    HAS_RATE_LIMITER = False

class LLMProvider:
    """Base class for LLM providers"""
    def __init__(self, name: str, api_key: str):
        self.name = name
        self.api_key = api_key
        self.is_available = bool(api_key)
        self.last_error = None
        self.error_count = 0
        self.max_errors = 3
        
    def generate(self, prompt: str, **kwargs) -> Optional[str]:
        """Generate content using this provider"""
        raise NotImplementedError
        
    def is_healthy(self) -> bool:
        """Check if provider is healthy (not too many errors)"""
        return self.is_available and self.error_count < self.max_errors
        
    def record_error(self, error: Exception):
        """Record an error for this provider"""
        self.error_count += 1
        self.last_error = str(error)
        print(f"❌ {self.name} error #{self.error_count}: {error}")

class GeminiProvider(LLMProvider):
    """Google Gemini provider"""
    def __init__(self, api_key: str):
        super().__init__("Gemini", api_key)
        if self.is_available:
            genai.configure(api_key=api_key)
            self.model_name = "models/gemini-2.5-flash"
            self.fallback_model = "models/gemini-2.0-flash"
    
    def generate(self, prompt: str, **kwargs) -> Optional[str]:
        if not self.is_healthy():
            return None
            
        try:
            # Try primary model first
            try:
                model = genai.GenerativeModel(self.model_name)
                resp = model.generate_content(prompt)
                result = getattr(resp, "text", None) or str(resp)
                if result and "quota" not in result.lower():
                    return result
            except Exception as e:
                if "quota" in str(e).lower():
                    print(f"⚠️ {self.name} quota exceeded, trying fallback")
                    model = genai.GenerativeModel(self.fallback_model)
                    resp = model.generate_content(prompt)
                    result = getattr(resp, "text", None) or str(resp)
                    return result
                raise e
                
        except Exception as e:
            self.record_error(e)
            return None

class GroqProvider(LLMProvider):
    """Groq provider"""
    def __init__(self, api_key: str):
        super().__init__("Groq", api_key)
        if self.is_available:
            self.client = Groq(api_key=api_key)
            self.model_name = "llama-3.3-70b-versatile"  # Fast and capable model
    
    def generate(self, prompt: str, **kwargs) -> Optional[str]:
        if not self.is_healthy():
            return None
            
        try:
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=4000,
                temperature=0.1
            )
            return response.choices[0].message.content
        except Exception as e:
            self.record_error(e)
            return None

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
    
    def generate(self, prompt: str, **kwargs) -> Optional[str]:
        if not self.is_healthy():
            return None
            
        try:
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=4000,
                temperature=0.1
            )
            return response.choices[0].message.content
        except Exception as e:
            self.record_error(e)
            return None

class LLMRotator:
    """Manages multiple LLM providers with rotation and fallback"""
    
    def __init__(self):
        self.providers: List[LLMProvider] = []
        self.current_index = 0
        self.setup_providers()
        
    def setup_providers(self):
        """Initialize all available providers"""
        # Gemini
        gemini_key = os.getenv("GEMINI_API_KEY")
        if gemini_key:
            self.providers.append(GeminiProvider(gemini_key))
            print(f"✅ Gemini provider initialized")
        
        # Groq
        groq_key = os.getenv("GROQ_API_KEY")
        if groq_key:
            self.providers.append(GroqProvider(groq_key))
            print(f"✅ Groq provider initialized")
        
        # DeepSeek
        deepseek_key = os.getenv("DEEPSEEK_API_KEY")
        if deepseek_key:
            self.providers.append(DeepSeekProvider(deepseek_key))
            print(f"✅ DeepSeek provider initialized")
        
        print(f"🚀 Initialized {len(self.providers)} LLM providers")
        
        if not self.providers:
            raise Exception("No LLM providers available! Please set at least one API key.")
    
    def get_next_provider(self) -> Optional[LLMProvider]:
        """Get the next healthy provider in rotation"""
        healthy_providers = [p for p in self.providers if p.is_healthy()]
        
        if not healthy_providers:
            print("❌ No healthy providers available")
            return None
        
        # Simple round-robin rotation
        provider = healthy_providers[self.current_index % len(healthy_providers)]
        self.current_index += 1
        return provider
    
    def generate_with_rotation(self, prompt: str, max_attempts: int = 3) -> Optional[str]:
        """Generate content using rotation across providers"""
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
                print(f"⏳ Waiting 2 seconds before retry...")
                time.sleep(2)
        
        print("❌ All providers failed")
        return None
    
    def get_status(self) -> Dict:
        """Get status of all providers"""
        return {
            "total_providers": len(self.providers),
            "healthy_providers": len([p for p in self.providers if p.is_healthy()]),
            "providers": [
                {
                    "name": p.name,
                    "available": p.is_available,
                    "healthy": p.is_healthy(),
                    "error_count": p.error_count,
                    "last_error": p.last_error
                }
                for p in self.providers
            ]
        }

# Global rotator instance
_rotator = None

def get_rotator() -> LLMRotator:
    """Get the global LLM rotator instance"""
    global _rotator
    if _rotator is None:
        _rotator = LLMRotator()
    return _rotator

def generate_doc_for_file(filename: str, code: str) -> str:
    """Generate markdown docs using LLM rotation. Never raise; return a fallback doc on error."""
    prompt = make_prompt(filename, code)
    
    try:
        rotator = get_rotator()
        result = rotator.generate_with_rotation(prompt)
        
        if result:
            return result
        else:
            # Fallback documentation
            return create_fallback_doc(filename, code, rotator.get_status())
            
    except Exception as e:
        print(f"❌ LLM generation failed: {e}")
        return create_fallback_doc(filename, code, {"error": str(e)})

def make_prompt(filename: str, code: str) -> str:
    """Create a prompt for documentation generation"""
    if len(code) > 12000:
        code = code[:12000] + "\n\n# TRUNCATED\n"
    
    return f"""You are DocAI, an expert documentation generator. Generate comprehensive markdown documentation for the following code.

Filename: {filename}

Code:
```{filename.split('.')[-1] if '.' in filename else 'text'}
{code}
```

Please provide:
1. **Purpose**: 1-2 line description of what this code does
2. **Functions/Classes**: For each function/class, provide:
   - Signature
   - 1-line summary
   - Parameters (if any)
   - Return value (if any)
3. **Example Usage**: Show how to use the main functions
4. **Notes/TODOs**: Any important notes or future improvements

Output only the markdown documentation, no additional text."""

def create_fallback_doc(filename: str, code: str, status: Dict) -> str:
    """Create a fallback documentation when all providers fail"""
    return f"""# {filename}

_Automatic documentation generation failed._

## Status
{format_status(status)}

## Code (truncated)
```{filename.split('.')[-1] if '.' in filename else 'text'}
{code[:1000]}{'...' if len(code) > 1000 else ''}
```

## Manual Documentation Needed
Please add proper documentation for this file manually.
"""

def format_status(status: Dict) -> str:
    """Format provider status for display"""
    if "error" in status:
        return f"**Error:** {status['error']}"
    
    lines = [
        f"**Total providers:** {status['total_providers']}",
        f"**Healthy providers:** {status['healthy_providers']}",
        "",
        "**Provider Status:**"
    ]
    
    for provider in status['providers']:
        status_icon = "✅" if provider['healthy'] else "❌"
        lines.append(f"- {status_icon} {provider['name']}: {provider['error_count']} errors")
        if provider['last_error']:
            lines.append(f"  - Last error: {provider['last_error'][:100]}...")
    
    return "\n".join(lines)

# Backward compatibility
def get_available_models():
    """Get available models for backward compatibility"""
    rotator = get_rotator()
    return [f"{p.name} ({p.name})" for p in rotator.providers if p.is_healthy()]

def check_model_availability(model_name: str):
    """Check model availability for backward compatibility"""
    rotator = get_rotator()
    return any(p.is_healthy() for p in rotator.providers)