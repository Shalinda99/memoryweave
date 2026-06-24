"""
Memory Orchestrator

Unified interface that coordinates all three memory tiers:
  Tier 1: WorkingMemoryManager   (in-context, current session)
  Tier 2: EpisodicMemoryStore    (Redis TTL, recent sessions)
  Tier 3: SemanticMemoryStore    (ChromaDB vector, long-term)

The orchestrator is the single entry point for the MemoryAgent.
It handles:
  - Reading: retrieve relevant memories from all tiers before generating a response
  - Writing: save conversation turns to episodic memory after each response
  - Context packing: fit the best memories into the token budget
  - Triggering consolidation when episodic memory threshold is reached
"""

import asyncio
import logging
from dataclasses import dataclass

from memory.working import WorkingMemoryManager

logger = logging.getLogger("memoryweave.orchestrator")

CONSOLIDATION_THRESHOLD = 5  # trigger consolidation after N new episodic memories


@dataclass
class MemoryContext:
    working_messages: list[dict]
    episodic_summaries: list[str]
    semantic_facts: list[str]
    total_tokens_used: int
    memories_recalled: list[str]


class MemoryOrchestrator:
    """
    Central coordinator for MemoryWeave's three-tier memory system.

    Usage by MemoryAgent:
        context = await orchestrator.get_context(user_id, session_id, query)
        # inject context into Qwen prompt
        await orchestrator.save_turn(user_id, session_id, user_msg, assistant_msg)
    """

    def __init__(
        self,
        working_memory_cls,
        episodic_store,
        semantic_store,
        consolidation_pipeline,
        scorer,
        token_budget: int = 6000,
    ):
        self.working_memory_cls = working_memory_cls
        self.episodic = episodic_store
        self.semantic = semantic_store
        self.consolidation = consolidation_pipeline
        self.scorer = scorer
        self.token_budget = token_budget
        self._sessions: dict = {}

    def get_or_create_session(self, session_id: str):
        if session_id not in self._sessions:
            self._sessions[session_id] = self.working_memory_cls(
                max_tokens=self.token_budget // 2
            )
        return self._sessions[session_id]

    def clear_session(self, session_id: str) -> None:
        if session_id in self._sessions:
            del self._sessions[session_id]

    async def get_context(
        self, user_id: str, session_id: str, query: str
    ) -> MemoryContext:
        episodic_task = asyncio.create_task(
            self.episodic.retrieve(user_id, limit=5)
        )
        semantic_task = asyncio.to_thread(
            self.semantic.search, user_id, query, 5, 0.25
        )
        episodic_mems, semantic_mems = await asyncio.gather(
            episodic_task, semantic_task
        )

        raw_episodic = [m.summary for m in episodic_mems]
        raw_semantic = [m.content for m in semantic_mems]

        memory_budget = self.token_budget // 3
        packed_semantic, packed_episodic, tokens_used = await self.pack_memories_into_prompt(
            raw_semantic, raw_episodic, memory_budget
        )

        session = self.get_or_create_session(session_id)
        working_msgs = session.get_context()

        recalled = (
            [f"[semantic] {f}" for f in packed_semantic]
            + [f"[episodic] {e}" for e in packed_episodic]
        )

        return MemoryContext(
            working_messages=working_msgs,
            episodic_summaries=packed_episodic,
            semantic_facts=packed_semantic,
            total_tokens_used=tokens_used,
            memories_recalled=recalled,
        )

    async def save_turn(
        self,
        user_id: str,
        session_id: str,
        user_message: str,
        assistant_message: str,
    ) -> None:
        session = self.get_or_create_session(session_id)
        session.add_message("user", user_message)
        session.add_message("assistant", assistant_message)

        try:
            summary = await self.consolidation.summarize_turn(
                user_message, assistant_message
            )
            await self.episodic.store(user_id, summary, ttl_days=30)
            logger.debug(f"Saved episodic turn for user {user_id}")
        except Exception as e:
            logger.error(f"Failed to store episodic memory for {user_id}: {e}")

        await self.trigger_consolidation_if_needed(user_id)

    async def pack_memories_into_prompt(
        self,
        semantic_facts: list,
        episodic_summaries: list,
        budget: int,
    ) -> tuple[list[str], list[str], int]:
        """Fit memories into a token budget (4 chars ≈ 1 token). Returns (facts, episodes, tokens)."""
        packed_facts: list[str] = []
        packed_episodes: list[str] = []
        tokens_used = 0

        for fact in semantic_facts:
            t = max(1, len(fact) // 4)
            if tokens_used + t > budget:
                break
            packed_facts.append(fact)
            tokens_used += t

        for ep in episodic_summaries:
            t = max(1, len(ep) // 4)
            if tokens_used + t > budget:
                break
            packed_episodes.append(ep)
            tokens_used += t

        return packed_facts, packed_episodes, tokens_used

    async def trigger_consolidation_if_needed(self, user_id: str) -> None:
        try:
            count = await self.episodic.count(user_id)
            if count >= CONSOLIDATION_THRESHOLD:
                logger.info(
                    f"Triggering background consolidation for {user_id} ({count} episodic memories)"
                )
                asyncio.create_task(self.consolidation.run_for_user(user_id))
        except Exception as e:
            logger.error(f"Consolidation trigger failed for {user_id}: {e}")
