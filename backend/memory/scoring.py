"""
Memory Scoring — Smart Forgetting Algorithm

Computes a retention score for each memory based on:
  - Recency: how recently was this memory created/accessed
  - Frequency: how often has it been retrieved
  - Importance: semantic importance tagged by Qwen at creation time

Score formula: score = (recency_weight * R) + (frequency_weight * F) + (importance_weight * I)

Memories with score below the prune_threshold are candidates for deletion.
Implemented in Phase 2.
"""

from dataclasses import dataclass
from datetime import datetime


@dataclass
class MemoryScore:
    memory_id: str
    recency_score: float
    frequency_score: float
    importance_score: float
    final_score: float
    should_prune: bool


class MemoryScorer:
    """
    Computes retention scores for MemoryWeave memories.

    Used by the consolidation pipeline and scheduled maintenance jobs
    to decide which memories to keep, promote, or prune.
    """

    def __init__(
        self,
        recency_weight: float = 0.4,
        frequency_weight: float = 0.3,
        importance_weight: float = 0.3,
        prune_threshold: float = 0.2,
        recency_half_life_days: float = 14.0,
    ):
        self.recency_weight = recency_weight
        self.frequency_weight = frequency_weight
        self.importance_weight = importance_weight
        self.prune_threshold = prune_threshold
        self.recency_half_life_days = recency_half_life_days

    def compute_recency(self, last_accessed: datetime) -> float:
        raise NotImplementedError("Implemented in Phase 2")

    def compute_frequency(self, access_count: int, max_count: int = 50) -> float:
        raise NotImplementedError("Implemented in Phase 2")

    def score(
        self,
        memory_id: str,
        last_accessed: datetime,
        access_count: int,
        importance_score: float,
    ) -> MemoryScore:
        raise NotImplementedError("Implemented in Phase 2")

    def batch_score(self, memories: list[dict]) -> list[MemoryScore]:
        raise NotImplementedError("Implemented in Phase 2")
