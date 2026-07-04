"""
Persistent vector store for financial data snapshots.

Every time a tool fetches fresh data for a ticker (query_financials,
summarize_risk), we store a text summary + metadata here. This gives the
agent two things beyond the in-memory TTL cache in tools.py:

1. Persistence across restarts (chromadb writes to disk).
2. Semantic search — the agent can ask things like "which companies did
   I check with high debt risk" without knowing exact tickers.

Embeddings are computed locally with sentence-transformers (no API key
needed), so this works standalone even if only ANTHROPIC_API_KEY is set.
"""

import json
from pathlib import Path
from typing import Any, Optional

import chromadb
from chromadb.utils import embedding_functions

_DB_PATH = str(Path(__file__).parent / "chroma_data")
_COLLECTION_NAME = "financial_data"
_EMBEDDING_MODEL = "all-MiniLM-L6-v2"

_client = None
_collection = None


def _get_collection():
    global _client, _collection
    if _collection is None:
        _client = chromadb.PersistentClient(path=_DB_PATH)
        embed_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name=_EMBEDDING_MODEL
        )
        _collection = _client.get_or_create_collection(
            name=_COLLECTION_NAME,
            embedding_function=embed_fn,
        )
    return _collection


def _to_document(ticker: str, data: dict[str, Any]) -> str:
    """Flatten a financial data dict into a natural-language summary for embedding."""
    parts = [f"{ticker.upper()} — {data.get('name', 'N/A')}", f"Sector: {data.get('sector', 'N/A')}"]
    for key in (
        "revenue_M", "net_income_M", "ebitda_M", "total_debt_M", "cash_M",
        "market_cap_M", "risk_score", "risk_tier",
    ):
        if key in data and data[key] is not None:
            parts.append(f"{key}: {data[key]}")
    if data.get("flags"):
        parts.append("Risk flags: " + "; ".join(data["flags"]))
    return " | ".join(parts)


def upsert_financial_data(ticker: str, data: dict[str, Any]) -> None:
    """Store/update a snapshot of tool output for a ticker."""
    ticker = ticker.upper().strip()
    if "error" in data:
        return

    collection = _get_collection()
    document = _to_document(ticker, data)
    # Metadata values must be str/int/float/bool for chromadb.
    metadata = {"ticker": ticker, "raw_json": json.dumps(data)}

    collection.upsert(ids=[ticker], documents=[document], metadatas=[metadata])


def get_by_ticker(ticker: str) -> Optional[dict[str, Any]]:
    """Exact-match lookup of the last stored snapshot for a ticker."""
    collection = _get_collection()
    result = collection.get(ids=[ticker.upper().strip()])
    if not result["ids"]:
        return None
    return json.loads(result["metadatas"][0]["raw_json"])


def search(query: str, n_results: int = 5) -> list[dict[str, Any]]:
    """Semantic search over stored financial snapshots."""
    collection = _get_collection()
    if collection.count() == 0:
        return []
    n_results = min(n_results, collection.count())

    result = collection.query(query_texts=[query], n_results=n_results)

    matches = []
    for doc, meta, dist in zip(
        result["documents"][0], result["metadatas"][0], result["distances"][0]
    ):
        matches.append({
            "ticker": meta["ticker"],
            "summary": doc,
            "data": json.loads(meta["raw_json"]),
            "distance": round(dist, 4),
        })
    return matches
