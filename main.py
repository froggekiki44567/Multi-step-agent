import argparse
import json
import os
import sys
import time
from textwrap import indent
from pathlib import Path

# Load .env file if it exists
_env_path = Path(__file__).parent / ".env"
if _env_path.exists():
    for _line in _env_path.read_text().splitlines():
        if "=" in _line and not _line.startswith("#"):
            _k, _v = _line.split("=", 1)
            os.environ.setdefault(_k.strip(), _v.strip())

from agent import FinancialAgent, AgentResponse

def _c(code: str, text: str) -> str:
    """Wrap text in ANSI colour code (skipped if not a TTY)."""
    if not sys.stdout.isatty():
        return text
    return f"\033[{code}m{text}\033[0m"

def bold(t):    return _c("1", t)
def dim(t):     return _c("2", t)
def green(t):   return _c("32", t)
def yellow(t):  return _c("33", t)
def red(t):     return _c("31", t)
def cyan(t):    return _c("36", t)
def magenta(t): return _c("35", t)

def print_header():
    print()
    print(bold("┌─────────────────────────────────────────┐"))
    print(bold("│   fin-agent  ·  Financial Analysis AI   │"))
    print(bold("│   ReAct Agent  ·  Anthropic Claude       │"))
    print(bold("└─────────────────────────────────────────┘"))
    print()

def print_response(resp: AgentResponse, show_trace: bool = False):
    # indicator
    q = resp.output_quality
    risk_colour = {"low": green, "medium": yellow, "high": red}.get(
        q.hallucination_risk if q else "low", yellow
    )

    print()
    print(bold("━" * 50))
    print(bold("ANSWER"))
    print(bold("━" * 50))
    print(resp.answer)
    print()

    # Metadata
    tools_str = ", ".join(resp.tools_called) if resp.tools_called else "none"
    print(dim(f"Tools used : {tools_str}"))
    print(dim(f"Iterations : {resp.iterations}"))
    print(dim(f"Latency    : {resp.latency_ms:.0f} ms"))

    if q:
        quality_bar = "█" * int(q.score * 10) + "░" * (10 - int(q.score * 10))
        print(
            dim(f"Quality    : ")
            + risk_colour(f"{quality_bar}  {q.score:.0%}  [{q.hallucination_risk} hallucination risk]")
        )
        if q.issues:
            for issue in q.issues:
                print(yellow(f"  ⚠ {issue}"))

    if resp.input_check and resp.input_check.flags:
        for flag in resp.input_check.flags:
            print(yellow(f"  ⚑ input flag: {flag}"))

    if show_trace and resp.steps:
        print()
        print(dim("━" * 50))
        print(dim("REASONING TRACE"))
        print(dim("━" * 50))
        for step in resp.steps:
            print(dim(step))

    print()

def print_memory_stats(agent: FinancialAgent):
    stats = agent.memory_stats
    print(dim(
        f"[Memory: {stats['messages_in_window']} messages | "
        f"~{stats['token_estimate']} tokens | "
        f"{stats['budget_used_pct']}% of budget | "
        f"{stats['tool_calls_total']} tool calls total]"
    ))

DEMO_QUESTIONS = [
    "What is Apple's net profit margin and how does it compare to Microsoft's?",
    "Assess the financial risk of Goldman Sachs (GS). Should I be concerned?",
    "Convert SEB bank's annual revenue from USD to EUR.",
    "Compare the debt levels of AAPL and TSLA relative to their EBITDA.",
]

def run_demo(agent: FinancialAgent, show_trace: bool):
    print(bold(f"\nRunning {len(DEMO_QUESTIONS)} demo questions...\n"))
    for i, q in enumerate(DEMO_QUESTIONS, 1):
        print(cyan(f"\n[{i}/{len(DEMO_QUESTIONS)}] {q}"))
        resp = agent.run(q)
        print_response(resp, show_trace)
        print_memory_stats(agent)
        if i < len(DEMO_QUESTIONS):
            time.sleep(1)

REPL_HELP = """
Commands:
  /reset    — clear conversation memory
  /stats    — show memory stats
  /trace    — toggle reasoning trace
  /tools    — list available tools
  /quit     — exit
  /help     — show this message
"""

def run_repl(agent: FinancialAgent):
    from tools import TOOL_SCHEMAS

    show_trace = False
    print(cyan("\nType a financial question. /help for commands.\n"))

    while True:
        try:
            user_input = input(bold("You › ")).strip()
        except (EOFError, KeyboardInterrupt):
            print("\nBye.")
            break

        if not user_input:
            continue

        # Commands
        if user_input.startswith("/"):
            cmd = user_input.lower()
            if cmd == "/quit":
                print("Bye.")
                break
            elif cmd == "/reset":
                agent.reset()
                print(green("Memory cleared."))
            elif cmd == "/stats":
                print(json.dumps(agent.memory_stats, indent=2))
            elif cmd == "/trace":
                show_trace = not show_trace
                print(green(f"Trace: {'ON' if show_trace else 'OFF'}"))
            elif cmd == "/tools":
                for t in TOOL_SCHEMAS:
                    print(f"  {bold(t['name'])}: {t['description'][:80]}...")
            elif cmd == "/help":
                print(REPL_HELP)
            else:
                print(red(f"Unknown command: {user_input}"))
            continue

        # Query
        print(dim("Thinking..."))
        resp = agent.run(user_input)
        print_response(resp, show_trace)
        print_memory_stats(agent)

def main():
    parser = argparse.ArgumentParser(description="Financial Analysis Agent")
    parser.add_argument("--demo",  action="store_true", help="Run preset demo questions")
    parser.add_argument("--trace", action="store_true", help="Show full reasoning trace")
    parser.add_argument("--query", type=str, help="Single query (non-interactive)")
    args = parser.parse_args()

    if not os.getenv("ANTHROPIC_API_KEY"):
        print(red("Error: ANTHROPIC_API_KEY environment variable not set."))
        sys.exit(1)

    print_header()
    agent = FinancialAgent()

    if args.query:
        resp = agent.run(args.query)
        print_response(resp, show_trace=args.trace)
    elif args.demo:
        run_demo(agent, show_trace=args.trace)
    else:
        run_repl(agent)


if __name__ == "__main__":
    main()