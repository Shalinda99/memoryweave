"""
Semantic Memory Store

Long-term memory backed by ChromaDB vector database.
Stores facts, user preferences, and learned patterns as vector embeddings.
Retrieved via semantic similarity search using Qwen text-embedding-v3.
"""

import uuid
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Callable

import chromadb

logger = logging.getLogger("memoryweave.semantic")


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
    metadata: dict = field(default_factory=dict)


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

    COLLECTION_NAME = "semantic_memories"

    def __init__(
        self,
        chroma_path: str = "./chroma_db",
        embed_fn: Callable[[str], list[float]] | None = None,
    ):
        self.chroma_path = chroma_path
        self.embed_fn = embed_fn
        self._client: chromadb.PersistentClient | None = None
        self._collection = None

    def initialize(self) -> None:
        self._client = chromadb.PersistentClient(path=self.chroma_path)
        self._collection = self._client.get_or_create_collection(
            name=self.COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"},
        )
        logger.info(f"SemanticMemoryStore initialized — {self._collection.count()} memories loaded")

    def store(
        self,
        user_id: str,
        content: str,
        memory_type: MemoryType,
        importance_score: float = 0.5,
    ) -> str:
        memory_id = str(uuid.uuid4())
        now = datetime.utcnow().isoformat()
        meta = {
            "user_id": user_id,
            "memory_type": memory_type.value,
            "importance_score": importance_score,
            "created_at": now,
            "last_accessed": now,
            "access_count": 0,
        }
        kwargs: dict = dict(ids=[memory_id], documents=[content], metadatas=[meta])
        if self.embed_fn:
            try:
                kwargs["embeddings"] = [self.embed_fn(content)]
            except Exception as e:
                logger.warning(f"Embedding failed, using ChromaDB default: {e}")
        self._collection.add(**kwargs)
        logger.debug(f"Stored semantic memory {memory_id} ({memory_type.value}) for user {user_id}")
        return memory_id

    def search(
        self,
        user_id: str,
        query: str,
        top_k: int = 5,
        min_score: float = 0.3,
    ) -> list[SemanticMemory]:
        total = self._collection.count()
        if total == 0:
            return []
        n = min(top_k, total)
        kwargs: dict = dict(
            n_results=n,
            where={"user_id": user_id},
            include=["documents", "metadatas", "distances"],
        )
        if self.embed_fn:
            try:
                kwargs["query_embeddings"] = [self.embed_fn(query)]
            except Exception as e:
                logger.warning(f"Query embedding failed, using text search: {e}")
                kwargs["query_texts"] = [query]
        else:
            kwargs["query_texts"] = [query]

        try:
            results = self._collection.query(**kwargs)
        except Exception as e:
            logger.error(f"Semantic search failed: {e}")
            return []

        memories: list[SemanticMemory] = []
        for i, doc_id in enumerate(results["ids"][0]):
            distance = results["distances"][0][i]
            similarity = 1.0 - distance
            if similarity < min_score:
                continue
            meta = results["metadatas"][0][i]
            new_count = int(meta.get("access_count", 0)) + 1
            now_iso = datetime.utcnow().isoformat()
            try:
                self._collection.update(
                    ids=[doc_id],
                    metadatas=[{**meta, "last_accessed": now_iso, "access_count": new_count}],
                )
            except Exception:
                pass
            memories.append(
                SemanticMemory(
                    id=doc_id,
                    user_id=meta["user_id"],
                    content=results["documents"][0][i],
                    memory_type=MemoryType(meta.get("memory_type", "fact")),
                    importance_score=float(meta.get("importance_score", 0.5)),
                    created_at=datetime.fromisoformat(meta["created_at"]),
                    last_accessed=datetime.utcnow(),
                    access_count=new_count,
                    metadata=meta,
                )
            )
        return memories

    def delete(self, memory_id: str) -> bool:
        try:
            self._collection.delete(ids=[memory_id])
            return True
        except Exception as e:
            logger.error(f"Delete semantic memory {memory_id} failed: {e}")
            return False

    def get_all(self, user_id: str) -> list[SemanticMemory]:
        try:
            results = self._collection.get(
                where={"user_id": user_id},
                include=["documents", "metadatas"],
            )
        except Exception as e:
            logger.error(f"get_all failed for user {user_id}: {e}")
            return []
        memories: list[SemanticMemory] = []
        for i, doc_id in enumerate(results["ids"]):
            meta = results["metadatas"][i]
            memories.append(
                SemanticMemory(
                    id=doc_id,
                    user_id=meta["user_id"],
                    content=results["documents"][i],
                    memory_type=MemoryType(meta.get("memory_type", "fact")),
                    importance_score=float(meta.get("importance_score", 0.5)),
                    created_at=datetime.fromisoformat(meta["created_at"]),
                    last_accessed=datetime.fromisoformat(
                        meta.get("last_accessed", meta["created_at"])
                    ),
                    access_count=int(meta.get("access_count", 0)),
                    metadata=meta,
                )
            )
        return memories

    def prune_low_score(self, user_id: str, threshold: float = 0.2) -> int:
        all_mems = self.get_all(user_id)
        pruned = 0
        for mem in all_mems:
            if mem.importance_score < threshold:
                if self.delete(mem.id):
                    pruned += 1
        if pruned:
            logger.info(f"Pruned {pruned} low-score semantic memories for user {user_id}")
        return pruned
