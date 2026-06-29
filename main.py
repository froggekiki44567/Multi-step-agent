from tools import dispatch

def test(label: str, tool: str, args: dict):
    print(f"\n--- {label} ---")
    result = dispatch(tool, args)
    for k, v in result.items():
        print(f"  {k}: {v}")

test("Financials: Apple",        "query_financials",  {"ticker": "AAPL"})
test("Financials: Novo Nordisk", "query_financials",  {"ticker": "NOVO-B.CO"})
test("Calculate: net margin",    "calculate",         {"expression": "(96995 / 394328) * 100"})
test("Exchange rate: USD→EUR",   "get_exchange_rate", {"from_currency": "USD", "to_currency": "EUR"})
test("Exchange rate: EUR→DKK",   "get_exchange_rate", {"from_currency": "EUR", "to_currency": "DKK"})
test("Risk: Apple",              "summarize_risk",    {"ticker": "AAPL"})
test("Risk: unknown ticker",     "summarize_risk",    {"ticker": "FAKEXYZ"})
test("Unknown tool",             "nežinomas",         {})