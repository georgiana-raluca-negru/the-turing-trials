# backend/app/services/game_store.py
"""
In-memory match state store.

Holds MatchRuntimeState objects keyed by match_id (UUID as string).
Thread-safe via a simple lock — sufficient for a single-process deployment.

NOTE: State is lost on server restart. A Redis / DB persistence adapter
is planned as a future enhancement.
"""

import threading
from typing import Optional

from backend_integration.models.match import MatchRuntimeState


class GameStore:
    """Thread-safe in-memory store for active match runtime states."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._states: dict[str, MatchRuntimeState] = {}

    def save(self, match_id: str, state: MatchRuntimeState) -> None:
        with self._lock:
            self._states[match_id] = state

    def get(self, match_id: str) -> Optional[MatchRuntimeState]:
        with self._lock:
            return self._states.get(match_id)

    def delete(self, match_id: str) -> None:
        with self._lock:
            self._states.pop(match_id, None)

    def has(self, match_id: str) -> bool:
        with self._lock:
            return match_id in self._states


# Single shared instance — import this everywhere
game_store = GameStore()
