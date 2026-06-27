from tools import get_ticket_info

info = get_ticket_info("AAPL")

if info:
    print("Ticket Info:", info)
else:
    print("No information found for the given ticker.")