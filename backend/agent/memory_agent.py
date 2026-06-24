"""
MemoryWeave Agent

The main AI agent that combines Qwen reasoning with the three-tier memory system.
Each response is informed by relevant memories retrieved from all tiers.
After each turn, the conversation is saved to episodic memory.

Flow per turn:
  1. Retrieve context: semantic facts + episodic summaries + working messages
  2. Build system prompt injecting memory context
  3. Call qwen-max with memory-enriched prompt
  4. Save the turn to episodic memory
  5. Trigger consolidation if episodic memory threshold reached

Implemented in Phase 2.
"""

from dataclasses import dataclass


@dataclass
class AgentResponse:
    reply: str
    session_id: str
    user_id: str
    memories_used: list[str]
    tokens_used: int


class MemoryAgent:
    """
    Qwen-powered chat agent with persistent cross-session memory.

    This agent demonstrates Track 1 (MemoryAgent) requirements:
    - Persistent memory across multi-turn, cross-session interactions
    - Efficient memory storage and retrieval
    - Timely forgetting of outdated information
    - Critical memory recall within limited context windows
    """

    SYSTEM_PROMPT_TEMPLATE = """You are MemoryWeave, an AI assistant with persistent memory.

You remember the following facts about this user:
{semantic_facts}

Recent context from previous sessions:
{episodic_summaries}

Use this memory naturally in your responses. If you recall something relevant, 
mention it briefly (e.g. "As I remember, you prefer..."). 
Do not make up memories that aren't listed above."""

    def __init__(self, qwen_client, orchestrator):
        self.qwen = qwen_client
        self.orchestrator = orchestrator

    async def chat(
        self, user_id: str, message: str, session_id: str
    ) -> AgentResponse:
        raise NotImplementedError("Implemented in Phase 2")

    def _build_system_prompt(
        self, semantic_facts: list[str], episodic_summaries: list[str]
    ) -> str:
        raise NotImplementedError("Implemented in Phase 2")
