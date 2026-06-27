from tools import get_ticker_info

info = get_ticker_info("AAPL")

if info:
    print("Ticker Info:", info)
else:
    print("No information found for the given ticker.")