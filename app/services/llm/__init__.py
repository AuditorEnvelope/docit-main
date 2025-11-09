from typing import Optional
from enum import Enum

from .service import LLMService, LLMProvider
from app.core.config import settings

# Initialize the default LLM service
_llm_service: Optional[LLMService] = None

def get_llm_service(provider: Optional[LLMProvider] = None) -> LLMService:
    """
    Get the configured LLM service instance.
    
    Args:
        provider: Optional provider to use (defaults to configured provider)
    
    Returns:
        LLMService: Configured LLM service instance
    """
    global _llm_service
    
    if _llm_service is None or (provider and _llm_service.provider != provider):
        provider_enum = LLMProvider(provider or settings.LLM_PROVIDER)
        _llm_service = LLMService(provider=provider_enum)
    
    return _llm_service

__all__ = [
    'LLMService',
    'LLMProvider',
    'get_llm_service',
]
