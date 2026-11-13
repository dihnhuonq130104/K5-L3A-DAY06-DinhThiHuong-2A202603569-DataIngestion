"""Supplementary hybrid retrieval: unchanged B chunks + BM25/weighted RRF.

No gold, question IDs or source-page hints enter ranking. The small bilingual
lexicon maps common programming phrases, not answers, into document vocabulary.
"""
from collections import Counter
import math
import re
import unicodedata

GLOSSARY = {
    'vòng lặp': 'loop', 'điều kiện': 'condition', 'chuỗi': 'string',
    'danh sách': 'list', 'toán tử': 'operator', 'so sánh': 'comparison',
    'thụt lề': 'indentation', 'lồng nhau': 'nested', 'biểu thức': 'expression',
    'ưu tiên': 'precedence', 'gán': 'assignment', 'số nguyên': 'integer',
    'bước nhảy': 'step', 'kết thúc': 'terminate', 'vô hạn': 'infinite',
}
STOP = set('a an the is are was were be been to of in on at by from and or not with '
           'for as this that it its if else then than can may should will do does '
           'what which how when why all any into using used use'.split())
# Python keywords remain searchable even when they are English stopwords.
KEYWORDS = {'and','or','not','for','if','else','while','elif','break','continue','True','False'}
TOKEN = re.compile(r'[a-zA-Z_][a-zA-Z_0-9]*|==|!=|<=|>=|\*\*|//|[<>%]')


def tokens(text):
    normalized = unicodedata.normalize('NFC', text).lower()
    translated = normalized
    for phrase, replacement in GLOSSARY.items():
        translated = translated.replace(phrase, ' ' + replacement + ' ')
    # Drop untranslated Vietnamese words whole (avoid partial ASCII matches).
    words = re.findall(r'[^\W\d]\w*|==|!=|<=|>=|\*\*|//|[<>%]', translated, re.UNICODE)
    return [word for word in words if word.isascii() and TOKEN.fullmatch(word)
            and (word not in STOP or word in {k.lower() for k in KEYWORDS})]


class HybridRanker:
    def __init__(self, chunks):
        self.chunks = {c['chunk_id']: c for c in chunks}
        self.counts = {key: Counter(tokens(c['text'])) for key,c in self.chunks.items()}
        self.lengths = {key: sum(c.values()) for key,c in self.counts.items()}
        self.average = sum(self.lengths.values()) / max(1,len(chunks))
        self.df = Counter(term for counts in self.counts.values() for term in counts)

    def search(self, question, dense_hits, dense_weight=0.5, top_k=3, chapter=None):
        if not 0 <= dense_weight <= 1:
            raise ValueError('dense_weight must be between 0 and 1')
        candidates = {key:c for key,c in self.chunks.items()
                      if chapter is None or c['metadata']['chapter']==chapter}
        dense = [h for h in dense_hits if h['chunk_id'] in candidates]
        query = set(tokens(question))
        scores = {}
        n = len(self.chunks)
        for key in candidates:
            score = 0.0
            for term in query:
                tf = self.counts[key][term]
                if tf:
                    idf = math.log(1 + (n-self.df[term]+0.5)/(self.df[term]+0.5))
                    score += idf * tf * 2.5 / (tf + 1.5*(0.25+0.75*self.lengths[key]/max(1,self.average)))
            if score > 0:
                scores[key] = score
        if not scores or dense_weight == 1:
            return dense[:top_k]
        lexical = sorted(scores,key=lambda key:(-scores[key],key))[:20]
        dense_ranks = {h['chunk_id']:i for i,h in enumerate(dense[:20],1)}
        lex_ranks = {key:i for i,key in enumerate(lexical,1)}
        dense_by_id = {h['chunk_id']:h for h in dense}
        fused = {key: dense_weight/(60+dense_ranks[key]) if key in dense_ranks else 0
                 for key in set(dense_ranks)|set(lex_ranks)}
        for key,rank in lex_ranks.items():
            fused[key] += (1-dense_weight)/(60+rank)
        result = []
        for key in sorted(fused,key=lambda key:(-fused[key],dense_ranks.get(key,999),key))[:top_k]:
            if key not in dense_by_id:
                raise ValueError('Hybrid requires dense scores for all candidate chunks')
            result.append({**dense_by_id[key], 'ranking':'hybrid_rrf',
                           'fusion_score':fused[key], 'dense_rank':dense_ranks.get(key),
                           'lexical_rank':lex_ranks.get(key), 'bm25_score':scores.get(key,0)})
        return result
