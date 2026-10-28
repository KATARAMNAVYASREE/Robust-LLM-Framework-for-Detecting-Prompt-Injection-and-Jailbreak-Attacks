from __future__ import annotations
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from app.detector import analyze_text
from security_layer.document_scanner import scan_document
from security_layer.audit_log import init_db, log_event

app = FastAPI(title="Robust LLM Security Shield API", version="2.0.0",
              description="Local prompt/document security middleware. No paid API required.")
init_db()

class AnalyzeRequest(BaseModel):
    text: str = Field(min_length=1, max_length=100000)
    language: str = "Auto / mixed"
    source: str = "api"

class DocumentRequest(BaseModel):
    filename: str = "document.txt"
    content: str = Field(min_length=1, max_length=2000000)
    language: str = "document"

def _analyze(text, language, source):
    result = analyze_text(text)
    action = str(result.get("action") or result.get("decision") or ("BLOCK" if result.get("is_attack") else "ALLOW")).upper()
    score = float(result.get("risk_score", result.get("risk", 0.0)) or 0.0)
    score = max(0.0, min(1.0, score))
    log_event(source, language, action, score, str(result.get("attack_type", "unknown")))
    return {**result, "action": action, "risk_score": score}

@app.get("/health")
def health():
    return {"status": "ok", "service": "Robust LLM Security Shield", "paid_api_required": False}

@app.post("/analyze")
def analyze(request: AnalyzeRequest):
    try:
        return _analyze(request.text, request.language, request.source)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Detector failed: {exc}")

@app.post("/scan-document")
def scan_doc(request: DocumentRequest):
    try:
        scan = scan_document(request.filename, request.content)
        result = _analyze(scan["text_for_detector"], request.language, "document_scan")
        result["structural_findings"] = scan["structural_findings"]
        if scan["structural_findings"] and result["action"] == "ALLOW":
            result["action"] = "REVIEW"
            result["structural_review_override"] = True
        return {"filename": request.filename, "character_count": len(request.content),
                "structural_findings": scan["structural_findings"], "detector_result": result}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Document scan failed: {exc}")
