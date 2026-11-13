"""evaluate retrieved evidence and preserve per-query traces."""
from typing import Any
import re


def compact(text):
    return re.sub(r"\s+", " ", text).strip()


def evaluate_query(question: dict[str, Any], hits: list[dict[str, Any]]) -> dict[str, Any]:
    """check source/page and enough gold evidence; keep hit@1 and hit@3 trace.

    Accept any documented alternative gold evidence. Do not infer human grounding
    or chunk coherence labels from exact string match.
    """
    golds = question.get("gold_evidence") or [{"source_id": question['gold_source_id'],
        "page": question['gold_page'], "quote": question['evidence_quote']}]
    labels = []
    for hit in hits[:3]:
        metadata = hit['metadata']
        labels.append(any(metadata['document_id'] == g['source_id'] and
                          metadata['page'] == g['page'] and compact(g['quote']) in compact(hit['text'])
                          for g in golds))
    return {"question_id": question['id'], "split": question['split'],
            "question": question['question'], "filter": question.get('filter'),
            "gold_evidence": golds, "expected_answer": question['expected_answer'],
            "hits": hits, "hit_labels": labels,
            "hit1": bool(labels and labels[0]), "hit3": any(labels)}


def summarize(traces: list[dict[str, Any]]) -> dict[str, Any]:
    """aggregate Hit@1 and Evidence Hit@3 by strategy and dev/test split."""
    result = []
    for strategy in sorted({t['strategy'] for t in traces}):
        for split in ['dev', 'test']:
            rows = [t for t in traces if t['strategy']==strategy and t['split']==split]
            n = len(rows)
            result.append({"strategy":strategy,"split":split,"n":n,
                           "hit1_n":sum(t['hit1'] for t in rows),
                           "hit3_n":sum(t['hit3'] for t in rows),
                           "hit1":sum(t['hit1'] for t in rows)/n if n else None,
                           "hit3":sum(t['hit3'] for t in rows)/n if n else None})
    return result
