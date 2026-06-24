# MemoryWeave

> Persistent hierarchical memory for Qwen-powered AI assistants

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](./LICENSE)
[![Python 3.11](https://img.shields.io/badge/python-3.11-blue.svg)](https://www.python.org/)
[![Powered by Qwen](https://img.shields.io/badge/Powered%20by-Qwen%20Cloud-orange.svg)](https://qwencloud.com)
[![Track](https://img.shields.io/badge/Track-1%20MemoryAgent-green.svg)](https://qwencloud-hackathon.devpost.com)

**Global AI Hackathon Series with Qwen Cloud — Track 1: MemoryAgent**

---

## The Problem

Every AI assistant forgets you the moment you close the tab. Users have to re-introduce themselves, re-explain their preferences, and repeat context on every new session. This wastes time and makes AI assistants feel impersonal and unreliable.

## The Solution

MemoryWeave is a persistent, hierarchical memory framework that gives Qwen-powered AI agents a genuine long-term memory. The agent remembers who you are, what you prefer, and what you've discussed — across sessions, across days, across weeks.

---

## Architecture

```
User (Browser)
      │
      ▼
React Dashboard (Vercel)
      │
      ▼
FastAPI Backend (Render.com)
┌──────────────────────────────────────────┐
│           Memory Orchestrator             │
│                                           │
│  ┌─────────────┐  ┌──────────────────┐   │
│  │   Working   │  │    Episodic      │   │
│  │   Memory    │  │    Memory        │   │
│  │ (in-context)│  │  (Upstash Redis) │   │
│  └─────────────┘  └──────────────────┘   │
│                   ┌──────────────────┐   │
│                   │    Semantic      │   │
│                   │    Memory        │   │
│                   │  (ChromaDB)      │   │
│                   └──────────────────┘   │
└──────────────────────────────────────────┘
      │
      ▼
Alibaba Cloud Qwen APIs (dashscope.aliyuncs.com)
  ├── qwen-max          (reasoning + chat)
  ├── qwen-long         (memory consolidation)
  ├── qwen-turbo        (fast scoring)
  └── text-embedding-v3 (semantic search)
      │
      ▼
Supabase PostgreSQL (user profiles + metadata)
```

---

## Three-Tier Memory System

| Tier | Store | Purpose | Lifetime |
|---|---|---|---|
| **Working** | In-context | Active conversation turns | Current session |
| **Episodic** | Upstash Redis | Recent session summaries | 7–30 days (TTL) |
| **Semantic** | ChromaDB vectors | Facts, preferences, learned patterns | Permanent (until pruned) |

### Smart Forgetting Algorithm

Each memory is scored: `score = (0.4 × recency) + (0.3 × frequency) + (0.3 × importance)`

Memories below the threshold are automatically pruned during nightly consolidation.

### Memory Consolidation

A background pipeline uses `qwen-long` to summarize episodic memories into semantic facts:
- 10 session turns → 3 key facts
- Contradiction detection prevents stale data
- New facts are deduplicated via vector similarity

---

## Alibaba Cloud Integration

This project uses Qwen Cloud APIs hosted on Alibaba Cloud infrastructure:

**API Endpoint**: `https://dashscope.aliyuncs.com/compatible-mode/v1`  
**Proof file**: [`backend/qwen_client.py`](./backend/qwen_client.py)

---

## Tech Stack

| Layer | Technology |
|---|---|
| LLM | Qwen-Max, Qwen-Long, Qwen-Turbo, text-embedding-v3 |
| Backend | Python 3.11 + FastAPI |
| Episodic Memory | Upstash Redis (free tier) |
| Semantic Memory | ChromaDB (embedded) |
| Database | Supabase PostgreSQL (free tier) |
| Frontend | React + TailwindCSS + shadcn/ui |
| Backend Hosting | Render.com (free tier) |
| Frontend Hosting | Vercel (free tier) |

---

## Quick Start

### Prerequisites
- Docker + Docker Compose
- Qwen Cloud API key (from [dashscope.aliyuncs.com](https://dashscope.aliyuncs.com))
- Supabase project (free at [supabase.com](https://supabase.com))
- Upstash Redis (free at [upstash.com](https://upstash.com))

### Setup

```bash
git clone https://github.com/YOUR_USERNAME/memoryweave.git
cd memoryweave

cp .env.example .env
# Edit .env with your API keys

docker compose up --build
```

### Test the connection

```bash
curl http://localhost:8000/api/v1/ping
```

### Test chat

```bash
curl -X POST http://localhost:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{"user_id": "user1", "message": "My name is Alex and I prefer Python."}'
```

---

## API Reference

| Endpoint | Method | Description |
|---|---|---|
| `/` | GET | Project info |
| `/health` | GET | Health check |
| `/api/v1/ping` | GET | Test Qwen Cloud connection |
| `/api/v1/chat` | POST | Send message to MemoryWeave agent |
| `/api/v1/memories/{user_id}` | GET | View stored memories |
| `/api/v1/memories/{id}` | DELETE | Delete a specific memory |
| `/api/v1/metrics/{user_id}` | GET | Accuracy improvement metrics |

Full API docs: `http://localhost:8000/docs`

---

## License

[MIT](./LICENSE)
