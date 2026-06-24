"""
Semantic Memory Store

Long-term memory backed by ChromaDB vector database.
Stores facts, user preferences, and learned patterns as vector embeddings.
Retrieved via semantic similarity search using Qwen text-embedding-v3.
Implemented in Phase 2.
"""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum


class MemoryType(str, Enum):
    PREFERENCE = "preference"
    FACT = "fact"
    SKILL = "skill"
    RELATIONSHIP = "relationship"


@dataclass
class SemanticMemory:
    id: str
    user_id: str
    content: str
    memory_type: MemoryType
    importance_score: float
    created_at: datetime
    last_accessed: datetime
    access_count: int = 0
    metadata: dict = None


class SemanticMemoryStore:
    """
    Tier 3 of MemoryWeave: Long-term semantic memory via ChromaDB + Qwen embeddings.

    Responsibilities:
    - Store memory facts as vector embeddings (text-embedding-v3)
    - Retrieve top-K most relevant memories by semantic similarity
    - Pack memories into Qwen context window without exceeding token budget
    - Handle contradiction detection (new fact vs. existing fact)
    - Prune low-score memories during maintenance
    """

    def __init__(self, chroma_path: str = "./chroma_db"):
        self.chroma_path = chroma_path
        self._collection = None

    def initialize(self) -> None:
        raise NotImplementedError("Implemented in Phase 2")

    def store(
        self,
        user_id: str,
        content: str,
        memory_type: MemoryType,
        importance_score: float = 0.5,
    ) -> str:
        raise NotImplementedError("Implemented in Phase 2")

    def search(
        self,
        user_id: str,
        query: str,
        top_k: int = 5,
        min_score: float = 0.3,
    ) -> list[SemanticMemory]:
        raise NotImplementedError("Implemented in Phase 2")

    def delete(self, memory_id: str) -> bool:
        raise NotImplementedError("Implemented in Phase 2")

    def get_all(self, user_id: str) -> list[SemanticMemory]:
        raise NotImplementedError("Implemented in Phase 2")

    def prune_low_score(self, user_id: str, threshold: float = 0.2) -> int:
        raise NotImplementedError("Implemented in Phase 2")
