"""Resolve PDF chunk spans to the matching OpenStax online sections.

Display-only: keep frozen corpus, embeddings and benchmark traces unchanged.
Section slugs verified against the View online table of contents.
"""
from functools import lru_cache
import re
from .project import ROOT, read_json

BASE = 'https://openstax.org/books/introduction-python-programming/pages/'
SECTIONS = {
    '4.1': ('Boolean values', '4-1-boolean-values'),
    '4.2': ('If-else statements', '4-2-if-else-statements'),
    '4.3': ('Boolean operations', '4-3-boolean-operations'),
    '4.4': ('Operator precedence', '4-4-operator-precedence'),
    '4.5': ('Chained decisions', '4-5-chained-decisions'),
    '4.6': ('Nested decisions', '4-6-nested-decisions'),
    '4.7': ('Conditional expressions', '4-7-conditional-expressions'),
    '5.1': ('While loop', '5-1-while-loop'),
    '5.2': ('For loop', '5-2-for-loop'),
    '5.3': ('Nested loops', '5-3-nested-loops'),
    '5.4': ('Break and continue', '5-4-break-and-continue'),
    '5.5': ('Loop else', '5-5-loop-else'),
    '5.6': ('Chapter summary', '5-6-chapter-summary'),
}


@lru_cache(maxsize=1)
def page_sections():
    pages = read_json(ROOT / 'data/processed/pages.json')
    result = {}
    current = None
    previous = None
    for page in sorted(pages, key=lambda p: p['page']):
        number, text = page['page'], page['text']
        # Selected ranges begin mid-section in the original PDF.
        if previous is None or number != previous + 1:
            current = {96: '4.1', 126: '5.1'}.get(number)
        boundaries = []
        for match in re.finditer(r'(?m)^([45]\.\d+) ([^\n]+)', text):
            section = match.group(1)
            if section in SECTIONS and match.group(2).strip() == SECTIONS[section][0]:
                boundaries.append((match.start(), section))
        spans, start = [], 0
        for offset, section in boundaries:
            if offset > start and current:
                spans.append((start, offset, current))
            start, current = offset, section
        if current and start < len(text):
            spans.append((start, len(text), current))
        result[number] = (text, spans)
        previous = number
    return result


def source_links(hit):
    """Return every online section actually intersecting this retrieved chunk."""
    metadata = hit['metadata']
    record = page_sections().get(int(metadata['page']))
    if record is None:
        return []
    text, spans = record
    start = metadata.get('char_start')
    end = metadata.get('char_end')
    if start is None or end is None:
        start = text.find(hit['text'])
        if start < 0:
            return []
        end = start + len(hit['text'])
    sections = dict.fromkeys(section for left, right, section in spans
                             if int(start) < right and int(end) > left)
    return [(f'{section} {SECTIONS[section][0]}', BASE + SECTIONS[section][1])
            for section in sections]
