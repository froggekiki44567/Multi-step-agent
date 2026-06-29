import re
import json
from dataclasses import dataclass, field
from typing import Optional

# Agentas turi ignuoruoti siuos dalykus arba nukreipti juos
_BLOCKED_PATTERNS = [
    (r"\b(insider|non.?public)\b.{0,30}\b(tip|info|trade)\b", "insider trading guidance"),
    (r"\bhow.{0,20}(launder|evade|hide).{0,20}(money|tax|fund)", "financial crime facilitation"),
    (r"\b(manipulat|pump.and.dump|wash.trad)", "market manipulation"),
    (r"\bpersonal.{0,20}(password|pin|ssn|social.security)", "PII/credential request"),
]

_FINANCIAL_KEYWORDS = [
    "revenue", "profit", "loss", "ebitda", "margin", "debt", "cash", "risk",
    "stock", "equity", "bond", "rate", "currency", "exchange", "ticker",
    "invest", "portfolio", "asset", "liability", "balance", "income",
    "quarter", "annual", "fiscal", "gdp", "inflation", "interest",
    "compare", "analyze", "assess", "calculate", "convert", "worth",
]
