"""
Working Memory Manager

Manages the active in-context conversation window for the current session.
Tracks token usage to stay within the Qwen model context limit.
Implemented in Phase 2.
"""

from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class Message:
    role: str
    content: str
    timestamp: datetime = field(default_factory=datetime.utcnow)


class WorkingMemoryManager:
    """
    Tier 1 of MemoryWeave: In-context working memory for the active session.

    Responsibilities:
    - Store the current conversation turn history
    - Enforce token budget (never exceed model context window)
    - Provide formatted message list for Qwen API calls
    """

    def __init__(self, max_tokens: int = 6000):
        self.max_tokens = max_tokens
        self.messages: list[Message] = []
        self.system_prompt: str = ""

    def set_system_prompt(self, prompt: str) -> None:
        raise NotImplementedError("Implemented in Phase 2")

    def add_message(self, role: str, content: str) -> None:
        raise NotImplementedError("Implemented in Phase 2")

    def get_context(self) -> list[dict]:
        raise NotImplementedError("Implemented in Phase 2")

    def estimate_tokens(self, text: str) -> int:
        raise NotImplementedError("Implemented in Phase 2")

    def trim_to_budget(self) -> None:
        raise NotImplementedError("Implemented in Phase 2")

    def clear(self) -> None:
        self.messages = []
