import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from config import CORS_ORIGINS, REDIS_URL, CHROMA_DB_PATH, validate_config
from api.routes import router

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("memoryweave")


@asynccontextmanager
async def lifespan(app: FastAPI):
    missing = validate_config()
    if missing:
        logger.warning(f"Missing environment variables: {missing}")
    else:
        logger.info("✅ All required environment variables are set")

    logger.info("🧠 MemoryWeave backend starting — initializing memory system...")

    from memory.episodic import EpisodicMemoryStore
    from memory.semantic import SemanticMemoryStore
    from memory.scoring import MemoryScorer
    from memory.consolidation import ConsolidationPipeline
    from memory.orchestrator import MemoryOrchestrator
    from memory.working import WorkingMemoryManager
    from agent.memory_agent import MemoryAgent
    from qwen_client import qwen

    episodic = EpisodicMemoryStore(redis_url=REDIS_URL)
    try:
        await episodic.connect()
        logger.info("✅ Redis (Tier 2 — Episodic memory) connected")
    except Exception as e:
        logger.error(f"❌ Redis connection failed: {e}")
        raise RuntimeError(f"Redis is required: {e}")

    semantic = SemanticMemoryStore(chroma_path=CHROMA_DB_PATH, embed_fn=qwen.embed)
    try:
        semantic.initialize()
        logger.info("✅ ChromaDB (Tier 3 — Semantic memory) initialized")
    except Exception as e:
        logger.error(f"❌ ChromaDB initialization failed: {e}")
        raise RuntimeError(f"ChromaDB is required: {e}")

    scorer = MemoryScorer()

    consolidation = ConsolidationPipeline(
        qwen_client=qwen,
        episodic_store=episodic,
        semantic_store=semantic,
        scorer=scorer,
    )

    orchestrator = MemoryOrchestrator(
        working_memory_cls=WorkingMemoryManager,
        episodic_store=episodic,
        semantic_store=semantic,
        consolidation_pipeline=consolidation,
        scorer=scorer,
        token_budget=6000,
    )

    agent = MemoryAgent(qwen_client=qwen, orchestrator=orchestrator)
    app.state.agent = agent

    logger.info("✅ MemoryWeave three-tier memory system ready")
    logger.info("   Tier 1: WorkingMemoryManager (in-context, per-session)")
    logger.info("   Tier 2: EpisodicMemoryStore  (Redis TTL, cross-session)")
    logger.info("   Tier 3: SemanticMemoryStore  (ChromaDB + Qwen embeddings)")

    yield

    logger.info("🛑 MemoryWeave backend shutting down")


app = FastAPI(
    title="MemoryWeave API",
    description=(
        "Persistent hierarchical memory layer for Qwen-powered AI assistants. "
        "Built for the Global AI Hackathon Series with Qwen Cloud (Track 1: MemoryAgent)."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router, prefix="/api/v1")


@app.get("/")
async def root():
    return {
        "project": "MemoryWeave",
        "version": "1.0.0",
        "track": "Track 1: MemoryAgent",
        "powered_by": "Alibaba Cloud Qwen",
        "docs": "/docs",
    }


@app.get("/health")
async def health():
    return {"status": "healthy"}
