"""
Centralized LLM API key management.

This module provides a single source of truth for LLM API key retrieval.
Currently reads from environment variables, but can be extended to fetch from database.
"""
import os
from typing import Optional

def get_llm_api_key() -> str:
    """
    Return the API key for the LLM provider.
    
    Priority order:
    1. LLM_API_KEY environment variable
    2. OPENAI_API_KEY environment variable (legacy support)
    3. Empty string if neither is set
    
    Returns:
        str: The API key or empty string if not found
    """
    return os.getenv("LLM_API_KEY") or os.getenv("OPENAI_API_KEY") or ""

def validate_llm_key(key: Optional[str] = None) -> bool:
    """
    Validate that an LLM API key is properly formatted.
    
    Args:
        key: The API key to validate. If None, gets the key using get_llm_api_key()
        
    Returns:
        bool: True if the key appears valid, False otherwise
    """
    key = key or get_llm_api_key()
    return bool(key and isinstance(key, str) and len(key.strip()) > 20)
