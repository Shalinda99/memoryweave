"""
Memory Consolidation Pipeline

Uses Qwen-Long to summarize episodic memories and extract key facts
for promotion into the semantic (long-term) memory store.

Pipeline steps:
  1. Fetch all episodic memories for a user
  2. Use qwen-long to summarize them into structured facts
  3. Check each fact against existing semantic memories (contradiction detection)
  4. Store new/updated facts in SemanticMemoryStore
  5. Delete consolidated episodic memories
  6. Score and prune low-value semantic memories
"""

import json
import asyncio
import logging
from dataclasses import dataclass

logger = logging.getLogger("memoryweave.consolidation")


@dataclass
class ConsolidationResult:
    user_id: str
    episodic_processed: int
    facts_extracted: int
    facts_stored: int
    contradictions_resolved: int
    memories_pruned: int


class ConsolidationPipeline:
    """
    Qwen-powered pipeline that converts episodic memories into semantic facts.

    This is the core innovation of MemoryWeave:
    - Runs periodically (via background task)
    - Uses qwen-long for large-context summarization
    - Uses qwen-turbo for fast contradiction detection
    - Uses text-embedding-v3 for semantic deduplication
    """

    EXTRACT_FACTS_PROMPT = """You are analyzing conversation memories to build a persistent user profile.
Extract durable facts from these session summaries.

Return a JSON array of facts. Each fact object must have:
- "content": concise fact string (1-2 sentences max)
- "memory_type": one of "preference", "fact", "skill", "relationship"
- "importance_score": float 0.0-1.0 (how durable/important this fact is)

Only include facts that will likely remain true across future sessions.
Ignore transient details (e.g., "user asked about weather today").

Session summaries:
{summaries}

Return ONLY a valid JSON array, no markdown, no explanation."""

    CONTRADICTION_PROMPT = """Does the NEW FACT contradict any EXISTING FACT?

NEW FACT: {new_fact}

EXISTING FACTS:
{existing_facts}

Reply with valid JSON only:
{{"contradicts": true or false, "contradicting_fact": "exact matching fact text or null"}}"""

    RESOLVE_PROMPT = """Two facts about the same user contradict. Produce one resolved fact.
Prefer the newer/more specific one or merge them if both are valid.

OLD FACT: {old_fact}
NEW FACT: {new_fact}

Reply with only the resolved fact text (1-2 sentences). No explanation."""

    SUMMARIZE_TURN_PROMPT = """Summarize this single conversation exchange in 1-2 sentences.
Capture key user information: preferences, goals, facts, context useful in future sessions.
Ignore generic pleasantries.

User: {user_message}
Assistant: {assistant_message}

Summary:"""

    def __init__(self, qwen_client, episodic_store, semantic_store, scorer):
        self.qwen = qwen_client
        self.episodic = episodic_store
        self.semantic = semantic_store
        self.scorer = scorer

    async def run_for_user(self, user_id: str) -> ConsolidationResult:
        logger.info(f"Starting consolidation for user {user_id}")
        episodic_memories = await self.episodic.get_all_for_consolidation(user_id)
        if not episodic_memories:
            return ConsolidationResult(
                user_id=user_id,
                episodic_processed=0,
                facts_extracted=0,
                facts_stored=0,
                contradictions_resolved=0,
                memories_pruned=0,
            )

        summaries = [m.summary for m in episodic_memories]
        facts = await self.extract_facts(summaries)

        existing_mems = await asyncio.to_thread(self.semantic.get_all, user_id)
        existing_facts = [m.content for m in existing_mems]

        facts_stored = 0
        contradictions_resolved = 0

        from memory.semantic import MemoryType

        for fact in facts:
            content = fact.get("content", "").strip()
            if not content:
                continue

            if existing_facts:
                contradiction = await self.detect_contradiction(content, existing_facts)
                if contradiction.get("contradicts") and contradiction.get("contradicting_fact"):
                    old_fact = contradiction["contradicting_fact"]
                    content = await self.resolve_contradiction(content, old_fact)
                    contradictions_resolved += 1

            mem_type_str = fact.get("memory_type", "fact")
            try:
                mem_type = MemoryType(mem_type_str)
            except ValueError:
                mem_type = MemoryType.FACT

            importance = float(fact.get("importance_score", 0.5))
            await asyncio.to_thread(
                self.semantic.store, user_id, content, mem_type, importance
            )
            facts_stored += 1

        for mem in episodic_memories:
            await self.episodic.delete(mem.id)

        memories_pruned = await asyncio.to_thread(
            self.semantic.prune_low_score, user_id, 0.15
        )

        logger.info(
            f"Consolidation done for {user_id}: "
            f"{len(episodic_memories)} episodic → {facts_stored} facts stored, "
            f"{contradictions_resolved} resolved, {memories_pruned} pruned"
        )
        return ConsolidationResult(
            user_id=user_id,
            episodic_processed=len(episodic_memories),
            facts_extracted=len(facts),
            facts_stored=facts_stored,
            contradictions_resolved=contradictions_resolved,
            memories_pruned=memories_pruned,
        )

    async def extract_facts(self, summaries: list[str]) -> list[dict]:
        prompt = self.EXTRACT_FACTS_PROMPT.format(
            summaries="\n".join(f"- {s}" for s in summaries)
        )
        try:
            response = await asyncio.to_thread(
                self.qwen.chat_long,
                [{"role": "user", "content": prompt}],
            )
            raw = response.strip()
            if raw.startswith("```"):
                parts = raw.split("```")
                raw = parts[1] if len(parts) > 1 else raw
                if raw.startswith("json"):
                    raw = raw[4:].strip()
            return json.loads(raw)
        except Exception as e:
            logger.error(f"extract_facts failed: {e}")
            return []

    async def detect_contradiction(
        self, new_fact: str, existing_facts: list[str]
    ) -> dict:
        if not existing_facts:
            return {"contradicts": False, "contradicting_fact": None}
        prompt = self.CONTRADICTION_PROMPT.format(
            new_fact=new_fact,
            existing_facts="\n".join(f"- {f}" for f in existing_facts[:20]),
        )
        try:
            response = await asyncio.to_thread(
                self.qwen.chat_fast,
                [{"role": "user", "content": prompt}],
            )
            raw = response.strip()
            if raw.startswith("```"):
                parts = raw.split("```")
                raw = parts[1] if len(parts) > 1 else raw
                if raw.startswith("json"):
                    raw = raw[4:].strip()
            return json.loads(raw)
        except Exception as e:
            logger.warning(f"detect_contradiction failed: {e}")
            return {"contradicts": False, "contradicting_fact": None}

    async def resolve_contradiction(self, new_fact: str, old_fact: str) -> str:
        prompt = self.RESOLVE_PROMPT.format(old_fact=old_fact, new_fact=new_fact)
        try:
            response = await asyncio.to_thread(
                self.qwen.chat_fast,
                [{"role": "user", "content": prompt}],
            )
            return response.strip() or new_fact
        except Exception as e:
            logger.warning(f"resolve_contradiction failed: {e}")
            return new_fact

    async def summarize_turn(self, user_message: str, assistant_message: str) -> str:
        """Summarize a single conversation turn into an episodic memory string."""
        prompt = self.SUMMARIZE_TURN_PROMPT.format(
            user_message=user_message[:2000],
            assistant_message=assistant_message[:2000],
        )
        try:
            response = await asyncio.to_thread(
                self.qwen.chat_fast,
                [{"role": "user", "content": prompt}],
            )
            return response.strip()
        except Exception as e:
            logger.error(f"summarize_turn failed: {e}")
            return f"User: {user_message[:100]}…"
