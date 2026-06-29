from typing import Optional
import yfinance as yf
import time

_cache: dict[str, dict] = {}
_CACHE_TTL = 300

def get_ticker_info(ticker: str) -> Optional[dict]:

    ticker = ticker.upper().strip()
    cached = _cache.get(ticker)
    if cached and (time.time() - cached["timestamp"] < _CACHE_TTL):
        return cached
    
    try:
        info = yf.Ticker(ticker).info
        if not info or info.get("trailingPps") is None and info.get("totalRevenue") is None:
            return None
        info["_ts"] = time.time()
        _cache[ticker] = info
        return info
    except Exception:
        return None
    
# Pridedamas, nes yahoo FX yra nepatikimas nemokamame lygyje, todėl naudojami statiniai valiutų kursai
_EXCHANGE_RATES = {
    ("USD", "EUR"): 0.921,
    ("USD", "GBP"): 0.789,
    ("USD", "SEK"): 10.42,
    ("USD", "DKK"): 7.05,
    ("EUR", "USD"): 1.086,
    ("EUR", "GBP"): 0.857,
    ("EUR", "SEK"): 11.32,
    ("EUR", "DKK"): 7.46,
    ("GBP", "USD"): 1.267,
    ("SEK", "EUR"): 0.0883,
    ("DKK", "EUR"): 0.134,
}

TOOL_SCHEMAS = [
    {
        "name": "query_financials",
        "description": (
            "Retrieve real financial metrics for any publicly traded company by ticker symbol. "
            "Returns revenue, net income, EBITDA, total debt, cash, sector, and current price. "
            "All figures in USD (most recent fiscal year). Uses live Yahoo Finance data."
        ),
        "parameters": {
            "ticker": "string — company ticker, e.g. 'AAPL', 'MSFT', 'NOVO-B.CO', 'SEB-A.ST'"
        },
    },
    {
        "name": "calculate",
        "description": (
            "Evaluate a mathematical expression safely. "
            "Use for ratios, growth rates, percentages. "
            "Supports: +, -, *, /, **, round(), abs(). "
            "Example: '(96995 / 394328) * 100' returns net margin %."
        ),
        "parameters": {
            "expression": "string — math expression to evaluate"
        },
    },
    {
        "name": "get_exchange_rate",
        "description": (
            "Get the exchange rate between two currencies. "
            "Returns rate to convert 1 unit of from_currency to to_currency. "
            "Supported: USD, EUR, GBP, SEK, DKK."
        ),
        "parameters": {
            "from_currency": "string — ISO 4217 code, e.g. 'USD', 'EUR'",
            "to_currency":   "string — ISO 4217 code",
        },
    },
    {
        "name": "summarize_risk",
        "description": (
            "Assess financial risk profile of a publicly traded company. "
            "Returns a risk score (0-100), risk tier (Low/Medium/High/Critical), "
            "and specific risk flags based on live financial data."
        ),
        "parameters": {
            "ticker": "string — company ticker to assess"
        },
    },
]
    
