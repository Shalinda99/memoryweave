"""
MemoryWeave — Qwen Cloud Client
Alibaba Cloud DashScope Integration

API Base URL: https://dashscope-intl.aliyuncs.com/compatible-mode/v1  (international)
             https://dashscope.aliyuncs.com/compatible-mode/v1         (China)
This file demonstrates use of Alibaba Cloud services and APIs
as required by the Global AI Hackathon Series with Qwen Cloud.

Alibaba Cloud services used:
  - qwen-max      : Main reasoning and chat completions
  - qwen-long     : Long-context memory consolidation
  - qwen-turbo    : Fast memory scoring and classification
  - text-embedding-v3 : Semantic vector embeddings for memory retrieval
"""

from openai import OpenAI
from config import (
    DASHSCOPE_API_KEY,
    DASHSCOPE_BASE_URL,
    QWEN_CHAT_MODEL,
    QWEN_LONG_MODEL,
    QWEN_EMBED_MODEL,
    QWEN_FAST_MODEL,
)


class QwenClient:
    """
    Client for Alibaba Cloud Qwen models via DashScope API.
    Uses the OpenAI-compatible endpoint (international: dashscope-intl.aliyuncs.com).
    """

    def __init__(self):
        self._client = OpenAI(
            api_key=DASHSCOPE_API_KEY,
            base_url=DASHSCOPE_BASE_URL,
        )

    def chat(
        self,
        messages: list[dict],
        model: str | None = None,
        temperature: float = 0.7,
        max_tokens: int | None = None,
    ) -> str:
        kwargs: dict = dict(
            model=model or QWEN_CHAT_MODEL,
            messages=messages,
            temperature=temperature,
        )
        if max_tokens:
            kwargs["max_tokens"] = max_tokens
        response = self._client.chat.completions.create(**kwargs)
        return response.choices[0].message.content or ""

    def chat_long(
        self,
        messages: list[dict],
        temperature: float = 0.3,
    ) -> str:
        return self.chat(messages, model=QWEN_LONG_MODEL, temperature=temperature)

    def chat_fast(
        self,
        messages: list[dict],
        temperature: float = 0.3,
    ) -> str:
        return self.chat(messages, model=QWEN_FAST_MODEL, temperature=temperature)

    def embed(self, text: str) -> list[float]:
        response = self._client.embeddings.create(
            model=QWEN_EMBED_MODEL,
            input=text,
        )
        return response.data[0].embedding

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        response = self._client.embeddings.create(
            model=QWEN_EMBED_MODEL,
            input=texts,
        )
        return [item.embedding for item in response.data]


qwen = QwenClient()
