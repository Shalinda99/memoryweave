from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from qwen_client import qwen

router = APIRouter()


class ChatRequest(BaseModel):
    user_id: str
    message: str
    session_id: str | None = None


class ChatResponse(BaseModel):
    reply: str
    user_id: str
    session_id: str
    memories_used: list[str] = []


@router.get("/ping")
async def ping():
    """Test Qwen Cloud (Alibaba Cloud DashScope) connectivity."""
    try:
        response = qwen.chat([
            {"role": "user", "content": "Reply with exactly: MemoryWeave is online!"}
        ])
        return {"qwen_response": response, "status": "connected"}
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Qwen connection failed: {str(e)}")


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Send a message to the MemoryWeave agent.
    Memory retrieval and storage will be added in Phase 2.
    """
    import uuid
    session_id = request.session_id or str(uuid.uuid4())

    reply = qwen.chat([
        {
            "role": "system",
            "content": (
                "You are MemoryWeave, an AI assistant with persistent memory. "
                "You remember users across sessions and learn their preferences over time."
            ),
        },
        {"role": "user", "content": request.message},
    ])

    return ChatResponse(
        reply=reply,
        user_id=request.user_id,
        session_id=session_id,
        memories_used=[],
    )


@router.get("/memories/{user_id}")
async def get_memories(user_id: str):
    """
    Retrieve stored memories for a user.
    Full implementation in Phase 2.
    """
    return {
        "user_id": user_id,
        "memories": [],
        "note": "Memory system will be implemented in Phase 2",
    }
