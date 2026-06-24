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
"""

import uuid
import asyncio
import logging
from dataclasses import dataclass

logger = logging.getLogger("memoryweave.agent")


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

    SYSTEM_PROMPT_TEMPLATE = """You are MemoryWeave, an AI assistant with persistent cross-session memory.
You are powered by Alibaba Cloud Qwen.

{memory_section}

Guidelines:
- Use your memory naturally. If something you remember is relevant, weave it into your response naturally (e.g., "Since you prefer Python..." or "Last time we discussed...").
- Never fabricate memories. Only reference what appears above.
- Be helpful, concise, and personalized."""

    MEMORY_SECTION_WITH_DATA = """What you remember about this user:

Learned facts:
{semantic_facts}

Recent session context:
{episodic_summaries}"""

    MEMORY_SECTION_EMPTY = """This appears to be your first interaction with this user. No prior memories yet.
Get to know them through this conversation — their preferences and context will be remembered for future sessions."""

    def __init__(self, qwen_client, orchestrator):
        self.qwen = qwen_client
        self.orchestrator = orchestrator

    async def chat(
        self, user_id: str, message: str, session_id: str | None = None
    ) -> AgentResponse:
        session_id = session_id or str(uuid.uuid4())

        context = await self.orchestrator.get_context(user_id, session_id, message)

        system_prompt = self._build_system_prompt(
            context.semantic_facts, context.episodic_summaries
        )

        messages = [{"role": "system", "content": system_prompt}]
        for msg in context.working_messages:
            if msg["role"] != "system":
                messages.append(msg)
        messages.append({"role": "user", "content": message})

        try:
            reply = await asyncio.to_thread(
                self.qwen.chat,
                messages,
                None,
                0.7,
                None,
            )
        except Exception as e:
            logger.error(f"Qwen chat failed for user {user_id}: {e}")
            reply = "I'm sorry, I encountered an error processing your request. Please try again."

        asyncio.create_task(
            self.orchestrator.save_turn(user_id, session_id, message, reply)
        )

        tokens_approx = sum(len(m["content"]) // 4 for m in messages) + len(reply) // 4

        return AgentResponse(
            reply=reply,
            session_id=session_id,
            user_id=user_id,
            memories_used=context.memories_recalled,
            tokens_used=tokens_approx,
        )

    def _build_system_prompt(
        self, semantic_facts: list[str], episodic_summaries: list[str]
    ) -> str:
        if not semantic_facts and not episodic_summaries:
            memory_section = self.MEMORY_SECTION_EMPTY
        else:
            facts_text = (
                "\n".join(f"  • {f}" for f in semantic_facts)
                if semantic_facts
                else "  (none yet)"
            )
            episodes_text = (
                "\n".join(f"  • {e}" for e in episodic_summaries)
                if episodic_summaries
                else "  (none yet)"
            )
            memory_section = self.MEMORY_SECTION_WITH_DATA.format(
                semantic_facts=facts_text,
                episodic_summaries=episodes_text,
            )
        return self.SYSTEM_PROMPT_TEMPLATE.format(memory_section=memory_section)
