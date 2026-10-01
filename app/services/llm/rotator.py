"""Multi-provider LLM rotation with key-pool parallelism.

Architecture (v2 – voice-locked fan-out):
  - Each provider (Gemini, Groq, DeepSeek) owns N API keys parsed from a
    comma-separated env var.
  - A "key slot" tracks per-key health (error count, in-flight requests,
    long-duration rate-limit disable).
  - `generate_with_pool()` (async) picks the least-loaded healthy slot,
    runs the call, and returns an LLMResult.
  - `generate_with_rotation()` (sync, legacy) is retained for backward compat.

Phase 6 Enhancement: Token tracking for shadow ledger metrics.
"""
from __future__ import annotations

import asyncio
import os
import re
import time
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field

import google.generativeai as genai
from groq import Groq
import openai


# ═══════════════════════════════════════════════════════════════════════════
# Data classes
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class LLMResult:
    """Result of LLM generation with token usage (Phase 6)"""
    content: str
    model_name: str
    input_tokens: int
    output_tokens: int
    total_tokens: int


@dataclass
class KeySlot:
    """Health tracker for a single API key within a provider's pool."""
    key: str
    index: int
    healthy: bool = True
    error_count: int = 0
    in_flight: int = 0
    last_error: str = ""
    last_used_at: float = 0.0
    max_errors: int = 3


# ═══════════════════════════════════════════════════════════════════════════
# Provider base
# ═══════════════════════════════════════════════════════════════════════════

class LLMProvider:
    """Base class for multi-key LLM providers."""

    provider_name: str = "Base"

    def __init__(self, keys: List[str]):
        self.slots: List[KeySlot] = [
            KeySlot(key=k.strip(), index=i) for i, k in enumerate(keys) if k.strip()
        ]
        self.name = self.provider_name
        # Legacy compat
        self.is_available = bool(self.slots)
        self.last_error: Optional[str] = None
        self.error_count = 0

    @property
    def pool_size(self) -> int:
        return len(self.slots)

    def healthy_slots(self) -> List[KeySlot]:
        return [s for s in self.slots if s.healthy and s.error_count < s.max_errors]

    def is_healthy(self) -> bool:
        return self.is_available and bool(self.healthy_slots())

    def acquire_slot(self) -> Optional[KeySlot]:
        """Pick the healthy slot with the lowest in-flight, tiebreak by LRU."""
        healthy = self.healthy_slots()
        if not healthy:
            return None
        return min(healthy, key=lambda s: (s.in_flight, s.last_used_at))

    def generate_with_slot(self, prompt: str, slot: KeySlot) -> Optional[LLMResult]:
        """Subclasses implement this – call the LLM using the given key slot."""
        raise NotImplementedError

    def generate(self, prompt: str) -> Optional[LLMResult]:
        """Legacy sync interface – picks a slot and calls it."""
        slot = self.acquire_slot()
        if not slot:
            return None
        slot.in_flight += 1
        slot.last_used_at = time.time()
        try:
            result = self.generate_with_slot(prompt, slot)
            if result:
                return result
            return None
        finally:
            slot.in_flight = max(0, slot.in_flight - 1)

    def _record_slot_error(self, slot: KeySlot, error: Exception) -> None:
        err_str = str(error)
        slot.error_count += 1
        slot.last_error = err_str
        self.last_error = err_str
        self.error_count += 1
        print(
            f"❌ {self.name}[key#{slot.index}] error #{slot.error_count}: {error}")

    def _disable_slot_for_session(self, slot: KeySlot, reason: str) -> None:
        slot.healthy = False
        slot.last_error = reason
        self.last_error = reason
        print(
            f"🚫 {self.name}[key#{slot.index}] disabled for session: {reason}")


# ═══════════════════════════════════════════════════════════════════════════
# Gemini provider
# ═══════════════════════════════════════════════════════════════════════════

class GeminiProvider(LLMProvider):
    provider_name = "Gemini"

    def __init__(self, keys: List[str]):
        super().__init__(keys)
        self.model_name = "models/gemini-3.8-flash"
        self.fallback_model = "models/gemini-2.0-flash"
        # Configure with the first key; per-slot we'll reconfigure as needed
        if self.slots:
            genai.configure(api_key=self.slots[0].key)

    def generate_with_slot(self, prompt: str, slot: KeySlot) -> Optional[LLMResult]:
        genai.configure(api_key=slot.key)
        request_options = {"timeout": 180}
        try:
            model = genai.GenerativeModel(self.model_name)
            resp = model.generate_content(
                prompt, request_options=request_options)
            result = _extract_gemini_text(resp)
            finish_reason = _gemini_finish_reason(resp)

            usage_metadata = getattr(resp, "usage_metadata", None)
            input_tokens = getattr(
                usage_metadata, "prompt_token_count", 0) if usage_metadata else 0
            output_tokens = getattr(
                usage_metadata, "candidates_token_count", 0) if usage_metadata else 0
            total_tokens = getattr(usage_metadata, "total_token_count", 0) if usage_metadata else (
                input_tokens + output_tokens)

            if finish_reason == 4:
                print("⚠️  Gemini refused: RECITATION")
                slot.last_error = "RECITATION"
                slot.error_count += 1
                return None
            if finish_reason == 3:
                print("⚠️  Gemini refused: SAFETY filter")
                slot.last_error = "SAFETY"
                slot.error_count += 1
                return None

            if result and "quota" not in result.lower():
                return LLMResult(
                    content=result, model_name=self.model_name,
                    input_tokens=input_tokens, output_tokens=output_tokens,
                    total_tokens=total_tokens,
                )

        except Exception as primary_error:
            err_lower = str(primary_error).lower()
            if "quota" in err_lower:
                print(
                    f"⚠️ Gemini[key#{slot.index}] quota exceeded, trying fallback model")
                try:
                    model = genai.GenerativeModel(self.fallback_model)
                    resp = model.generate_content(
                        prompt, request_options=request_options)
                    result = _extract_gemini_text(resp)
                    usage_metadata = getattr(resp, "usage_metadata", None)
                    input_tokens = getattr(
                        usage_metadata, "prompt_token_count", 0) if usage_metadata else 0
                    output_tokens = getattr(
                        usage_metadata, "candidates_token_count", 0) if usage_metadata else 0
                    total_tokens = getattr(usage_metadata, "total_token_count", 0) if usage_metadata else (
                        input_tokens + output_tokens)
                    if result:
                        return LLMResult(
                            content=result, model_name=self.fallback_model,
                            input_tokens=input_tokens, output_tokens=output_tokens,
                            total_tokens=total_tokens,
                        )
                except Exception as fallback_error:
                    self._record_slot_error(slot, fallback_error)
                    return None
            if _is_long_rate_limit(str(primary_error)):
                self._disable_slot_for_session(slot, str(primary_error))
                return None
            self._record_slot_error(slot, primary_error)
            return None
        return None


# ═══════════════════════════════════════════════════════════════════════════
# Groq provider
# ═══════════════════════════════════════════════════════════════════════════

class GroqProvider(LLMProvider):
    provider_name = "Groq"

    def __init__(self, keys: List[str]):
        super().__init__(keys)
        self.model_name = "llama-3.3-70b-versatile"
        self._clients: Dict[int, Groq] = {}
        for slot in self.slots:
            self._clients[slot.index] = Groq(api_key=slot.key)

    def generate_with_slot(self, prompt: str, slot: KeySlot) -> Optional[LLMResult]:
        client = self._clients[slot.index]
        try:
            response = client.chat.completions.create(
                model=self.model_name,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=4000,
                temperature=0.1,
            )
            usage = response.usage
            return LLMResult(
                content=response.choices[0].message.content,
                model_name=self.model_name,
                input_tokens=getattr(usage, "prompt_tokens", 0),
                output_tokens=getattr(usage, "completion_tokens", 0),
                total_tokens=getattr(usage, "total_tokens", 0),
            )
        except Exception as error:
            if _is_long_rate_limit(str(error)):
                self._disable_slot_for_session(slot, str(error))
            else:
                self._record_slot_error(slot, error)
            return None


# ═══════════════════════════════════════════════════════════════════════════
# DeepSeek provider
# ═══════════════════════════════════════════════════════════════════════════

class DeepSeekProvider(LLMProvider):
    provider_name = "DeepSeek"

    def __init__(self, keys: List[str]):
        super().__init__(keys)
        self.model_name = "deepseek-chat"
        self._clients: Dict[int, openai.OpenAI] = {}
        for slot in self.slots:
            self._clients[slot.index] = openai.OpenAI(
                api_key=slot.key, base_url="https://api.deepseek.com/v1",
            )

    def generate_with_slot(self, prompt: str, slot: KeySlot) -> Optional[LLMResult]:
        client = self._clients[slot.index]
        try:
            response = client.chat.completions.create(
                model=self.model_name,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=4000,
                temperature=0.1,
            )
            usage = response.usage
            return LLMResult(
                content=response.choices[0].message.content,
                model_name=self.model_name,
                input_tokens=getattr(usage, "prompt_tokens", 0),
                output_tokens=getattr(usage, "completion_tokens", 0),
                total_tokens=getattr(usage, "total_tokens", 0),
            )
        except Exception as error:
            if _is_long_rate_limit(str(error)):
                self._disable_slot_for_session(slot, str(error))
            else:
                self._record_slot_error(slot, error)
            return None


# ═══════════════════════════════════════════════════════════════════════════
# LLM Rotator — orchestrates providers + key pools
# ═══════════════════════════════════════════════════════════════════════════

class LLMRotator:
    """Voice-locked multi-key rotation with per-section async support."""

    PROVIDER_PRIORITY = ["gemini", "groq", "deepseek"]

    def __init__(self) -> None:
        self.providers: Dict[str, LLMProvider] = {}
        self._setup()

    def _setup(self) -> None:
        gemini_keys = _parse_keys("GEMINI_API_KEY")
        groq_keys = _parse_keys("GROQ_API_KEY")
        deepseek_keys = _parse_keys("DEEPSEEK_API_KEY")

        if gemini_keys:
            self.providers["gemini"] = GeminiProvider(gemini_keys)
            print(
                f"✅ Gemini provider initialized ({len(gemini_keys)} key{'s' if len(gemini_keys) > 1 else ''})")
        if groq_keys:
            self.providers["groq"] = GroqProvider(groq_keys)
            print(
                f"✅ Groq provider initialized ({len(groq_keys)} key{'s' if len(groq_keys) > 1 else ''})")
        if deepseek_keys:
            self.providers["deepseek"] = DeepSeekProvider(deepseek_keys)
            print(
                f"✅ DeepSeek provider initialized ({len(deepseek_keys)} key{'s' if len(deepseek_keys) > 1 else ''})")

        total = sum(p.pool_size for p in self.providers.values())
        print(
            f"🚀 Initialized {len(self.providers)} providers, {total} total key slots")
        if not self.providers:
            raise RuntimeError(
                "No LLM providers available – configure at least one API key.")

    def get_preferred_provider(self) -> Optional[LLMProvider]:
        """Return the user's preferred provider (DOC_GENERATION_PROVIDER env),
        falling back to the first healthy one in priority order."""
        preferred = os.getenv("DOC_GENERATION_PROVIDER", "").lower().strip()
        if preferred and preferred in self.providers:
            p = self.providers[preferred]
            if p.is_healthy():
                return p

        for name in self.PROVIDER_PRIORITY:
            if name in self.providers and self.providers[name].is_healthy():
                return self.providers[name]
        return None

    # ── Async per-section generation ──────────────────────────────────
    async def generate_with_pool(
        self,
        prompt: str,
        provider: Optional[LLMProvider] = None,
        max_retries: int = 3,
    ) -> Optional[LLMResult]:
        """Generate content using a specific provider's key pool.

        Acquires the least-loaded key slot, calls the LLM, retries on
        transient errors using a DIFFERENT slot. Never compacts the prompt
        (per-section prompts are small enough to never need compaction).
        """
        target = provider or self.get_preferred_provider()
        if not target:
            print("❌ No healthy provider available")
            return None

        for attempt in range(1, max_retries + 1):
            slot = target.acquire_slot()
            if not slot:
                # This provider's pool is exhausted; try next provider
                print(f"⚠️  {target.name}: all key slots exhausted")
                target = self._next_healthy_provider(exclude=target.name)
                if not target:
                    print("❌ No healthy providers remaining")
                    return None
                print(f"🔀 Falling back to {target.name}")
                continue

            slot.in_flight += 1
            slot.last_used_at = time.time()
            try:
                print(f"🔄 {target.name}[key#{slot.index}] (attempt {attempt})")
                # Run the blocking LLM call in a thread so we don't block the event loop
                loop = asyncio.get_event_loop()
                result = await loop.run_in_executor(
                    None, target.generate_with_slot, prompt, slot
                )
                if result:
                    print(
                        f"✅ {target.name}[key#{slot.index}] | "
                        f"Tokens: {result.input_tokens} in / {result.output_tokens} out"
                    )
                    return result

                # Transient failure – wait briefly then retry on a different slot
                if attempt < max_retries:
                    wait = 3 if "504" in (slot.last_error or "") else 2
                    print(f"⏳ Waiting {wait}s before retry...")
                    await asyncio.sleep(wait)

            finally:
                slot.in_flight = max(0, slot.in_flight - 1)

        print(f"❌ {target.name}: all retries exhausted")
        return None

    def _next_healthy_provider(self, exclude: str = "") -> Optional[LLMProvider]:
        for name in self.PROVIDER_PRIORITY:
            if name == exclude.lower():
                continue
            if name in self.providers and self.providers[name].is_healthy():
                return self.providers[name]
        return None

    # ── Legacy sync interface (planning call, backward compat) ────────
    def generate_with_rotation(self, prompt: str, max_attempts: int = 3) -> Optional[LLMResult]:
        """Sync generation with provider rotation. Used for planning calls."""
        for attempt in range(1, max_attempts + 1):
            provider = self.get_preferred_provider()
            if not provider:
                print("❌ No healthy providers available")
                return None

            print(f"🔄 Trying {provider.name} (attempt {attempt})")
            result = provider.generate(prompt)
            if result:
                print(
                    f"✅ Success with {provider.name} | "
                    f"Tokens: {result.input_tokens} in / {result.output_tokens} out"
                )
                return result

            if attempt < max_attempts:
                last_err = (provider.last_error or "").lower()
                wait = 5 if "504" in last_err or "stream" in last_err else 2
                print(f"⏳ Waiting {wait}s before retry...")
                time.sleep(wait)

        print("❌ All providers failed")
        return None

    def get_status(self) -> Dict[str, object]:
        return {
            "total_providers": len(self.providers),
            "providers": {
                name: {
                    "healthy": p.is_healthy(),
                    "pool_size": p.pool_size,
                    "healthy_slots": len(p.healthy_slots()),
                    "slots": [
                        {"index": s.index, "healthy": s.healthy,
                         "error_count": s.error_count, "in_flight": s.in_flight}
                        for s in p.slots
                    ],
                }
                for name, p in self.providers.items()
            },
        }


# ═══════════════════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════════════════

def _parse_keys(env_var: str) -> List[str]:
    """Parse comma-separated API keys from an env var."""
    raw = os.getenv(env_var, "")
    if not raw:
        return []
    return [k.strip() for k in raw.split(",") if k.strip()]


def _extract_gemini_text(resp) -> str:
    """Safely extract text from a Gemini response, tolerating refusals."""
    try:
        text = getattr(resp, "text", None)
        if text:
            return text
    except Exception:
        pass
    try:
        for cand in getattr(resp, "candidates", []) or []:
            content = getattr(cand, "content", None)
            for part in (getattr(content, "parts", None) or []):
                ptext = getattr(part, "text", None)
                if ptext:
                    return ptext
    except Exception:
        pass
    return ""


def _gemini_finish_reason(resp) -> Optional[int]:
    """Return the int finish_reason from the first candidate, or None."""
    try:
        candidates = getattr(resp, "candidates", None) or []
        if not candidates:
            return None
        reason = getattr(candidates[0], "finish_reason", None)
        if reason is None:
            return None
        value = getattr(reason, "value", None)
        if value is not None:
            return int(value)
        return int(reason)
    except Exception:
        return None


def _is_long_rate_limit(error_message: str) -> bool:
    """Detect daily/long-duration rate limits where retrying is futile."""
    if not error_message:
        return False
    lower = error_message.lower()
    if "tokens per day" in lower or "tpd" in lower or "per day" in lower:
        return True
    m = re.search(r'try again in\s+(\d+)h', lower)
    if m and int(m.group(1)) >= 1:
        return True
    m = re.search(r'try again in\s+(\d+)m', lower)
    if m and int(m.group(1)) >= 2:
        return True
    return False


# ═══════════════════════════════════════════════════════════════════════════
# Singleton + backward-compat API
# ═══════════════════════════════════════════════════════════════════════════

_rotator: Optional[LLMRotator] = None


def get_rotator() -> LLMRotator:
    global _rotator
    if _rotator is None:
        _rotator = LLMRotator()
    return _rotator


def create_fallback_doc(filename: str, code: str, status: Dict[str, object]) -> str:
    snippet = code[:1000] + ("..." if len(code) > 1000 else "")
    return (
        f"# {filename}\n\n"
        "_Automatic documentation generation failed._\n\n"
        "## Provider Status\n"
        f"```json\n{status}\n```\n\n"
        "## Code (truncated)\n"
        f"```\n{snippet}\n```\n"
        "\n## Manual Documentation Needed\n"
        "Please add proper documentation manually.\n"
    )


def generate_doc_for_file(filename: str, code: str) -> str:
    """Generate documentation for a file (backwards compatible)"""
    prompt = make_prompt(filename, code)
    try:
        result = get_rotator().generate_with_rotation(prompt)
        if result:
            return result.content
        return create_fallback_doc(filename, code, get_rotator().get_status())
    except Exception as error:
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
