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

@dataclass
class InputCheckResult:
    allowed: bool
    reason: Optional[str] = None
    confidence: float = 1.0
    flags: list[str] = field(default_factory=list)


def check_input(user_query: str) -> InputCheckResult:
    """Validate user query before sending to agent."""
    query_lower = user_query.lower()
    flags = []

    # Hard blocks
    for pattern, label in _BLOCKED_PATTERNS:
        if re.search(pattern, query_lower):
            return InputCheckResult(
                allowed=False,
                reason=f"Query matches blocked category: {label}",
                confidence=0.95,
                flags=[f"BLOCKED:{label}"],
            )

    # Relevance check — is this even a finance question?
    keyword_hits = sum(1 for kw in _FINANCIAL_KEYWORDS if kw in query_lower)
    if keyword_hits == 0 and len(user_query.split()) > 3:
        flags.append("LOW_RELEVANCE: no financial keywords detected")
        return InputCheckResult(
            allowed=True,  # still allow, but flag it
            reason="Query may be outside financial domain",
            confidence=0.6,
            flags=flags,
        )

    # Prompt injection attempt
    injection_signals = ["ignore previous", "disregard", "new instructions", "you are now", "jailbreak"]
    if any(sig in query_lower for sig in injection_signals):
        flags.append("INJECTION_ATTEMPT")
        return InputCheckResult(
            allowed=False,
            reason="Possible prompt injection detected",
            confidence=0.85,
            flags=flags,
        )

    return InputCheckResult(allowed=True, confidence=1.0, flags=flags)