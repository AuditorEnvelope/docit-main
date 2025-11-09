from pathlib import Path
from typing import Dict


def create_fallback_doc(filename: str, code: str, status: Dict) -> str:
    """Create a fallback documentation when LLM providers fail."""
    return (
        "# Documentation Generation Failed\n\n"
        f"## {filename}\n\n"
        "**Error**: Failed to generate documentation using LLM providers.\n\n"
        f"**Status**: {status.get('error', 'Unknown error')}\n\n"
        "## Code\n\n"
        "```python\n"
        f"{code}\n"
        "```\n"
    )
