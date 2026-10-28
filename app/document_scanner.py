
import re
from html import unescape
from pathlib import Path
from typing import Any

from bs4 import BeautifulSoup, Comment

from app.detector import analyze_text


MAX_DOCUMENT_BYTES = 5 * 1024 * 1024  # 5 MB
CHUNK_SIZE = 1000
CHUNK_OVERLAP = 100

SUPPORTED_EXTENSIONS = {".txt", ".pdf", ".html", ".htm"}


def extract_html_content(html_text: str) -> dict:
    """Extract visible text, comments and hidden HTML text separately."""

    soup = BeautifulSoup(html_text, "html.parser")

    # Extract HTML comments before removing them from the document tree.
    comments = [
        str(node).strip()
        for node in soup.find_all(
            string=lambda value: isinstance(value, Comment)
        )
        if str(node).strip()
    ]

    hidden_parts = []

    for element in soup.find_all(True):
        style = element.get("style", "")
        style_compact = re.sub(r"\s+", "", style.lower())

        is_hidden = (
            element.has_attr("hidden")
            or str(element.get("aria-hidden", "")).lower() == "true"
            or "display:none" in style_compact
            or "visibility:hidden" in style_compact
        )

        if is_hidden:
            hidden_text = element.get_text(" ", strip=True)
            if hidden_text:
                hidden_parts.append(hidden_text)

    # Remove script/style content from normal visible text.
    for element in soup(["script", "style", "noscript"]):
        element.decompose()

    visible_text = soup.get_text(" ", strip=True)

    return {
        "visible_text": unescape(visible_text),
        "html_comments": comments,
        "hidden_text": hidden_parts,
    }


def extract_document_content(
    filename: str,
    content: bytes,
) -> dict:
    """Extract text from supported document formats."""

    if len(content) > MAX_DOCUMENT_BYTES:
        raise ValueError("File exceeds the 5 MB size limit.")

    extension = Path(filename).suffix.lower()

    if extension not in SUPPORTED_EXTENSIONS:
        raise ValueError(
            "Unsupported file type. Upload TXT, PDF, HTML or HTM."
        )

    if extension == ".txt":
        text = content.decode("utf-8-sig", errors="replace")

        return {
            "visible_text": text,
            "html_comments": [],
            "hidden_text": [],
        }

    if extension in {".html", ".htm"}:
        html_text = content.decode("utf-8-sig", errors="replace")
        return extract_html_content(html_text)

    # PDF extraction
    from io import BytesIO
    from pypdf import PdfReader

    reader = PdfReader(BytesIO(content))

    if reader.is_encrypted:
        raise ValueError(
            "Encrypted PDFs are not supported. Upload an unencrypted PDF."
        )

    page_texts = []

    for page_number, page in enumerate(reader.pages, start=1):
        page_text = page.extract_text() or ""

        if page_text.strip():
            page_texts.append(
                f"[Page {page_number}]\n{page_text}"
            )

    return {
        "visible_text": "\n\n".join(page_texts),
        "html_comments": [],
        "hidden_text": [],
    }


def split_into_chunks(
    text: str,
    chunk_size: int = CHUNK_SIZE,
    overlap: int = CHUNK_OVERLAP,
) -> list[str]:
    """Split text into overlapping chunks."""

    text = text.strip()

    if not text:
        return []

    if chunk_size <= 0:
        raise ValueError("chunk_size must be positive.")

    if overlap < 0 or overlap >= chunk_size:
        raise ValueError(
            "overlap must be non-negative and smaller than chunk_size."
        )

    chunks = []
    start = 0

    while start < len(text):
        end = min(start + chunk_size, len(text))
        chunks.append(text[start:end])

        if end == len(text):
            break

        start = end - overlap

    return chunks


def scan_document_text(
    extracted: dict[str, Any],
) -> dict:
    """
    Scan normal text, HTML comments and hidden text separately.

    Each chunk is analyzed by the existing Stage 3 detector.
    """

    sources = [
        ("document_text", extracted.get("visible_text", "")),
    ]

    sources.extend(
        ("html_comment", text)
        for text in extracted.get("html_comments", [])
    )

    sources.extend(
        ("hidden_html_text", text)
        for text in extracted.get("hidden_text", [])
    )

    chunk_results = []

    for source_type, source_text in sources:
        chunks = split_into_chunks(source_text)

        for chunk_number, chunk in enumerate(chunks, start=1):
            result = analyze_text(chunk)

            chunk_results.append({
                "source_type": source_type,
                "chunk_number": chunk_number,
                "is_attack": result["is_attack"],
                "risk_score": result["risk_score"],
                "action": result["action"],
                "attack_type": result["attack_type"],
                "evidence": result["evidence"],
                "normalization": result["normalization"],
                "normalized_text": result["normalized_text"],
            })

    if not chunk_results:
        raise ValueError(
            "No extractable text was found in the document."
        )

    # Aggregate all chunk decisions.
    risk_score = max(
        item["risk_score"] for item in chunk_results
    )

    if any(item["action"] == "BLOCK" for item in chunk_results):
        action = "BLOCK"
    elif any(item["action"] == "REVIEW" for item in chunk_results):
        action = "REVIEW"
    else:
        action = "ALLOW"

    suspicious_chunks = [
        item for item in chunk_results
        if item["is_attack"] or item["action"] != "ALLOW"
    ]

    return {
        "is_attack": any(
            item["is_attack"] for item in chunk_results
        ),
        "risk_score": round(risk_score, 4),
        "action": action,
        "total_chunks": len(chunk_results),
        "suspicious_chunk_count": len(suspicious_chunks),
        "suspicious_chunks": suspicious_chunks,
        "chunk_results": chunk_results,
    }


def scan_uploaded_document(
    filename: str,
    content: bytes,
) -> dict:
    """Extract and scan a complete uploaded document."""

    extracted = extract_document_content(filename, content)
    result = scan_document_text(extracted)

    result["filename"] = Path(filename).name
    result["extraction_summary"] = {
        "visible_text_characters": len(
            extracted["visible_text"]
        ),
        "html_comments_found": len(
            extracted["html_comments"]
        ),
        "hidden_text_blocks_found": len(
            extracted["hidden_text"]
        ),
    }

    return result
