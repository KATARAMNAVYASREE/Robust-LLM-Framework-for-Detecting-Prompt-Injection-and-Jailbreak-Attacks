
import re
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, File, HTTPException, Query, UploadFile
from pydantic import BaseModel

from app.database import (
    init_db,
    log_scan,
    get_logs,
    get_summary,
    export_logs_csv,
)
from fastapi.responses import StreamingResponse
from app.detector import analyze_text


app = FastAPI(
    title="Robust LLM Security Framework",
    description="Prompt Injection Detection API",
    version="0.1.0",
)

init_db()


class AnalyzeRequest(BaseModel):
    text: str


def extract_document_chunks(content: str, suffix: str):
    """Extract visible text, HTML comments, and hidden HTML text."""
    comments = []
    hidden_blocks = []

    if suffix in {".html", ".htm", ".html.txt"}:
        comments = re.findall(
            r"<!--(.*?)-->",
            content,
            flags=re.DOTALL,
        )

        hidden_blocks = re.findall(
            r"<([a-zA-Z][\w:-]*)\b([^>]*)>(.*?)</\1\s*>",
            content,
            flags=re.DOTALL | re.IGNORECASE,
        )

        hidden_texts = []
        for _, attributes, inner_text in hidden_blocks:
            if re.search(
                r"display\s*:\s*none|visibility\s*:\s*hidden|"
                r"hidden(?:\s|=|$)|opacity\s*:\s*0",
                attributes,
                flags=re.IGNORECASE,
            ):
                hidden_texts.append(inner_text)

        visible = re.sub(
            r"<!--.*?-->",
            " ",
            content,
            flags=re.DOTALL,
        )
        visible = re.sub(
            r"<script\b[^>]*>.*?</script>",
            " ",
            visible,
            flags=re.DOTALL | re.IGNORECASE,
        )
        visible = re.sub(
            r"<style\b[^>]*>.*?</style>",
            " ",
            visible,
            flags=re.DOTALL | re.IGNORECASE,
        )
        visible = re.sub(r"<[^>]+>", " ", visible)
        visible = re.sub(r"\s+", " ", visible).strip()
    else:
        visible = content.strip()
        hidden_texts = []

    chunks = []

    if visible:
        chunks.append({
            "source_type": "document_text",
            "text": visible,
        })

    for comment in comments:
        if comment.strip():
            chunks.append({
                "source_type": "html_comment",
                "text": comment.strip(),
            })

    for hidden_text in hidden_texts:
        if hidden_text.strip():
            chunks.append({
                "source_type": "hidden_html_text",
                "text": hidden_text.strip(),
            })

    extraction_summary = {
        "visible_text_characters": len(visible),
        "html_comments_found": len(comments),
        "hidden_text_blocks_found": len(hidden_texts),
    }

    return chunks, extraction_summary


@app.get("/")
def root():
    return {
        "name": "Robust LLM Security Framework",
        "status": "running",
    }


@app.get("/health")
def health():
    return {"status": "healthy"}


@app.post("/analyze")
def analyze(request: AnalyzeRequest):
    if not request.text.strip():
        raise HTTPException(
            status_code=422,
            detail="Prompt text cannot be empty.",
        )

    result = analyze_text(request.text)

    log_scan(
        input_text=request.text,
        risk_score=result.get("risk_score", 0),
        confidence=result.get("confidence"),
        attack_type=result.get("attack_type", "none"),
        action=result.get("action", "ALLOW"),
        source="prompt",
        is_attack=result.get("is_attack", False),
        details=result,
    )

    return result


@app.post("/scan-document")
async def scan_document(file: UploadFile = File(...)):
    filename = Path(file.filename or "uploaded.txt").name
    suffix = Path(filename).suffix.lower()

    if suffix not in {".txt", ".html", ".htm"}:
        raise HTTPException(
            status_code=415,
            detail="Upload a TXT, HTML, or HTM file.",
        )

    raw = await file.read(2 * 1024 * 1024 + 1)

    if len(raw) > 2 * 1024 * 1024:
        raise HTTPException(
            status_code=413,
            detail="Maximum upload size is 2 MB.",
        )

    content = raw.decode("utf-8", errors="replace")
    chunks, extraction_summary = extract_document_chunks(
        content,
        suffix,
    )

    results = []

    for index, chunk in enumerate(chunks, start=1):
        detection = analyze_text(chunk["text"])

        results.append({
            "source_type": chunk["source_type"],
            "chunk_number": index,
            "is_attack": bool(detection.get("is_attack", False)),
            "risk_score": float(detection.get("risk_score", 0)),
            "action": detection.get("action", "ALLOW"),
            "attack_type": detection.get("attack_type", "none"),
            "evidence": detection.get("evidence", []),
        })

    suspicious = [
        item for item in results
        if item["is_attack"] or item["action"] in {"BLOCK", "REVIEW"}
    ]

    highest_risk = max(
        (item["risk_score"] for item in results),
        default=0.0,
    )

    if highest_risk >= 0.70:
        action = "BLOCK"
    elif highest_risk >= 0.40:
        action = "REVIEW"
    else:
        action = "ALLOW"

    attack_types = [
        item["attack_type"] for item in suspicious
        if item["attack_type"] not in {"none", "unknown", None}
    ]

    result = {
        "is_attack": bool(suspicious),
        "risk_score": round(highest_risk, 4),
        "action": action,
        "total_chunks": len(chunks),
        "suspicious_chunk_count": len(suspicious),
        "suspicious_chunks": suspicious,
        "filename": filename,
        "extraction_summary": extraction_summary,
        "attack_type": attack_types[0] if attack_types else "none",
    }

    log_scan(
        input_text=f"Document scan: {filename}",
        risk_score=result["risk_score"],
        confidence=None,
        attack_type=result["attack_type"],
        action=result["action"],
        source="document",
        filename=filename,
        is_attack=result["is_attack"],
        details=result,
    )

    return result


@app.get("/admin/summary")
def admin_summary():
    return get_summary()


@app.get("/logs")
def list_logs(
    limit: int = Query(default=500, ge=1, le=5000),
    action: Optional[str] = None,
    attack_type: Optional[str] = None,
    source: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
):
    return {
        "logs": get_logs(
            limit=limit,
            action=action,
            attack_type=attack_type,
            source=source,
            start_date=start_date,
            end_date=end_date,
        )
    }


@app.get("/logs/export")
def download_logs(
    action: Optional[str] = None,
    attack_type: Optional[str] = None,
    source: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
):
    logs = get_logs(
        limit=5000,
        action=action,
        attack_type=attack_type,
        source=source,
        start_date=start_date,
        end_date=end_date,
    )

    csv_text = export_logs_csv(logs)

    return StreamingResponse(
        iter([csv_text]),
        media_type="text/csv",
        headers={
            "Content-Disposition":
                'attachment; filename="security_logs.csv"'
        },
    )
