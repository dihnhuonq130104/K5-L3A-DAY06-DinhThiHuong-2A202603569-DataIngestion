"""Shared frozen-input, embedding-cache and usage utilities."""
import hashlib
import json
from .project import ROOT,RESULTS,read_json,write_json,digest,now,config


def validate_frozen():
    frozen = read_json(ROOT/'benchmark/freeze.json')
    for name,path in [('questions_sha256', ROOT/'benchmark/questions.json'), ('config_sha256', ROOT/'configs/experiment.json'), ('pdf_sha256', ROOT/config()['pdf'])]:
        if frozen[name] != digest(path):
            raise ValueError(f'Frozen input changed: {name}; disclose a new experiment.')
    return frozen


def cached_embed(embedder, texts):
    cache = ROOT/'.cache/api_embeddings'
    cache.mkdir(parents=True, exist_ok=True)
    keys = [hashlib.sha256(f'{embedder.model_name}:{embedder.dimensions}:{text}'.encode()).hexdigest() for text in texts]
    missing = {key:text for key,text in zip(keys,texts) if not (cache/f'{key}.json').exists()}
    pairs = list(missing.items())
    for start in range(0,len(pairs),32):
        batch = pairs[start:start+32]
        vectors = embedder.embed_documents([text for _,text in batch])
        for (key,_),vector in zip(batch,vectors):
            write_json(cache/f'{key}.json',vector)
    return [read_json(cache/f'{key}.json') for key in keys]


def append_usage(stage,tokens,extra=None):
    RESULTS.mkdir(exist_ok=True)
    with (RESULTS/'usage.jsonl').open('a',encoding='utf-8') as f:
        f.write(json.dumps({'at':now(),'stage':stage,'embedding_tokens':tokens,'embedding_estimated_usd':tokens*.02/1_000_000,**(extra or {})},ensure_ascii=False)+'\n')
