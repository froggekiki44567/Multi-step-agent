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
    
class ConversationMemory:
    """
    Sliding window memory with a hard token budget.

    When the window exceeds `max_tokens`, oldest non-system messages
    are dropped and a compression notice is injected.
    """

    SYSTEM_PROMPT = """You are a financial analysis agent with access to real-time tools.
Your job is to answer financial questions accurately using the tools provided.

BEHAVIOUR RULES:
1. Always use tools to retrieve data — never invent financial figures.
2. Show your reasoning step by step (Thought → Action → Observation).
3. When uncertain, say so explicitly. Confidence > fabrication.
4. After each tool result, reflect on whether you have enough data or need another tool.
5. Keep final answers concise: lead with the direct answer, then supporting data.
6. If a question is outside your tool coverage, say so rather than guessing.

TOOL USAGE FORMAT — when you want to call a tool, output EXACTLY this JSON block:
```tool_call
{"tool": "<tool_name>", "args": {<arguments>}}
```
After seeing a tool result, continue your reasoning until you can give a final answer.
Output your final answer prefixed with: FINAL ANSWER:"""