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