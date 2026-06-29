from typing import Optional, Any
import yfinance as yf
import time
from datetime import datetime, timezone

_cache: dict[str, dict] = {}
_CACHE_TTL = 300

def _get_ticker_info(ticker: str) -> Optional[dict]:

    ticker = ticker.upper().strip()
    cached = _cache.get(ticker)
    if cached and (time.time() - cached["_ts"] < _CACHE_TTL):
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

def query_financials(ticker: str) -> dict[str, Any]:
    info = _get_ticker_info(ticker)
    if info is None:
        return {
            "error": f"Could not fetch data for '{ticker}'. Check the ticker symbol.",
            "hint": "Use standard Yahoo Finance tickers: 'AAPL', 'NOVO-B.CO', 'SEB-A.ST', etc.",
        }

    def _m(val):
        """Convert to millions, round to 1dp."""
        if val is None:
            return None
        return round(val / 1_000_000, 1)

    revenue    = _m(info.get("totalRevenue"))
    net_income = _m(info.get("netIncomeToCommon"))
    ebitda     = _m(info.get("ebitda"))
    total_debt = _m(info.get("totalDebt"))
    cash       = _m(info.get("totalCash"))
    price      = info.get("currentPrice") or info.get("regularMarketPrice")
    mkt_cap    = _m(info.get("marketCap"))

    return {
        "ticker":      ticker.upper(),
        "name":        info.get("shortName") or info.get("longName", "N/A"),
        "sector":      info.get("sector", "N/A"),
        "currency":    info.get("financialCurrency", "USD"),
        "price":       price,
        "market_cap_M":  mkt_cap,
        "revenue_M":     revenue,
        "net_income_M":  net_income,
        "ebitda_M":      ebitda,
        "total_debt_M":  total_debt,
        "cash_M":        cash,
        "fiscal_year":   info.get("mostRecentQuarter", "N/A"),
        "note": "All _M values in millions of the company's reporting currency.",
    }

def calculate(expression: str) -> dict[str, Any]:
    allowed_chars = set("0123456789+-*/.() ")
    clean = expression.replace("**", "##POW##")
    clean = clean.replace("##POW##", "**")

    if not all(c in allowed_chars or c == "*" for c in clean):
        return {"error": "Expression contains disallowed characters.", "expression": expression}

    try:
        result = eval(expression, {"__builtins__": {}}, {"round": round, "abs": abs})
        return {
            "expression": expression,
            "result":     round(float(result), 4),
        }
    except Exception as e:
        return {"error": str(e), "expression": expression}
    
def get_exchange_rate(from_currency: str, to_currency: str) -> dict[str, Any]:
    fc = from_currency.upper().strip()
    tc = to_currency.upper().strip()

    if fc == tc:
        return {"from": fc, "to": tc, "rate": 1.0}

    rate = _EXCHANGE_RATES.get((fc, tc))
    if rate is None:
        inv = _EXCHANGE_RATES.get((tc, fc))
        if inv:
            rate = round(1 / inv, 6)
        else:
            return {"error": f"Exchange rate {fc}/{tc} not available. Supported: USD, EUR, GBP, SEK, DKK."}

    return {
        "from":      fc,
        "to":        tc,
        "rate":      rate,
        "timestamp": datetime.now(timezone.utc).isoformat() + "Z",
    }

def summarize_risk(ticker: str) -> dict[str, Any]:
    data = query_financials(ticker)
    if "error" in data:
        return data

    flags  = []
    score  = 0

    revenue    = data.get("revenue_M")    or 0
    net_income = data.get("net_income_M") or 0
    ebitda     = data.get("ebitda_M")     or 0
    debt       = data.get("total_debt_M") or 0
    cash       = data.get("cash_M")       or 0
    sector     = data.get("sector", "")

    # Debt / EBITDA
    if ebitda > 0:
        de = debt / ebitda
        if de > 6:
            flags.append(f"Debt/EBITDA critically high: {de:.1f}x")
            score += 35
        elif de > 4:
            flags.append(f"Debt/EBITDA elevated: {de:.1f}x")
            score += 20
        elif de > 2:
            score += 8

    # Net margin
    if revenue > 0:
        margin = (net_income / revenue) * 100
        if margin < 0:
            flags.append(f"Negative net margin: {margin:.1f}%")
            score += 30
        elif margin < 5:
            flags.append(f"Thin net margin: {margin:.1f}%")
            score += 15
        elif margin > 25:
            flags.append(f"Strong net margin: {margin:.1f}%")

    # Cash coverage
    if debt > 0:
        cov = cash / debt
        if cov < 0.05:
            flags.append(f"Very low cash coverage: {cov:.1%} of debt")
            score += 20
        elif cov < 0.15:
            flags.append(f"Low cash coverage: {cov:.1%} of debt")
            score += 10

    # Sector adjustment
    if "financial" in sector.lower() or "bank" in sector.lower():
        flags.append("Financial sector: high leverage is structural")
        score = max(0, score - 15)

    score = min(score, 100)
    tier  = (
        "Low"      if score < 20 else
        "Medium"   if score < 45 else
        "High"     if score < 70 else
        "Critical"
    )

    return {
        "ticker":       ticker.upper(),
        "name":         data.get("name"),
        "risk_score":   score,
        "risk_tier":    tier,
        "flags":        flags if flags else ["No major risk flags detected"],
        "assessed_at":  datetime.utcnow().isoformat() + "Z",
    } 

TOOL_MAP = {
    "query_financials": query_financials,
    "calculate":        calculate,
    "get_exchange_rate": get_exchange_rate,
    "summarize_risk":   summarize_risk,
}


def dispatch(tool_name: str, args: dict) -> dict:
    fn = TOOL_MAP.get(tool_name)
    if fn is None:
        return {"error": f"Unknown tool: '{tool_name}'"}
    try:
        return fn(**args)
    except TypeError as e:
        return {"error": f"Bad arguments for '{tool_name}': {e}"}
