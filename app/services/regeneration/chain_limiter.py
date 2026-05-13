"""
Selective Regeneration Chain Limiter - Phase 4.5

Tracks consecutive selective regenerations and forces full regeneration
after threshold to prevent error accumulation.

Safety: Prevents degradation from repeated partial updates.
"""

import json
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional


# Phase 4.5: Chain limit configuration
SELECTIVE_REGEN_CHAIN_LIMIT = 3  # Force full regen after N selective regenerations


@dataclass
class ChainState:
    """
    Tracks selective regeneration chain state.
    """
    repo_id: str
    persona: str
    selective_regen_count: int = 0
    last_full_regeneration: Optional[datetime] = None
    last_selective_regeneration: Optional[datetime] = None
    chain_start_commit: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "repo_id": self.repo_id,
            "persona": self.persona,
            "selective_regen_count": self.selective_regen_count,
            "last_full_regeneration": self.last_full_regeneration.isoformat() if self.last_full_regeneration else None,
            "last_selective_regeneration": self.last_selective_regeneration.isoformat() if self.last_selective_regeneration else None,
            "chain_start_commit": self.chain_start_commit,
        }


class SelectiveRegenerationChainLimiter:
    """
    Manages selective regeneration chain limits.

    Rules:
    1. Track consecutive selective regenerations per repo+persona
    2. Force full regeneration after SELECTIVE_REGEN_CHAIN_LIMIT
    3. Reset counter on full regeneration
    4. Persist state in memory (no DB required)
    """

    def __init__(self):
        # In-memory state storage: {(repo_id, persona): ChainState}
        self._state: Dict[tuple, ChainState] = {}

    def check_and_update(
        self,
        repo_id: str,
        persona: str,
        commit_sha: str,
        is_selective: bool,
    ) -> tuple[bool, str]:
        """
        Check if selective regeneration is allowed and update state.

        Args:
            repo_id: Repository identifier
            persona: Documentation persona
            commit_sha: Current commit SHA
            is_selective: Whether this regeneration is selective

        Returns:
            Tuple of (allowed: bool, reason: str)
        """
        key = (repo_id, persona)

        # Get or create state
        if key not in self._state:
            self._state[key] = ChainState(
                repo_id=repo_id,
                persona=persona,
            )

        state = self._state[key]

        # If full regeneration, reset counter
        if not is_selective:
            state.selective_regen_count = 0
            state.last_full_regeneration = datetime.utcnow()
            return True, "full_regeneration_resets_chain"

        # Check chain limit
        if state.selective_regen_count >= SELECTIVE_REGEN_CHAIN_LIMIT:
            # Force full regeneration
            state.selective_regen_count = 0
            state.last_full_regeneration = datetime.utcnow()
            return False, f"chain_limit_reached_{SELECTIVE_REGEN_CHAIN_LIMIT}"

        # Increment selective count
        state.selective_regen_count += 1
        state.last_selective_regeneration = datetime.utcnow()

        # Set chain start if first in chain
        if state.selective_regen_count == 1:
            state.chain_start_commit = commit_sha

        return True, f"selective_regen_{state.selective_regen_count}_of_{SELECTIVE_REGEN_CHAIN_LIMIT}"

    def get_chain_state(self, repo_id: str, persona: str) -> Optional[ChainState]:
        """Get current chain state for repo+persona."""
        return self._state.get((repo_id, persona))

    def reset_chain(self, repo_id: str, persona: str) -> None:
        """Manually reset chain for repo+persona."""
        key = (repo_id, persona)
        if key in self._state:
            self._state[key].selective_regen_count = 0
            self._state[key].last_full_regeneration = datetime.utcnow()

    def should_force_full_regeneration(self, repo_id: str, persona: str) -> bool:
        """Check if full regeneration should be forced due to chain limit."""
        state = self._state.get((repo_id, persona))
        if not state:
            return False
        return state.selective_regen_count >= SELECTIVE_REGEN_CHAIN_LIMIT

    def get_stats(self) -> Dict[str, Any]:
        """Get overall chain limiter statistics."""
        return {
            "tracked_repos": len(self._state),
            "chain_limit": SELECTIVE_REGEN_CHAIN_LIMIT,
            "states": [s.to_dict() for s in self._state.values()],
        }


# ============================================================================
# Convenience Functions
# ============================================================================

_limiter_instance: Optional[SelectiveRegenerationChainLimiter] = None


def get_chain_limiter() -> SelectiveRegenerationChainLimiter:
    """Get singleton chain limiter."""
    global _limiter_instance
    if _limiter_instance is None:
        _limiter_instance = SelectiveRegenerationChainLimiter()
    return _limiter_instance


def check_selective_regeneration_allowed(
    repo_id: str,
    persona: str,
    commit_sha: str,
) -> tuple[bool, str]:
    """
    Check if selective regeneration is allowed (pre-check).

    Use before regeneration to determine strategy.
    """
    try:
        limiter = get_chain_limiter()
        # Assume selective for pre-check
        return limiter.check_and_update(repo_id, persona, commit_sha, is_selective=True)
    except Exception as e:
        print(f"⚠️ Chain limiter check failed (non-fatal): {e}")
        # Fail open: allow selective
        return True, "limiter_check_failed"


def record_regeneration_completed(
    repo_id: str,
    persona: str,
    commit_sha: str,
    was_selective: bool,
) -> tuple[bool, str]:
    """
    Record completed regeneration and update chain state.

    Call after regeneration completes.
    """
    try:
        limiter = get_chain_limiter()
        return limiter.check_and_update(repo_id, persona, commit_sha, was_selective)
    except Exception as e:
        print(f"⚠️ Chain limiter update failed (non-fatal): {e}")
        return True, "update_failed"


def get_chain_state(repo_id: str, persona: str) -> Optional[ChainState]:
    """Get current chain state."""
    try:
        limiter = get_chain_limiter()
        return limiter.get_chain_state(repo_id, persona)
    except Exception:
        return None
