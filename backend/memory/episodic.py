"""
Episodic Memory Store

Stores recent interactions across sessions using Redis with TTL-based expiry.
Memories decay naturally based on age and retrieval frequency.
Implemented in Phase 2.
"""

from dataclasses import dataclass
from datetime import datetime


@dataclass
class EpisodicMemory:
    id: str
    user_id: str
    summary: str
    created_at: datetime
    ttl_days: int
    retrieval_count: int = 0
    importance_score: float = 0.5


class EpisodicMemoryStore:
    """
    Tier 2 of MemoryWeave: Short-to-medium term memory backed by Redis.

    Responsibilities:
    - Store session summaries with TTL expiry
    - Retrieve recent memories by user_id
    - Track retrieval frequency for scoring
    - Feed consolidated memories to SemanticMemoryStore
    """

    def __init__(self, redis_url: str):
        self.redis_url = redis_url
        self._redis = None

    def connect(self) -> None:
        raise NotImplementedError("Implemented in Phase 2")

    def store(self, user_id: str, summary: str, ttl_days: int = 30) -> str:
        raise NotImplementedError("Implemented in Phase 2")

    def retrieve(self, user_id: str, limit: int = 10) -> list[EpisodicMemory]:
        raise NotImplementedError("Implemented in Phase 2")

    def delete(self, memory_id: str) -> bool:
        raise NotImplementedError("Implemented in Phase 2")

    def get_all_for_consolidation(self, user_id: str) -> list[EpisodicMemory]:
        raise NotImplementedError("Implemented in Phase 2")
