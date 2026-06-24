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

Implemented in Phase 2.
"""

from dataclasses import dataclass


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
        context = await orchestrator.get_context(user_id, query)
        # inject context into Qwen prompt
        await orchestrator.save_turn(user_id, user_msg, assistant_msg)
    """

    def __init__(
        self,
        working_memory,
        episodic_store,
        semantic_store,
        consolidation_pipeline,
        scorer,
        token_budget: int = 6000,
    ):
        self.working = working_memory
        self.episodic = episodic_store
        self.semantic = semantic_store
        self.consolidation = consolidation_pipeline
        self.scorer = scorer
        self.token_budget = token_budget

    async def get_context(self, user_id: str, query: str) -> MemoryContext:
        raise NotImplementedError("Implemented in Phase 2")

    async def save_turn(
        self, user_id: str, user_message: str, assistant_message: str
    ) -> None:
        raise NotImplementedError("Implemented in Phase 2")

    async def pack_memories_into_prompt(
        self, semantic_facts: list, episodic_summaries: list, budget: int
    ) -> tuple[list[str], int]:
        raise NotImplementedError("Implemented in Phase 2")

    async def trigger_consolidation_if_needed(self, user_id: str) -> None:
        raise NotImplementedError("Implemented in Phase 2")
