"""
Working Memory Manager

Manages the active in-context conversation window for the current session.
Tracks token usage to stay within the Qwen model context limit.
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
        self.system_prompt = prompt

    def add_message(self, role: str, content: str) -> None:
        self.messages.append(Message(role=role, content=content))
        self.trim_to_budget()

    def get_context(self) -> list[dict]:
        result: list[dict] = []
        if self.system_prompt:
            result.append({"role": "system", "content": self.system_prompt})
        result.extend({"role": m.role, "content": m.content} for m in self.messages)
        return result

    def estimate_tokens(self, text: str) -> int:
        """Rough estimate: ~4 chars per token (conservative for mixed CJK/English)."""
        return max(1, len(text) // 4)

    def _total_tokens(self) -> int:
        total = self.estimate_tokens(self.system_prompt)
        for m in self.messages:
            total += self.estimate_tokens(m.content)
        return total

    def trim_to_budget(self) -> None:
        """Drop oldest messages (preserving at least 2) until within token budget."""
        while len(self.messages) > 2 and self._total_tokens() > self.max_tokens:
            self.messages.pop(0)

    def clear(self) -> None:
        self.messages = []

    @property
    def turn_count(self) -> int:
        return len(self.messages) // 2
