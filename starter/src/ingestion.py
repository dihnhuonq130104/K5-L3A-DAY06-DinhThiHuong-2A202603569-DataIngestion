"""Read and normalize source data. implement functions."""
from pathlib import Path
import re
import unicodedata
from pypdf import PdfReader
from .models import DocumentPage


def load_pdf(path: Path, document_id: str, source: str) -> list[DocumentPage]:
    """extract each physical page; keep its page number and source.

    Detect and record pages with no text. OCR, when needed, is a separate step.
    """
    reader = PdfReader(path)
    pages = []
    for number, raw in enumerate(reader.pages, 1):
        text = normalize_text(raw.extract_text() or "")
        pages.append(DocumentPage(document_id, source, number, text,
                                  {"extraction_status": "ok" if text else "empty"}))
    return pages


def normalize_text(text: str) -> str:
    """normalize Unicode and whitespace without discarding useful structure."""
    text = unicodedata.normalize("NFKC", text).replace("\u00ad", "")
    lines = []
    for line in text.splitlines():
        if line.strip() == "Access for free at openstax.org":
            continue
        if re.match(r"^\s*\d+\s*[•·]\s*(Decisions|Loops)\s*$", line):
            continue
        if re.match(r"^\s*[45]\.\d+\s*[•·].*\d+\s*$", line):
            continue
        lines.append(line.rstrip())
    return re.sub(r"\n{3,}", "\n\n", "\n".join(lines)).strip()
