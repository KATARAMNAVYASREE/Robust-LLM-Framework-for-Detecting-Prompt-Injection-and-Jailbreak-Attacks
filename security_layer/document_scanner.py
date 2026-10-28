from __future__ import annotations
import base64
import html
import json
import re
import unicodedata
from bs4 import BeautifulSoup, Comment

ZERO_WIDTH_RE = re.compile(r"[\u200b-\u200f\u202a-\u202e\u2060-\u206f\ufeff]")
INJECTION_RE = re.compile(
    r"(ignore|disregard|override|forget)\s+(all\s+)?(previous|prior|above|system)\s+"
    r"(instructions?|rules?|messages?)|reveal\s+(the\s+)?(system prompt|secrets?|hidden instructions?)|"
    r"bypass\s+(safety|security|restrictions?)",
    re.I,
)

def _decode_base64_candidates(text: str):
    found = []
    for token in re.findall(r"(?<![A-Za-z0-9+/])[A-Za-z0-9+/]{20,}={0,2}(?![A-Za-z0-9+/])", text):
        try:
            decoded = base64.b64decode(token, validate=True).decode("utf-8", errors="ignore")
            if decoded and INJECTION_RE.search(decoded):
                found.append(decoded[:300])
        except Exception:
            pass
    return found

def scan_document(filename: str, content: str) -> dict:
    findings = []
    ext = filename.lower().rsplit(".", 1)[-1] if "." in filename else ""
    normalized = unicodedata.normalize("NFKC", content)
    if ZERO_WIDTH_RE.search(content):
        findings.append({"type": "zero_width_or_bidi_control", "detail": "Zero-width or bidirectional control characters were found."})
        normalized = ZERO_WIDTH_RE.sub("", normalized)

    detector_text = normalized
    if ext in {"html", "htm"} or "<html" in content.lower() or "<!doctype html" in content.lower():
        soup = BeautifulSoup(content, "html.parser")
        comments = [str(node) for node in soup.find_all(string=lambda node: isinstance(node, Comment))]
        for comment in comments:
            if INJECTION_RE.search(html.unescape(comment)):
                findings.append({"type": "suspicious_html_comment", "detail": "An HTML comment contains instruction-override language."})
        hidden_nodes = soup.select("[hidden], [aria-hidden='true'], [style*='display:none'], [style*='display: none'], [style*='visibility:hidden'], [style*='visibility: hidden']")
        for node in hidden_nodes:
            hidden_text = node.get_text(" ", strip=True)
            if hidden_text and INJECTION_RE.search(hidden_text):
                findings.append({"type": "suspicious_hidden_html_text", "detail": "Hidden HTML element contains instruction-override language."})
        for node in soup.find_all(["script", "style", "noscript"]):
            hidden_text = node.get_text(" ", strip=True)
            if hidden_text and INJECTION_RE.search(hidden_text):
                findings.append({"type": "suspicious_script_or_style", "detail": f"Suspicious instruction-like text in <{node.name}> content."})
        detector_text = soup.get_text(" ", strip=True) + "\n" + "\n".join(comments)
        # Include hidden text to ensure detector sees it, while recording its structural origin.
        detector_text += "\n" + "\n".join(n.get_text(" ", strip=True) for n in hidden_nodes)
    elif ext == "json":
        try:
            obj = json.loads(content)
            detector_text = json.dumps(obj, ensure_ascii=False)
        except Exception:
            detector_text = normalized

    for decoded in _decode_base64_candidates(content):
        findings.append({"type": "base64_obfuscated_instruction", "detail": f"Base64 content decodes to instruction-like text: {decoded}"})
        detector_text += "\n" + decoded

    if INJECTION_RE.search(detector_text) and not any(f["type"] == "suspicious_html_comment" for f in findings):
        findings.append({"type": "instruction_like_text", "detail": "Instruction-override language found in document text."})

    # Stable de-duplication
    unique = []
    seen = set()
    for f in findings:
        key = (f["type"], f["detail"])
        if key not in seen:
            seen.add(key); unique.append(f)
    return {"filename": filename, "text_for_detector": detector_text, "structural_findings": unique}
