import os
from dotenv import load_dotenv

load_dotenv()

DASHSCOPE_API_KEY: str = os.getenv("DASHSCOPE_API_KEY", "")
DASHSCOPE_BASE_URL: str = os.getenv(
    "DASHSCOPE_BASE_URL",
    "https://dashscope-intl.aliyuncs.com/compatible-mode/v1",
)
SUPABASE_URL: str = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY: str = os.getenv("SUPABASE_KEY", "")
DATABASE_URL: str = os.getenv("DATABASE_URL", "")
REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379")

QWEN_CHAT_MODEL: str = os.getenv("QWEN_CHAT_MODEL", "qwen-max")
QWEN_LONG_MODEL: str = os.getenv("QWEN_LONG_MODEL", "qwen-long")
QWEN_EMBED_MODEL: str = os.getenv("QWEN_EMBED_MODEL", "text-embedding-v3")
QWEN_FAST_MODEL: str = os.getenv("QWEN_FAST_MODEL", "qwen-turbo")

APP_ENV: str = os.getenv("APP_ENV", "development")
CORS_ORIGINS: list[str] = os.getenv(
    "CORS_ORIGINS", "http://localhost:3000,http://localhost:5173"
).split(",")

CHROMA_DB_PATH: str = os.getenv("CHROMA_DB_PATH", "./chroma_db")


def validate_config() -> list[str]:
    missing = []
    if not DASHSCOPE_API_KEY:
        missing.append("DASHSCOPE_API_KEY")
    return missing
