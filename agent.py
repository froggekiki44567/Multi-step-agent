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

class FinancialAgent:
    MAX_ITERATIONS = 8 # hard coding

    def __init__(self, api_key: Optional[str] = None):
        # env var automatically
        self.client = anthropic.Anthropic(api_key=api_key)
        self.memory = ConversationMemory()
        self._build_tool_context()

    def _build_tool_context(self):
        """Prepend available tools to system context (injected once)."""
        tools_doc = "AVAILABLE TOOLS:\n"
        for t in TOOL_SCHEMAS:
            tools_doc += f"\n• {t['name']}: {t['description']}\n"
            tools_doc += f"  Parameters: {json.dumps(t['parameters'])}\n"
        # Append to system message
        self.memory.messages[0].content += f"\n\n{tools_doc}"

    def _call_llm(self) -> str:
        """Send current context to Claude and return raw text response."""
        context = self.memory.get_context()
        system_msg = next((m["content"] for m in context if m["role"] == "system"), "")
        user_msgs = [m for m in context if m["role"] != "system"]

        response = self.client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=1024,
            system=system_msg,
            messages=user_msgs,
        )
        return response.content[0].text

    def run(self, user_query: str) -> AgentResponse:
        """
        Process a user query through the full ReAct loop.

        Returns an AgentResponse with the answer, trace, and quality report.
        """
        t_start = time.monotonic()
        tools_called: list[str] = []
        tool_results: list[dict] = []
        steps: list[str] = []

        # --- Input guardrail ---
        input_check = check_input(user_query)
        if not input_check.allowed:
            return AgentResponse(
                answer=f"I can't process that query. Reason: {input_check.reason}",
                tools_called=[],
                tool_results=[],
                steps=["[BLOCKED by input guardrail]"],
                input_check=input_check,
                latency_ms=(time.monotonic() - t_start) * 1000,
            )

        # Add query to memory
        self.memory.add_user(user_query)
        steps.append(f"User query: {user_query}")

        # --- ReAct loop ---
        final_answer = None
        for iteration in range(self.MAX_ITERATIONS):
            steps.append(f"\n[Iteration {iteration + 1}]")

            llm_output = self._call_llm()
            self.memory.add_assistant(llm_output)
            steps.append(f"LLM output:\n{llm_output}")

            # Check for final answer
            final_answer = extract_final_answer(llm_output)
            if final_answer:
                steps.append("→ Final answer extracted.")
                break

            # Check for tool call
            tool_call = parse_tool_call(llm_output)
            if tool_call:
                tool_name = tool_call.get("tool", "")
                tool_args = tool_call.get("args", {})
                steps.append(f"→ Tool call: {tool_name}({tool_args})")

                result = dispatch(tool_name, tool_args)
                tools_called.append(tool_name)
                tool_results.append(result)
                steps.append(f"→ Tool result: {json.dumps(result, indent=2)}")

                self.memory.add_tool_result(tool_name, result)
            else:
                steps.append("No tool call or final answer found; nudging.")
                self.memory.add_user(
                    "Please continue. If you have enough information, provide your FINAL ANSWER. "
                    "Otherwise, call the next tool."
                )

        if final_answer is None:
            final_answer = (
                "I was unable to reach a definitive answer within the iteration limit. "
                "Here is my last reasoning step:\n\n"
                + (steps[-1] if steps else "No output produced.")
            )

        # --- Output guardrail ---
        quality = check_output(final_answer, tool_results, tools_called)

        latency = (time.monotonic() - t_start) * 1000
        return AgentResponse(
            answer=final_answer,
            tools_called=tools_called,
            tool_results=tool_results,
            steps=steps,
            input_check=input_check,
            output_quality=quality,
            iterations=iteration + 1,
            latency_ms=round(latency, 1),
        )

    def reset(self):
        """Clear conversation memory for a new session."""
        self.memory.reset()
        self._build_tool_context()

    @property
    def memory_stats(self) -> dict:
        return self.memory.stats()
