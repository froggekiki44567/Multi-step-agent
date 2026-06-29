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

    def __init__(self, max_tokens: int = 6000):
        self.max_tokens = max_tokens
        self.messages: list[Message] = []
        self.turn_count: int = 0
        self.tool_calls_total: int = 0
        self._add_system()

    def _add_system(self):
        self.messages.append(Message(role="system", content=self.SYSTEM_PROMPT))

    def add_user(self, content: str):
        self.turn_count += 1
        self.messages.append(Message(role="user", content=content))
        self._maybe_compress()

    def add_assistant(self, content: str):
        self.messages.append(Message(role="assistant", content=content))

    def add_tool_result(self, tool_name: str, result: dict):
        self.tool_calls_total += 1
        content = f"[Tool: {tool_name}]\n{json.dumps(result, indent=2)}"
        self.messages.append(Message(role="tool", content=content))

    def get_context(self) -> list[dict]:
        """Return messages in Anthropic API format."""
        return [m.to_api_format() for m in self.messages]

    def get_token_estimate(self) -> int:
        return sum(m.token_estimate for m in self.messages)

    def _maybe_compress(self):
        """Drop oldest non-system messages if over budget."""
        while self.get_token_estimate() > self.max_tokens and len(self.messages) > 3:
            for i, msg in enumerate(self.messages):
                if msg.role != "system":
                    removed = self.messages.pop(i)
                    if i == 1:
                        notice = Message(
                            role="assistant",
                            content="[Context compressed: earlier messages were dropped to fit the context window.]",
                        )
                        self.messages.insert(1, notice)
                    break
