import json
import re
import time
from dataclasses import dataclass, field
from typing import Optional

import anthropic

from tools import TOOL_SCHEMAS, dispatch
from memory import ConversationMemory
from guardrails import check_input, check_output, InputCheckResult, OutputQualityReport

@dataclass
class AgentResponse:
    answer: str
    tools_called: list[str]
    tool_results: list[dict]
    steps: list[str]                       # reasoning trace
    input_check: InputCheckResult = None
    output_quality: OutputQualityReport = None
    iterations: int = 0
    latency_ms: float = 0.0
    error: Optional[str] = None

_TOOL_BLOCK_RE = re.compile(
    r"```tool_call\s*\n(\{.*?\})\s*\n```",
    re.DOTALL,
)


def parse_tool_call(text: str) -> Optional[dict]:
    """Extract the first tool_call JSON block from LLM output."""
    match = _TOOL_BLOCK_RE.search(text)
    if not match:
        return None
    try:
        return json.loads(match.group(1))
    except json.JSONDecodeError:
        return None


def extract_final_answer(text: str) -> Optional[str]:
    """Extract everything after 'FINAL ANSWER:' marker."""
    marker = "FINAL ANSWER:"
    idx = text.find(marker)
    if idx == -1:
        return None
    return text[idx + len(marker):].strip()