"""Rebuild the frozen selected indices and reproduce the recorded benchmark."""
import argparse
from .project import ROOT,RESULTS,read_json,write_json,now
from .pipeline import validate_frozen,cached_embed,append_usage
from .embeddings import MyEmbedder
from .chroma_store import ChromaStore
from .models import Chunk
from .experiment import indexed_text,query_text,validate
from .evaluation import evaluate_query


def ingest():
    validate_frozen();validate()
    info=read_json(RESULTS/'ingestion.json')
    embedder=MyEmbedder()
    assert (embedder.model_name,embedder.dimensions)==(info['model'],info['dimensions'])
    for strategy in ['A','B']:
        chunks=[Chunk(**c) for c in read_json(RESULTS/f'chunks_{strategy}.json')]
        vectors=cached_embed(embedder,[indexed_text(c) for c in chunks])
        store=ChromaStore(ROOT/'.chroma',info['collections'][strategy],embedder.dimensions)
        count=store.replace(chunks,vectors)
        assert store.replace(chunks,vectors)==count==len(chunks)
        print(strategy,'index verified:',count,'chunks')
    append_usage('rebuild_selected_indices',embedder.total_tokens)


def benchmark():
    validate_frozen();validate()
    info=read_json(RESULTS/'ingestion.json')
    embedder=MyEmbedder()
    assert (embedder.model_name,embedder.dimensions)==(info['model'],info['dimensions'])
    questions=read_json(ROOT/'benchmark/questions.json')
    vectors=cached_embed(embedder,[query_text(q['question']) for q in questions])
    expected={(r['strategy'],r['question_id']):r for r in read_json(RESULTS/'traces.json')}
    rows=[]
    for strategy in 'ABC':
        store=ChromaStore(ROOT/'.chroma',info['collections'][strategy],embedder.dimensions)
        for q,vector in zip(questions,vectors):
            scope=q.get('filter') if strategy=='C' else None
            hits=store.search(vector,filters=scope)
            row={**evaluate_query(q,hits),'strategy':strategy,'applied_filter':scope}
            before=expected[strategy,q['id']]
            row['same_metrics']=(row['hit1'],row['hit3'])==(before['hit1'],before['hit3'])
            row['same_top3']=[h['chunk_id'] for h in hits]==[h['chunk_id'] for h in before['hits']]
            rows.append(row)
    result={'at':now(),'all_metrics_identical':all(r['same_metrics'] for r in rows),
            'all_top3_identical':all(r['same_top3'] for r in rows),'traces':rows}
    write_json(RESULTS/'reproduction.json',result)
    append_usage('benchmark_reproduction',embedder.total_tokens)
    assert result['all_metrics_identical'] and result['all_top3_identical'],'Inspect results/reproduction.json for drift'
    print('All 75 ABC traces reproduced with identical metrics and top-3 IDs.')


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('command',choices=['ingest','benchmark','all'])
    args=parser.parse_args()
    if args.command in ['ingest','all']:ingest()
    if args.command in ['benchmark','all']:benchmark()
