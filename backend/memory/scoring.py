"""
Memory Scoring — Smart Forgetting Algorithm

Computes a retention score for each memory based on:
  - Recency: how recently was this memory created/accessed
  - Frequency: how often has it been retrieved
  - Importance: semantic importance tagged by Qwen at creation time

Score formula: score = (recency_weight * R) + (frequency_weight * F) + (importance_weight * I)

Memories with score below the prune_threshold are candidates for deletion.
"""

import math
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
        """Exponential decay: score = e^(-ln(2) * age_days / half_life)."""
        age_days = (datetime.utcnow() - last_accessed).total_seconds() / 86400.0
        return math.exp(-math.log(2) * age_days / self.recency_half_life_days)

    def compute_frequency(self, access_count: int, max_count: int = 50) -> float:
        """Log-normalized frequency score in [0, 1]."""
        return min(1.0, math.log1p(access_count) / math.log1p(max_count))

    def score(
        self,
        memory_id: str,
        last_accessed: datetime,
        access_count: int,
        importance_score: float,
    ) -> MemoryScore:
        r = self.compute_recency(last_accessed)
        f = self.compute_frequency(access_count)
        i = max(0.0, min(1.0, importance_score))
        final = (
            self.recency_weight * r
            + self.frequency_weight * f
            + self.importance_weight * i
        )
        return MemoryScore(
            memory_id=memory_id,
            recency_score=round(r, 4),
            frequency_score=round(f, 4),
            importance_score=round(i, 4),
            final_score=round(final, 4),
            should_prune=final < self.prune_threshold,
        )

    def batch_score(self, memories: list[dict]) -> list[MemoryScore]:
        """
        Score a list of memory dicts.
        Each dict must have: id, last_accessed (datetime), access_count (int), importance_score (float).
        """
        return [
            self.score(
                memory_id=m["id"],
                last_accessed=m["last_accessed"],
                access_count=m["access_count"],
                importance_score=m["importance_score"],
            )
            for m in memories
        ]
