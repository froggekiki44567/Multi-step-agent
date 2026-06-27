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
    
