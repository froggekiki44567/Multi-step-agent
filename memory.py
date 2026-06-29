import json
from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal


Role = Literal["system", "user", "assistant", "tool"]


@dataclass
class Message:
    role: Role
    content: str
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    token_estimate: int = 0

    def __post_init__(self):
        # 1 token ≈ 4 chars
        self.token_estimate = max(1, len(self.content) // 4)

    def to_api_format(self) -> dict:
        return {"role": self.role, "content": self.content}