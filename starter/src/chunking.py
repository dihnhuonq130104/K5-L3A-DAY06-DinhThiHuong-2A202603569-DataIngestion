"""Implement fixed-size and structure-aware chunking."""
from .models import Chunk, DocumentPage
import hashlib
import re


def make_chunk(page, text, start, end, method):
    key = f"{page.document_id}:{page.page}:{method}:{start}:{end}:{text}"
    return Chunk(hashlib.sha256(key.encode()).hexdigest()[:24], page.document_id,
                 page.source, page.page, text,
                 {**page.metadata, "char_start": start, "char_end": end,
                  "chunk_method": method, "attribution": "Access for free at openstax.org"})


def fixed_size(page: DocumentPage, size: int, overlap: int) -> list[Chunk]:
    """split text into overlapping windows and retain page metadata."""
    if size <= 0 or not 0 <= overlap < size:
        raise ValueError("Require size > overlap >= 0")
    chunks = []
    start = 0
    while start < len(page.text):
        end = min(start + size, len(page.text))
        chunks.append(make_chunk(page, page.text[start:end], start, end, "fixed"))
        if end == len(page.text):
            break
        start = end - overlap
    return chunks


def by_paragraph(page: DocumentPage, max_size: int) -> list[Chunk]:
    """group paragraphs, split oversized paragraphs and retain metadata."""
    if max_size <= 0:
        raise ValueError("max_size must be positive")
    # PDF extraction wraps prose at physical lines. Prefer sentence/newline
    # boundaries rather than assuming PDF blank lines are reliable paragraphs.
    text, chunks, start = page.text, [], 0
    while start < len(text):
        limit = min(start + max_size, len(text))
        end = limit
        if limit < len(text):
            segment = text[start:limit]
            boundaries = [m.end() for m in re.finditer(r"[.!?](?=\s)|\n(?=[A-Z#•])", segment)
                          if m.end() >= max_size // 2]
            if boundaries:
                end = start + boundaries[-1]
            else:
                space = text.rfind(" ", start + max_size // 2, limit)
                if space > start:
                    end = space
        chunks.append(make_chunk(page, text[start:end], start, end, "sentence_paragraph"))
        start = end
    return chunks
