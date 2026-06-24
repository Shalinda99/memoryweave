"""
Phase 1 Connection Tests

Run this to verify all services are connected before starting Phase 2.

Usage:
    docker compose exec backend python tests/test_connection.py
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import DASHSCOPE_API_KEY, REDIS_URL


def test_qwen_connection():
    print("Testing Qwen Cloud (Alibaba Cloud DashScope)...")
    if not DASHSCOPE_API_KEY:
        print("❌ DASHSCOPE_API_KEY is not set in .env")
        return False

    from qwen_client import qwen
    response = qwen.chat([
        {"role": "user", "content": "Reply with exactly three words: MemoryWeave is online"}
    ])
    if response:
        print(f"✅ Qwen Cloud connected | Response: {response}")
        return True
    else:
        print("❌ Qwen returned empty response")
        return False


def test_qwen_embedding():
    print("Testing Qwen text-embedding-v3...")
    from qwen_client import qwen
    embedding = qwen.embed("test memory embedding")
    if embedding and len(embedding) > 0:
        print(f"✅ Qwen embeddings working | Dimensions: {len(embedding)}")
        return True
    else:
        print("❌ Qwen embeddings failed")
        return False


def test_redis_connection():
    print("Testing Redis...")
    import redis
    try:
        r = redis.from_url(REDIS_URL, decode_responses=True)
        r.ping()
        r.set("memoryweave:test", "phase1_ok", ex=60)
        value = r.get("memoryweave:test")
        if value == "phase1_ok":
            print(f"✅ Redis connected | URL: {REDIS_URL}")
            return True
        else:
            print("❌ Redis read/write failed")
            return False
    except Exception as e:
        print(f"❌ Redis connection failed: {e}")
        return False


if __name__ == "__main__":
    print("=" * 50)
    print("  MemoryWeave — Phase 1 Connection Tests")
    print("=" * 50)

    results = []
    results.append(test_qwen_connection())
    results.append(test_qwen_embedding())
    results.append(test_redis_connection())

    print("=" * 50)
    passed = sum(results)
    total = len(results)
    if passed == total:
        print(f"✅ All {total} tests passed — Phase 1 complete!")
    else:
        print(f"⚠️  {passed}/{total} tests passed — fix issues above before Phase 2")
    print("=" * 50)
