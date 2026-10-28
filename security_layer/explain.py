from __future__ import annotations
import re
from security_layer.document_scanner import INJECTION_RE, ZERO_WIDTH_RE

def explain_result(text: str, result: dict) -> dict:
    spans = []
    for match in INJECTION_RE.finditer(text):
        spans.append(match.group(0))
    if ZERO_WIDTH_RE.search(text):
        spans.append("Zero-width / bidirectional control characters")
    for item in result.get("evidence", []) or []:
        if isinstance(item, dict) and item.get("span"):
            spans.append(str(item["span"]))
    spans = list(dict.fromkeys(spans))[:20]
    action = result.get("action", "UNKNOWN")
    attack_type = result.get("attack_type", "unknown")
    score = float(result.get("risk_score", 0.0) or 0.0)
    summary = f"Decision: {action}. Risk score: {score:.4f}. Attack category: {attack_type}. "
    summary += "This is a heuristic explanation from matching indicators and detector evidence, not a causal explanation of the ML model."
    return {"summary": summary, "spans": spans}
