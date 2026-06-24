"""
Phase 3 — API Integration & Dashboard Tests

Tests the HTTP API endpoints that back the React dashboard:
  - GET  /api/v1/metrics/{user_id}
  - GET  /api/v1/export/{user_id}
  - GET  /api/v1/stats/{user_id}
  - POST /api/v1/chat
  - GET  /api/v1/memories/{user_id}
  - POST /api/v1/consolidate/{user_id}
  - DELETE /api/v1/memories/{user_id}/all

Run with the stack up:
    docker compose exec backend python tests/test_phase3.py

Or locally (Redis on :6379, API on :8000):
    cd backend && python tests/test_phase3.py
"""

import sys
import os
import asyncio
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")


# ── HTTP helper ───────────────────────────────────────────────────────────────

async def http_get(path: str) -> dict:
    import httpx
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=30) as client:
        r = await client.get(path)
        r.raise_for_status()
        return r.json()


async def http_post(path: str, body: dict) -> dict:
    import httpx
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=60) as client:
        r = await client.post(path, json=body)
        r.raise_for_status()
        return r.json()


async def http_delete(path: str) -> dict:
    import httpx
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=30) as client:
        r = await client.delete(path)
        r.raise_for_status()
        return r.json()


# ── Tests ─────────────────────────────────────────────────────────────────────

async def test_health():
    print("\n[Health Check]")
    data = await http_get("/health")
    assert data.get("status") == "healthy", f"Expected healthy, got {data}"
    print(f"  Status: {data['status']}")
    print("  ✅ /health OK")


async def test_ping():
    print("\n[Qwen Cloud Ping]")
    data = await http_get("/api/v1/ping")
    assert data.get("status") == "connected", f"Expected connected, got {data}"
    assert "qwen_response" in data
    print(f"  Qwen response  : {data['qwen_response'][:60]}")
    print(f"  Model          : {data.get('model', 'unknown')}")
    print("  ✅ /api/v1/ping OK")


async def test_chat_endpoint():
    print("\n[Chat Endpoint]")
    user_id = "phase3_test_chat_user"

    body = {
        "user_id": user_id,
        "message": "Hi! I'm a data scientist who loves Python and uses pandas daily.",
        "session_id": "phase3-test-session",
    }
    data = await http_post("/api/v1/chat", body)

    assert "reply" in data, "No reply field"
    assert data["user_id"] == user_id
    assert data["session_id"] == "phase3-test-session"
    assert isinstance(data["memories_used"], list)
    assert isinstance(data["tokens_used"], int)
    print(f"  Reply (first 80 chars) : {data['reply'][:80]}…")
    print(f"  Session ID             : {data['session_id']}")
    print(f"  Memories used          : {len(data['memories_used'])}")
    print(f"  Tokens used            : {data['tokens_used']}")
    print("  ✅ /api/v1/chat OK")

    return user_id


async def test_memories_endpoint(user_id: str):
    print("\n[Memories Endpoint]")
    data = await http_get(f"/api/v1/memories/{user_id}")

    assert "user_id" in data
    assert data["user_id"] == user_id
    assert isinstance(data["semantic"], list)
    assert isinstance(data["episodic"], list)
    assert "total" in data
    print(f"  Semantic memories : {len(data['semantic'])}")
    print(f"  Episodic memories : {len(data['episodic'])}")
    print(f"  Total             : {data['total']}")

    if data["episodic"]:
        ep = data["episodic"][0]
        assert "id" in ep
        assert "content" in ep
        assert "importance_score" in ep
        assert "tier" in ep
        print(f"  Sample episodic   : {ep['content'][:60]}…")

    print("  ✅ /api/v1/memories/{user_id} OK")


async def test_stats_endpoint(user_id: str):
    print("\n[Stats Endpoint]")
    data = await http_get(f"/api/v1/stats/{user_id}")

    assert "semantic_memories" in data
    assert "episodic_memories" in data
    assert "active_sessions" in data
    print(f"  Semantic  : {data['semantic_memories']}")
    print(f"  Episodic  : {data['episodic_memories']}")
    print(f"  Sessions  : {data['active_sessions']}")
    print("  ✅ /api/v1/stats/{user_id} OK")


async def test_metrics_endpoint(user_id: str):
    print("\n[Metrics Endpoint — Phase 3]")
    data = await http_get(f"/api/v1/metrics/{user_id}")

    required_keys = [
        "user_id", "semantic_memories", "episodic_memories",
        "avg_health_score", "prune_candidates", "memory_type_breakdown",
        "active_sessions", "top_memories",
    ]
    for key in required_keys:
        assert key in data, f"Missing key: {key}"

    assert data["user_id"] == user_id
    assert isinstance(data["avg_health_score"], float)
    assert 0.0 <= data["avg_health_score"] <= 1.0
    assert isinstance(data["memory_type_breakdown"], dict)
    assert isinstance(data["top_memories"], list)

    td = data["memory_type_breakdown"]
    for expected_type in ["preference", "fact", "skill", "relationship"]:
        assert expected_type in td, f"Missing type key: {expected_type}"

    print(f"  Semantic memories : {data['semantic_memories']}")
    print(f"  Episodic memories : {data['episodic_memories']}")
    print(f"  Avg health score  : {data['avg_health_score']:.4f}")
    print(f"  Prune candidates  : {data['prune_candidates']}")
    print(f"  Type breakdown    : {data['memory_type_breakdown']}")
    print(f"  Top memories      : {len(data['top_memories'])} items")
    print("  ✅ /api/v1/metrics/{user_id} OK")


async def test_export_endpoint(user_id: str):
    print("\n[Export Endpoint — Phase 3]")
    data = await http_get(f"/api/v1/export/{user_id}")

    assert "user_id" in data
    assert "exported_at" in data
    assert "semantic" in data
    assert "episodic" in data
    assert isinstance(data["semantic"], list)
    assert isinstance(data["episodic"], list)

    json_str = json.dumps(data)
    assert len(json_str) > 10
    print(f"  User ID        : {data['user_id']}")
    print(f"  Exported at    : {data['exported_at']}")
    print(f"  Semantic count : {len(data['semantic'])}")
    print(f"  Episodic count : {len(data['episodic'])}")

    if data["semantic"]:
        s = data["semantic"][0]
        assert "content" in s
        assert "memory_type" in s
        assert "importance_score" in s
        assert "created_at" in s
        assert "last_accessed" in s
        assert "access_count" in s

    if data["episodic"]:
        e = data["episodic"][0]
        assert "summary" in e
        assert "created_at" in e
        assert "importance_score" in e
        assert "retrieval_count" in e

    print("  ✅ /api/v1/export/{user_id} OK")


async def test_consolidate_endpoint(user_id: str):
    print("\n[Consolidate Endpoint]")
    data = await http_post(f"/api/v1/consolidate/{user_id}", {})

    required = [
        "user_id", "episodic_processed", "facts_extracted",
        "facts_stored", "contradictions_resolved", "memories_pruned",
    ]
    for key in required:
        assert key in data, f"Missing key: {key}"

    assert data["user_id"] == user_id
    print(f"  Episodic processed       : {data['episodic_processed']}")
    print(f"  Facts extracted          : {data['facts_extracted']}")
    print(f"  Facts stored             : {data['facts_stored']}")
    print(f"  Contradictions resolved  : {data['contradictions_resolved']}")
    print(f"  Memories pruned          : {data['memories_pruned']}")
    print("  ✅ /api/v1/consolidate/{user_id} OK")


async def test_delete_all_memories(user_id: str):
    print("\n[Delete All Memories]")
    data = await http_delete(f"/api/v1/memories/{user_id}/all")

    assert "semantic_deleted" in data
    assert "episodic_deleted" in data
    print(f"  Semantic deleted : {data['semantic_deleted']}")
    print(f"  Episodic deleted : {data['episodic_deleted']}")

    after = await http_get(f"/api/v1/memories/{user_id}")
    assert after["total"] == 0, f"Expected 0 after delete all, got {after['total']}"
    print("  Verified: memories cleared to 0")
    print("  ✅ DELETE /api/v1/memories/{user_id}/all OK")


async def test_metrics_schema_completeness():
    """Verify metrics response has the exact shape the dashboard expects."""
    print("\n[Metrics Schema Completeness]")
    user_id = "phase3_schema_test_user"

    await http_post("/api/v1/chat", {
        "user_id": user_id,
        "message": "I prefer dark mode and work in Go.",
    })

    data = await http_get(f"/api/v1/metrics/{user_id}")

    assert isinstance(data["top_memories"], list)
    if data["top_memories"]:
        mem = data["top_memories"][0]
        for f in ["id", "content", "memory_type", "importance_score", "access_count"]:
            assert f in mem, f"top_memories item missing field: {f}"

    td = data["memory_type_breakdown"]
    assert sum(td.values()) == data["semantic_memories"], (
        "type_breakdown sum should equal semantic_memories"
    )
    print("  Schema validation passed")

    await http_delete(f"/api/v1/memories/{user_id}/all")
    print("  Cleaned up")
    print("  ✅ Metrics schema completeness OK")


# ── Runner ────────────────────────────────────────────────────────────────────

async def run_all():
    results: list[tuple[str, bool]] = []

    async def run(name: str, coro):
        try:
            result = await coro
            results.append((name, True))
            return result
        except Exception as exc:
            import traceback
            print(f"  ❌ {name} FAILED: {exc}")
            traceback.print_exc()
            results.append((name, False))
            return None

    print("=" * 60)
    print("  MemoryWeave — Phase 3 API Integration Tests")
    print(f"  Target: {BASE_URL}")
    print("=" * 60)

    await run("Health Check",      test_health())
    await run("Qwen Cloud Ping",   test_ping())

    user_id = await run("Chat Endpoint",    test_chat_endpoint())
    if user_id:
        await run("Memories Endpoint",  test_memories_endpoint(user_id))
        await run("Stats Endpoint",     test_stats_endpoint(user_id))
        await run("Metrics Endpoint",   test_metrics_endpoint(user_id))
        await run("Export Endpoint",    test_export_endpoint(user_id))
        await run("Consolidate",        test_consolidate_endpoint(user_id))
        await run("Delete All",         test_delete_all_memories(user_id))

    await run("Metrics Schema", test_metrics_schema_completeness())

    print("\n" + "=" * 60)
    passed = sum(1 for _, ok in results if ok)
    total = len(results)
    for name, ok in results:
        icon = "✅" if ok else "❌"
        print(f"  {icon} {name}")
    print("=" * 60)
    if passed == total:
        print(f"  ✅ All {total} tests passed — Phase 3 complete!")
    else:
        print(f"  ⚠️  {passed}/{total} tests passed")
    print("=" * 60)
    return passed == total


if __name__ == "__main__":
    success = asyncio.run(run_all())
    sys.exit(0 if success else 1)
