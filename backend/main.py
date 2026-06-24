import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from config import CORS_ORIGINS, validate_config
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
    logger.info("🧠 MemoryWeave backend starting...")
    yield
    logger.info("MemoryWeave backend shutting down")


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
