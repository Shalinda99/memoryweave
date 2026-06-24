"""
Episodic Memory Store

Stores recent interactions across sessions using Redis with TTL-based expiry.
Memories decay naturally based on age and retrieval frequency.

Key schema:
  mw:episodic:{memory_id}          → Hash  (id, user_id, summary, created_at, ttl_days, retrieval_count, importance_score)
  mw:episodic_ids:{user_id}        → ZSet  (member=memory_id, score=unix_timestamp)
"""

import uuid
import logging
import redis.asyncio as aioredis
from dataclasses import dataclass
from datetime import datetime

logger = logging.getLogger("memoryweave.episodic")


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
        self._redis: aioredis.Redis | None = None

    async def connect(self) -> None:
        self._redis = await aioredis.from_url(
            self.redis_url, decode_responses=True, socket_connect_timeout=5
        )
        await self._redis.ping()
        logger.info("EpisodicMemoryStore connected to Redis")

    async def store(self, user_id: str, summary: str, ttl_days: int = 30) -> str:
        if not self._redis:
            raise RuntimeError("Redis not connected — call connect() first")
        memory_id = str(uuid.uuid4())
        now = datetime.utcnow()
        ttl_seconds = ttl_days * 86400
        key = f"mw:episodic:{memory_id}"
        data = {
            "id": memory_id,
            "user_id": user_id,
            "summary": summary,
            "created_at": now.isoformat(),
            "ttl_days": str(ttl_days),
            "retrieval_count": "0",
            "importance_score": "0.5",
        }
        async with self._redis.pipeline(transaction=True) as pipe:
            pipe.hset(key, mapping=data)
            pipe.expire(key, ttl_seconds)
            pipe.zadd(f"mw:episodic_ids:{user_id}", {memory_id: now.timestamp()})
            pipe.expire(f"mw:episodic_ids:{user_id}", ttl_seconds)
            await pipe.execute()
        logger.debug(f"Stored episodic memory {memory_id} for user {user_id}")
        return memory_id

    async def retrieve(self, user_id: str, limit: int = 10) -> list[EpisodicMemory]:
        if not self._redis:
            return []
        ids = await self._redis.zrevrange(f"mw:episodic_ids:{user_id}", 0, limit - 1)
        memories: list[EpisodicMemory] = []
        for mid in ids:
            data = await self._redis.hgetall(f"mw:episodic:{mid}")
            if not data:
                await self._redis.zrem(f"mw:episodic_ids:{user_id}", mid)
                continue
            await self._redis.hincrby(f"mw:episodic:{mid}", "retrieval_count", 1)
            memories.append(
                EpisodicMemory(
                    id=data["id"],
                    user_id=data["user_id"],
                    summary=data["summary"],
                    created_at=datetime.fromisoformat(data["created_at"]),
                    ttl_days=int(data.get("ttl_days", 30)),
                    retrieval_count=int(data.get("retrieval_count", 0)),
                    importance_score=float(data.get("importance_score", 0.5)),
                )
            )
        return memories

    async def delete(self, memory_id: str) -> bool:
        if not self._redis:
            return False
        data = await self._redis.hgetall(f"mw:episodic:{memory_id}")
        if not data:
            return False
        user_id = data.get("user_id", "")
        async with self._redis.pipeline(transaction=True) as pipe:
            pipe.delete(f"mw:episodic:{memory_id}")
            if user_id:
                pipe.zrem(f"mw:episodic_ids:{user_id}", memory_id)
            await pipe.execute()
        return True

    async def get_all_for_consolidation(self, user_id: str) -> list[EpisodicMemory]:
        """Return all episodic memories for a user (up to 200) for consolidation."""
        return await self.retrieve(user_id, limit=200)

    async def count(self, user_id: str) -> int:
        if not self._redis:
            return 0
        return await self._redis.zcard(f"mw:episodic_ids:{user_id}")
