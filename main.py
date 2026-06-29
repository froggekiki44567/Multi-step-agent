import argparse
import json
import os
import sys
import time
from textwrap import indent

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