import os
from pathlib import Path
from typing import Optional

# Load .env file if it exists (same as main.py)
_env_path = Path(__file__).parent / ".env"
if _env_path.exists():
    for _line in _env_path.read_text().splitlines():
        if "=" in _line and not _line.startswith("#"):
            _k, _v = _line.split("=", 1)
            os.environ.setdefault(_k.strip(), _v.strip())

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

import vectorstore
from agent import FinancialAgent
from tools import TOOL_SCHEMAS

app = FastAPI(
    title="Financial Analysis Agent API",
    description="HTTP interface for the ReAct financial analysis agent.",
    version="1.0.0",
)

# One FinancialAgent (= one conversation memory) per session_id.
_sessions: dict[str, FinancialAgent] = {}


def _get_agent(session_id: str) -> FinancialAgent:
    agent = _sessions.get(session_id)
    if agent is None:
        agent = FinancialAgent()
        _sessions[session_id] = agent
    return agent


class QueryRequest(BaseModel):
    query: str
    session_id: str = "default"


class QueryResponse(BaseModel):
    answer: str
    tools_called: list[str]
    iterations: int
    latency_ms: float
    quality_score: Optional[float] = None
    hallucination_risk: Optional[str] = None
    issues: list[str] = []


class ResetRequest(BaseModel):
    session_id: str = "default"


class SearchRequest(BaseModel):
    query: str
    n_results: int = 5


@app.on_event("startup")
def _check_api_key():
    if not os.getenv("ANTHROPIC_API_KEY"):
        raise RuntimeError("ANTHROPIC_API_KEY environment variable not set.")


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/tools")
def list_tools():
    return TOOL_SCHEMAS


@app.post("/query", response_model=QueryResponse)
def query(req: QueryRequest):
    agent = _get_agent(req.session_id)
    resp = agent.run(req.query)

    if not resp.input_check.allowed:
        raise HTTPException(status_code=400, detail=resp.answer)

    return QueryResponse(
        answer=resp.answer,
        tools_called=resp.tools_called,
        iterations=resp.iterations,
        latency_ms=resp.latency_ms,
        quality_score=resp.output_quality.score if resp.output_quality else None,
        hallucination_risk=resp.output_quality.hallucination_risk if resp.output_quality else None,
        issues=resp.output_quality.issues if resp.output_quality else [],
    )


@app.post("/reset")
def reset(req: ResetRequest):
    agent = _sessions.get(req.session_id)
    if agent is None:
        return {"status": "no session to reset"}
    agent.reset()
    return {"status": "reset"}


@app.get("/stats/{session_id}")
def stats(session_id: str):
    agent = _sessions.get(session_id)
    if agent is None:
        raise HTTPException(status_code=404, detail="Unknown session_id")
    return agent.memory_stats


@app.post("/search")
def search_knowledge(req: SearchRequest):
    """Semantic search directly over the vector store (bypasses the LLM)."""
    return {"matches": vectorstore.search(req.query, n_results=req.n_results)}
