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
    
