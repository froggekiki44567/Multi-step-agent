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

@dataclass
class OutputQualityReport:
    passed: bool
    score: float            # 0.0 – 1.0
    hallucination_risk: str  # "low" | "medium" | "high"
    issues: list[str] = field(default_factory=list)
    suggestions: list[str] = field(default_factory=list)

# Blogos frazes, kurios gali rodyti, kad atsakymas yra netikras arba nepatikimas
_HALLUCINATION_SIGNALS = [
    r"\b(approximately|roughly|around|about)\s+\$?\d",
    r"\b(I believe|I think|I'm fairly sure|probably|likely)\b",
    r"\bin \d{4}\b",                          
    r"\bsources (say|indicate|suggest)\b",
]

_UNCERTAINTY_PHRASES = [
    "based on available data",
    "according to the retrieved",
    "the tools indicate",
    "from the query results",
]

# Numeris, kuris gali buti netikras arba nepatikimas
_NUMBER_PATTERN = re.compile(r"\$?[\d,]+(?:\.\d+)?(?:\s*(?:million|billion|%|M|B))?")

def check_output(
    response_text: str,
    tool_results: list[dict],
    tools_called: list[str],
) -> OutputQualityReport:
    """Assess quality and hallucination risk of agent output."""
    issues = []
    suggestions = []
    risk_points = 0

    text_lower = response_text.lower()

    # 1.
    numbers_in_response = _NUMBER_PATTERN.findall(response_text)
    if numbers_in_response and not tools_called:
        issues.append(f"Response contains {len(numbers_in_response)} numeric claims but no tools were called")
        suggestions.append("Verify all numeric claims are grounded in tool output")
        risk_points += 30

    # 2.
    for pattern in _HALLUCINATION_SIGNALS:
        if re.search(pattern, text_lower):
            issues.append(f"Hedging/uncertainty language detected: matches '{pattern}'")
            risk_points += 10

    # 3.
    if tool_results:
        tool_numbers = set()
        for result in tool_results:
            raw = json.dumps(result)
            for m in _NUMBER_PATTERN.findall(raw):
                cleaned = m.replace(",", "").replace("$", "").strip()
                tool_numbers.add(cleaned)

        unverified = 0
        for num in numbers_in_response:
            cleaned = num.replace(",", "").replace("$", "").strip()
            # <200 leidimas
            try:
                if float(cleaned) < 200:
                    continue
            except ValueError:
                pass
            if cleaned not in tool_numbers:
                unverified += 1

        if unverified > 2:
            issues.append(f"{unverified} large numeric values in response not traceable to tool output")
            suggestions.append("Cross-reference all figures with retrieved data")
            risk_points += min(unverified * 8, 25)

    # 4.
    word_count = len(response_text.split())
    if word_count < 20 and tools_called:
        issues.append("Very short response after tool use — may be incomplete")
        suggestions.append("Ensure response summarises all tool findings")
        risk_points += 10
    elif word_count > 800:
        suggestions.append("Response is long — consider a summary section")

    # 5. 
    if any(phrase in text_lower for phrase in _UNCERTAINTY_PHRASES):
        risk_points = max(0, risk_points - 10)

    # Finaliniai skaiciai
    risk_points = min(risk_points, 100)
    score = round(1.0 - (risk_points / 100), 2)
    passed = score >= 0.6

    if risk_points < 20:
        hallucination_risk = "low"
    elif risk_points < 50:
        hallucination_risk = "medium"
    else:
        hallucination_risk = "high"

    return OutputQualityReport(
        passed=passed,
        score=score,
        hallucination_risk=hallucination_risk,
        issues=issues,
        suggestions=suggestions,
    )

