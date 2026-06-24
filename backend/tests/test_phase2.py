"""
Phase 2 — Core Memory System Tests

Covers all three memory tiers, the orchestrator, and the agent.

Usage (inside the container):
    docker compose exec backend python tests/test_phase2.py

Or locally (with Redis running on localhost:6379):
    cd backend && python tests/test_phase2.py
"""

import sys
import os
import asyncio
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# ─── Tier-0: Scoring ─────────────────────────────────────────────────────────

def test_memory_scorer():
    print("\n[MemoryScorer]")
    from memory.scoring import MemoryScorer

    scorer = MemoryScorer()

    # Fresh memory with high access — should score high
    score_high = scorer.score(
        memory_id="m1",
        last_accessed=datetime.utcnow(),
        access_count=20,
        importance_score=0.9,
    )
    print(f"  High-value score : {score_high.final_score:.4f}  (expect > 0.5)")
    assert score_high.final_score > 0.5, "High-value memory scored too low"
    assert not score_high.should_prune

    # Ancient memory with zero access — should score low
    score_low = scorer.score(
        memory_id="m2",
        last_accessed=datetime.utcnow() - timedelta(days=90),
        access_count=0,
        importance_score=0.05,
    )
    print(f"  Low-value score  : {score_low.final_score:.4f}  (expect < 0.2)")
    assert score_low.final_score < 0.2, "Stale memory scored too high"
    assert score_low.should_prune

    # batch_score
    batch = scorer.batch_score([
        {"id": "b1", "last_accessed": datetime.utcnow(), "access_count": 5, "importance_score": 0.7},
        {"id": "b2", "last_accessed": datetime.utcnow() - timedelta(days=30), "access_count": 1, "importance_score": 0.3},
    ])
    assert len(batch) == 2
    print(f"  batch_score OK   : {[s.final_score for s in batch]}")
    print("  ✅ MemoryScorer passed")


# ─── Tier-1: Working Memory ───────────────────────────────────────────────────

def test_working_memory():
    print("\n[WorkingMemoryManager]")
    from memory.working import WorkingMemoryManager

    wm = WorkingMemoryManager(max_tokens=200)
    wm.set_system_prompt("You are MemoryWeave.")

    wm.add_message("user", "Hello!")
    wm.add_message("assistant", "Hi there!")
    wm.add_message("user", "What can you do?")
    wm.add_message("assistant", "I remember things across sessions.")

    ctx = wm.get_context()
    assert ctx[0]["role"] == "system"
    assert any(m["role"] == "user" for m in ctx)
    print(f"  Context length   : {len(ctx)} messages")
    print(f"  Turn count       : {wm.turn_count}")

    # Token budget enforcement — add many long messages
    wm2 = WorkingMemoryManager(max_tokens=50)
    for i in range(20):
        wm2.add_message("user", f"This is message number {i} with some content to fill tokens.")
        wm2.add_message("assistant", f"Acknowledged message {i}.")
    assert wm2._total_tokens() <= wm2.max_tokens * 1.1, "Token budget exceeded"
    print(f"  Budget enforcement: {wm2._total_tokens()} tokens (budget={wm2.max_tokens})")

    wm.clear()
    assert wm.messages == []
    print("  ✅ WorkingMemoryManager passed")


# ─── Tier-2: Episodic Memory ──────────────────────────────────────────────────

async def test_episodic_memory():
    print("\n[EpisodicMemoryStore]")
    from config import REDIS_URL
    from memory.episodic import EpisodicMemoryStore

    store = EpisodicMemoryStore(redis_url=REDIS_URL)
    await store.connect()
    print("  Connected to Redis")

    user_id = "test_phase2_episodic_user"

    mid1 = await store.store(user_id, "User asked about Python decorators. Explained with examples.", ttl_days=1)
    mid2 = await store.store(user_id, "User prefers dark mode. Showed dark mode demo.", ttl_days=1)
    print(f"  Stored 2 memories: {mid1[:8]}…, {mid2[:8]}…")

    count = await store.count(user_id)
    assert count >= 2, f"Expected >= 2, got {count}"
    print(f"  Count: {count}")

    memories = await store.retrieve(user_id, limit=10)
    assert len(memories) >= 2
    assert all(m.user_id == user_id for m in memories)
    print(f"  Retrieved {len(memories)} memories")
    print(f"  First summary    : {memories[0].summary[:60]}…")

    ok = await store.delete(mid1)
    assert ok, "Delete returned False"
    ok2 = await store.delete(mid2)
    assert ok2
    print("  Deleted test memories")
    print("  ✅ EpisodicMemoryStore passed")


# ─── Tier-3: Semantic Memory ──────────────────────────────────────────────────

def test_semantic_memory():
    print("\n[SemanticMemoryStore]")
    from config import CHROMA_DB_PATH
    from memory.semantic import SemanticMemoryStore, MemoryType
    from qwen_client import qwen

    store = SemanticMemoryStore(chroma_path=CHROMA_DB_PATH, embed_fn=qwen.embed)
    store.initialize()
    print("  ChromaDB initialized")

    user_id = "test_phase2_semantic_user"

    mid = store.store(user_id, "User is an expert Python developer who prefers functional programming.", MemoryType.PREFERENCE, 0.85)
    print(f"  Stored memory    : {mid[:8]}…")

    results = store.search(user_id, "programming language preferences", top_k=3, min_score=0.1)
    print(f"  Search results   : {len(results)} (min_score=0.1)")
    assert len(results) >= 1, "Expected at least 1 result after storing"
    print(f"  Top result       : {results[0].content[:60]}…")
    print(f"  Similarity score : {1.0 - 0.0:.2f} (approximate)")

    all_mems = store.get_all(user_id)
    assert any(m.id == mid for m in all_mems)
    print(f"  get_all count    : {len(all_mems)}")

    ok = store.delete(mid)
    assert ok, "Delete returned False"
    print("  Deleted test memory")
    print("  ✅ SemanticMemoryStore passed")


# ─── Consolidation Pipeline ───────────────────────────────────────────────────

async def test_consolidation_pipeline():
    print("\n[ConsolidationPipeline — extract_facts]")
    from config import REDIS_URL, CHROMA_DB_PATH
    from memory.episodic import EpisodicMemoryStore
    from memory.semantic import SemanticMemoryStore, MemoryType
    from memory.scoring import MemoryScorer
    from memory.consolidation import ConsolidationPipeline
    from qwen_client import qwen

    episodic = EpisodicMemoryStore(redis_url=REDIS_URL)
    await episodic.connect()

    semantic = SemanticMemoryStore(chroma_path=CHROMA_DB_PATH, embed_fn=qwen.embed)
    semantic.initialize()

    scorer = MemoryScorer()
    pipeline = ConsolidationPipeline(
        qwen_client=qwen,
        episodic_store=episodic,
        semantic_store=semantic,
        scorer=scorer,
    )

    summaries = [
        "User mentioned they work as a data scientist at a tech startup.",
        "User asked for Python tips. They use pandas and scikit-learn daily.",
        "User prefers concise explanations with code examples.",
    ]
    facts = await pipeline.extract_facts(summaries)
    print(f"  Extracted {len(facts)} facts from 3 summaries")
    for f in facts:
        print(f"  • [{f.get('memory_type','?')}] {f.get('content','')[:70]}…")
    assert isinstance(facts, list), "extract_facts should return a list"
    print("  ✅ ConsolidationPipeline.extract_facts passed")


# ─── Full Agent Flow ──────────────────────────────────────────────────────────

async def test_memory_agent_chat():
    print("\n[MemoryAgent — full chat flow]")
    from config import REDIS_URL, CHROMA_DB_PATH
    from memory.episodic import EpisodicMemoryStore
    from memory.semantic import SemanticMemoryStore
    from memory.scoring import MemoryScorer
    from memory.consolidation import ConsolidationPipeline
    from memory.orchestrator import MemoryOrchestrator
    from memory.working import WorkingMemoryManager
    from agent.memory_agent import MemoryAgent
    from qwen_client import qwen

    episodic = EpisodicMemoryStore(redis_url=REDIS_URL)
    await episodic.connect()

    semantic = SemanticMemoryStore(chroma_path=CHROMA_DB_PATH, embed_fn=qwen.embed)
    semantic.initialize()

    scorer = MemoryScorer()
    consolidation = ConsolidationPipeline(qwen, episodic, semantic, scorer)
    orchestrator = MemoryOrchestrator(
        working_memory_cls=WorkingMemoryManager,
        episodic_store=episodic,
        semantic_store=semantic,
        consolidation_pipeline=consolidation,
        scorer=scorer,
        token_budget=6000,
    )
    agent = MemoryAgent(qwen_client=qwen, orchestrator=orchestrator)

    user_id = "test_phase2_agent_user"
    session_id = "test-session-phase2-001"

    # Turn 1
    r1 = await agent.chat(user_id=user_id, message="Hi! I'm Alice, a Python developer.", session_id=session_id)
    print(f"  Turn 1 reply     : {r1.reply[:80]}…")
    assert r1.reply, "Empty reply on turn 1"
    assert r1.session_id == session_id

    # Turn 2 — should have turn 1 in working memory
    r2 = await agent.chat(user_id=user_id, message="What did I just tell you about myself?", session_id=session_id)
    print(f"  Turn 2 reply     : {r2.reply[:80]}…")
    assert r2.reply, "Empty reply on turn 2"
    print(f"  Memories used    : {len(r2.memories_used)}")
    print(f"  Tokens used      : {r2.tokens_used}")

    # Verify episodic memory was saved
    episodic_mems = await episodic.retrieve(user_id, limit=10)
    print(f"  Episodic saved   : {len(episodic_mems)} memories")
    assert len(episodic_mems) >= 1, "No episodic memories saved after chat"

    # Cleanup
    for m in episodic_mems:
        await episodic.delete(m.id)
    print("  Cleaned up test memories")
    print("  ✅ MemoryAgent.chat passed")


# ─── Runner ───────────────────────────────────────────────────────────────────

def run(name: str, fn, results: list):
    try:
        if asyncio.iscoroutinefunction(fn):
            asyncio.run(fn())
        else:
            fn()
        results.append((name, True))
    except Exception as exc:
        import traceback
        print(f"  ❌ {name} FAILED: {exc}")
        traceback.print_exc()
        results.append((name, False))


if __name__ == "__main__":
    print("=" * 60)
    print("  MemoryWeave — Phase 2 Core Memory Tests")
    print("=" * 60)

    results: list[tuple[str, bool]] = []

    run("MemoryScorer",            test_memory_scorer,           results)
    run("WorkingMemoryManager",    test_working_memory,          results)
    run("EpisodicMemoryStore",     test_episodic_memory,         results)
    run("SemanticMemoryStore",     test_semantic_memory,         results)
    run("ConsolidationPipeline",   test_consolidation_pipeline,  results)
    run("MemoryAgent (full flow)", test_memory_agent_chat,       results)

    print("\n" + "=" * 60)
    passed = sum(1 for _, ok in results if ok)
    total  = len(results)
    for name, ok in results:
        icon = "✅" if ok else "❌"
        print(f"  {icon} {name}")
    print("=" * 60)
    if passed == total:
        print(f"  ✅ All {total} tests passed — Phase 2 complete!")
    else:
        print(f"  ⚠️  {passed}/{total} tests passed — fix failures above before Phase 3")
    print("=" * 60)
    sys.exit(0 if passed == total else 1)
