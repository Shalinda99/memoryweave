import asyncio
import logging
from fastapi import APIRouter, HTTPException, Request, BackgroundTasks
from pydantic import BaseModel
from qwen_client import qwen

logger = logging.getLogger("memoryweave.routes")
router = APIRouter()


# ── Request / Response models ────────────────────────────────────────────────

class ChatRequest(BaseModel):
    user_id: str
    message: str
    session_id: str | None = None


class ChatResponse(BaseModel):
    reply: str
    user_id: str
    session_id: str
    memories_used: list[str] = []
    tokens_used: int = 0


class MemoryItem(BaseModel):
    id: str
    content: str
    memory_type: str
    importance_score: float
    created_at: str
    tier: str


class MemoriesResponse(BaseModel):
    user_id: str
    semantic: list[MemoryItem] = []
    episodic: list[MemoryItem] = []
    total: int = 0


class ConsolidationResponse(BaseModel):
    user_id: str
    episodic_processed: int
    facts_extracted: int
    facts_stored: int
    contradictions_resolved: int
    memories_pruned: int


# ── Helpers ──────────────────────────────────────────────────────────────────

def _get_agent(request: Request):
    agent = getattr(request.app.state, "agent", None)
    if agent is None:
        raise HTTPException(status_code=503, detail="Memory system not initialized")
    return agent


def _get_orchestrator(request: Request):
    return _get_agent(request).orchestrator


# ── Routes ───────────────────────────────────────────────────────────────────

@router.get("/ping")
async def ping():
    """Test Qwen Cloud (Alibaba Cloud DashScope) connectivity."""
    try:
        response = await asyncio.to_thread(
            qwen.chat,
            [{"role": "user", "content": "Reply with exactly: MemoryWeave is online!"}],
        )
        return {"qwen_response": response, "status": "connected", "model": "qwen-max"}
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Qwen connection failed: {str(e)}")


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest, req: Request):
    """Send a message to the MemoryWeave agent with full memory integration."""
    agent = _get_agent(req)
    try:
        result = await agent.chat(
            user_id=request.user_id,
            message=request.message,
            session_id=request.session_id,
        )
        return ChatResponse(
            reply=result.reply,
            user_id=result.user_id,
            session_id=result.session_id,
            memories_used=result.memories_used,
            tokens_used=result.tokens_used,
        )
    except Exception as e:
        logger.error(f"Chat error for user {request.user_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/memories/{user_id}", response_model=MemoriesResponse)
async def get_memories(user_id: str, req: Request):
    """Retrieve all stored memories (semantic + episodic) for a user."""
    orchestrator = _get_orchestrator(req)

    semantic_task = asyncio.to_thread(orchestrator.semantic.get_all, user_id)
    episodic_task = orchestrator.episodic.retrieve(user_id, limit=50)
    semantic_mems, episodic_mems = await asyncio.gather(semantic_task, episodic_task)

    semantic_items = [
        MemoryItem(
            id=m.id,
            content=m.content,
            memory_type=m.memory_type.value,
            importance_score=m.importance_score,
            created_at=m.created_at.isoformat(),
            tier="semantic",
        )
        for m in semantic_mems
    ]
    episodic_items = [
        MemoryItem(
            id=m.id,
            content=m.summary,
            memory_type="episodic",
            importance_score=m.importance_score,
            created_at=m.created_at.isoformat(),
            tier="episodic",
        )
        for m in episodic_mems
    ]

    return MemoriesResponse(
        user_id=user_id,
        semantic=semantic_items,
        episodic=episodic_items,
        total=len(semantic_items) + len(episodic_items),
    )


@router.delete("/memories/semantic/{memory_id}")
async def delete_semantic_memory(memory_id: str, req: Request):
    """Delete a specific semantic (long-term) memory by ID."""
    orchestrator = _get_orchestrator(req)
    ok = await asyncio.to_thread(orchestrator.semantic.delete, memory_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Memory not found")
    return {"deleted": memory_id, "tier": "semantic"}


@router.delete("/memories/episodic/{memory_id}")
async def delete_episodic_memory(memory_id: str, req: Request):
    """Delete a specific episodic memory by ID."""
    orchestrator = _get_orchestrator(req)
    ok = await orchestrator.episodic.delete(memory_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Memory not found")
    return {"deleted": memory_id, "tier": "episodic"}


@router.delete("/memories/{user_id}/all")
async def delete_all_memories(user_id: str, req: Request):
    """Delete ALL memories (semantic + episodic) for a user."""
    orchestrator = _get_orchestrator(req)

    semantic_mems = await asyncio.to_thread(orchestrator.semantic.get_all, user_id)
    episodic_mems = await orchestrator.episodic.retrieve(user_id, limit=500)

    sem_deleted = 0
    for m in semantic_mems:
        if await asyncio.to_thread(orchestrator.semantic.delete, m.id):
            sem_deleted += 1

    ep_deleted = 0
    for m in episodic_mems:
        if await orchestrator.episodic.delete(m.id):
            ep_deleted += 1

    return {
        "user_id": user_id,
        "semantic_deleted": sem_deleted,
        "episodic_deleted": ep_deleted,
    }


@router.post("/consolidate/{user_id}", response_model=ConsolidationResponse)
async def consolidate(user_id: str, req: Request, background_tasks: BackgroundTasks):
    """Manually trigger memory consolidation for a user (episodic → semantic)."""
    orchestrator = _get_orchestrator(req)
    try:
        result = await orchestrator.consolidation.run_for_user(user_id)
        return ConsolidationResponse(
            user_id=result.user_id,
            episodic_processed=result.episodic_processed,
            facts_extracted=result.facts_extracted,
            facts_stored=result.facts_stored,
            contradictions_resolved=result.contradictions_resolved,
            memories_pruned=result.memories_pruned,
        )
    except Exception as e:
        logger.error(f"Consolidation error for {user_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/sessions/{session_id}")
async def clear_session(session_id: str, req: Request):
    """Clear the working memory for a session."""
    orchestrator = _get_orchestrator(req)
    orchestrator.clear_session(session_id)
    return {"cleared": session_id}


@router.get("/stats/{user_id}")
async def get_stats(user_id: str, req: Request):
    """Get memory statistics for a user."""
    orchestrator = _get_orchestrator(req)
    semantic_mems = await asyncio.to_thread(orchestrator.semantic.get_all, user_id)
    episodic_count = await orchestrator.episodic.count(user_id)
    return {
        "user_id": user_id,
        "semantic_memories": len(semantic_mems),
        "episodic_memories": episodic_count,
        "active_sessions": len(orchestrator._sessions),
    }
