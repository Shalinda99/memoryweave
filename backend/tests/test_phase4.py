"""
MemoryWeave — Phase 4 API Integration Tests
Tests the two new Phase 4 endpoints: /timeline and /benchmark
Run from the project root:
    docker compose exec backend python tests/test_phase4.py
"""

import json
import sys
import urllib.request
import urllib.error
from datetime import datetime

BASE = "http://localhost:8000"
USER = "phase4-test-user"
SEP = "=" * 60


def _request(method: str, path: str, body: dict | None = None) -> dict:
    url = f"{BASE}{path}"
    data = json.dumps(body).encode() if body else None
    req = urllib.request.Request(
        url,
        data=data,
        method=method,
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read())


def get(path: str) -> dict:
    return _request("GET", path)


def post(path: str, body: dict) -> dict:
    return _request("POST", path, body)


def delete(path: str) -> dict:
    return _request("DELETE", path)


def ok(label: str) -> None:
    print(f"  \u2705 {label}")


def fail(label: str, reason: str) -> None:
    print(f"  \u274c {label}: {reason}")
    sys.exit(1)


def run_tests() -> None:
    print(SEP)
    print("  MemoryWeave \u2014 Phase 4 API Integration Tests")
    print(f"  Target: {BASE}")
    print(SEP)

    passed = 0

    # ── Test 1: Health check ──────────────────────────────────────────────────
    try:
        r = get("/api/v1/ping")
        assert "qwen_response" in r or "status" in r
        ok("Health check")
        passed += 1
    except Exception as e:
        fail("Health check", str(e))

    # ── Seed: send a chat message so memories exist ───────────────────────────
    try:
        post(
            "/api/v1/chat",
            {
                "user_id": USER,
                "message": "My name is Phase4 Tester and I love automated testing.",
                "session_id": "phase4-seed-session",
            },
        )
        ok("Seed chat message")
        passed += 1
    except Exception as e:
        fail("Seed chat message", str(e))

    # ── Test 2: Timeline endpoint returns correct shape ───────────────────────
    try:
        r = get(f"/api/v1/timeline/{USER}")
        assert "user_id" in r, "missing user_id"
        assert "total_events" in r, "missing total_events"
        assert "groups" in r, "missing groups"
        assert isinstance(r["groups"], list), "groups must be a list"
        assert isinstance(r["total_events"], int), "total_events must be int"
        ok("Timeline schema")
        passed += 1
    except Exception as e:
        fail("Timeline schema", str(e))

    # ── Test 3: Timeline groups are date-keyed ────────────────────────────────
    try:
        r = get(f"/api/v1/timeline/{USER}")
        for group in r["groups"]:
            assert "date" in group, "group missing date"
            assert "events" in group, "group missing events"
            assert "count" in group, "group missing count"
            assert isinstance(group["events"], list), "events must be list"
            datetime.fromisoformat(group["date"])
        ok("Timeline group structure")
        passed += 1
    except Exception as e:
        fail("Timeline group structure", str(e))

    # ── Test 4: Timeline event shape ─────────────────────────────────────────
    try:
        r = get(f"/api/v1/timeline/{USER}")
        if r["total_events"] > 0:
            evt = r["groups"][0]["events"][0]
            assert "id" in evt
            assert "type" in evt
            assert evt["type"] in ("semantic", "episodic")
            assert "memory_type" in evt
            assert "content" in evt
            assert "importance_score" in evt
            assert "access_count" in evt
            assert "timestamp" in evt
            assert "date" in evt
            datetime.fromisoformat(evt["timestamp"])
        ok("Timeline event shape")
        passed += 1
    except Exception as e:
        fail("Timeline event shape", str(e))

    # ── Test 5: Benchmark endpoint returns correct shape ──────────────────────
    try:
        r = get(f"/api/v1/benchmark/{USER}")
        assert "user_id" in r
        assert "total_memories" in r
        assert "baseline_accuracy" in r
        assert "memory_accuracy" in r
        assert "improvement_factor" in r
        assert "total_memory_accesses" in r
        assert "avg_importance_score" in r
        assert "sessions" in r
        ok("Benchmark schema")
        passed += 1
    except Exception as e:
        fail("Benchmark schema", str(e))

    # ── Test 6: Benchmark accuracy values are valid ───────────────────────────
    try:
        r = get(f"/api/v1/benchmark/{USER}")
        assert 0.0 <= r["baseline_accuracy"] <= 1.0, "baseline out of range"
        assert 0.0 <= r["memory_accuracy"] <= 1.0, "memory_accuracy out of range"
        assert r["improvement_factor"] >= 0, "improvement_factor negative"
        assert r["memory_accuracy"] >= r["baseline_accuracy"], \
            "memory_accuracy should be >= baseline"
        ok("Benchmark accuracy values valid")
        passed += 1
    except Exception as e:
        fail("Benchmark accuracy values valid", str(e))

    # ── Test 7: Benchmark sessions array ─────────────────────────────────────
    try:
        r = get(f"/api/v1/benchmark/{USER}")
        sessions = r["sessions"]
        assert isinstance(sessions, list) and len(sessions) >= 1
        s = sessions[0]
        assert "session" in s
        assert "baseline_recall" in s
        assert "memory_recall" in s
        assert "memories_available" in s
        assert 0.0 <= s["memory_recall"] <= 1.0
        ok("Benchmark sessions array")
        passed += 1
    except Exception as e:
        fail("Benchmark sessions array", str(e))

    # ── Test 8: Timeline for unknown user returns empty groups ────────────────
    try:
        r = get("/api/v1/timeline/no-such-user-xyz-999")
        assert r["total_events"] == 0
        assert r["groups"] == []
        ok("Timeline empty user")
        passed += 1
    except Exception as e:
        fail("Timeline empty user", str(e))

    # ── Test 9: Benchmark for unknown user returns safe defaults ─────────────
    try:
        r = get("/api/v1/benchmark/no-such-user-xyz-999")
        assert r["total_memories"] == 0
        assert r["baseline_accuracy"] >= 0
        assert r["memory_accuracy"] >= 0
        ok("Benchmark empty user defaults")
        passed += 1
    except Exception as e:
        fail("Benchmark empty user defaults", str(e))

    # ── Test 10: Cleanup ──────────────────────────────────────────────────────
    try:
        delete(f"/api/v1/memories/{USER}/all")
        ok("Cleanup test memories")
        passed += 1
    except Exception as e:
        fail("Cleanup test memories", str(e))

    print(SEP)
    print(f"  \u2705 All {passed} tests passed \u2014 Phase 4 complete!")
    print(SEP)


if __name__ == "__main__":
    run_tests()
