"""
MemoryWeave Dependency Initialization

Builds and wires all memory-system components:
  EpisodicMemoryStore → ConsolidationPipeline
  SemanticMemoryStore → ConsolidationPipeline
  MemoryScorer        → ConsolidationPipeline
  ConsolidationPipeline + WorkingMemoryManager → MemoryOrchestrator
  MemoryOrchestrator + QwenClient → MemoryAgent

Called once at FastAPI startup; the agent is stored on app.state.agent.
"""

import logging
from fastapi import FastAPI

from config import REDIS_URL, CHROMA_DB_PATH
from qwen_client import qwen
from memory.working import WorkingMemoryManager
from memory.episodic import EpisodicMemoryStore
from memory.semantic import SemanticMemoryStore
from memory.scoring import MemoryScorer
from memory.consolidation import ConsolidationPipeline
from memory.orchestrator import MemoryOrchestrator
from agent.memory_agent import MemoryAgent

logger = logging.getLogger("memoryweave.deps")


async def initialize_memory_system(app: FastAPI) -> MemoryAgent:
    """Initialize all memory components and attach the agent to app.state."""

    episodic_store = EpisodicMemoryStore(redis_url=REDIS_URL)
    await episodic_store.connect()
    logger.info("✅ EpisodicMemoryStore (Redis) connected")

    semantic_store = SemanticMemoryStore(
        chroma_path=CHROMA_DB_PATH,
        embed_fn=qwen.embed,
    )
    semantic_store.initialize()
    logger.info("✅ SemanticMemoryStore (ChromaDB) initialized")

    scorer = MemoryScorer()

    consolidation = ConsolidationPipeline(
        qwen_client=qwen,
        episodic_store=episodic_store,
        semantic_store=semantic_store,
        scorer=scorer,
    )

    orchestrator = MemoryOrchestrator(
        working_memory_cls=WorkingMemoryManager,
        episodic_store=episodic_store,
        semantic_store=semantic_store,
        consolidation_pipeline=consolidation,
        scorer=scorer,
        token_budget=6000,
    )

    agent = MemoryAgent(qwen_client=qwen, orchestrator=orchestrator)

    app.state.agent = agent
    logger.info("✅ MemoryAgent ready — three-tier memory system online")
    return agent
