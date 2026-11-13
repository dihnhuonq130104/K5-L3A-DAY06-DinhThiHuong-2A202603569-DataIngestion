"""Offline consistency checks for the English ABC submission; no API calls."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from starter.src.project import ROOT,RESULTS,read_json,write_json,digest,now
from starter.src.pipeline import validate_frozen
from starter.src.experiment import validate
from starter.src.evaluation import evaluate_query,summarize,compact
from starter.src.source_links import source_links


def main():
    validate_frozen();validate()
    final=read_json(ROOT/'report/finalization.json')
    assert digest(ROOT/final['report'])==final['sha256'],'Finalized report hash mismatch'
    report=(ROOT/final['report']).read_text(encoding='utf-8-sig')
    questions=read_json(ROOT/'benchmark/questions.json')
    assert questions==read_json(ROOT/'benchmark/english_questions.json')
    assert len(questions)==25 and sum(q['split']=='dev' for q in questions)==15
    pages={p['page']:p for p in read_json(ROOT/'data/processed/pages.json')}
    assert len(pages)==43
    for q in questions:
        assert compact(q['evidence_quote']) in compact(pages[q['gold_page']]['text'])
        assert q['question'].isascii(),q['id']
    qs={q['id']:q for q in questions}
    traces=read_json(RESULTS/'traces.json')
    assert len(traces)==75
    for row in traces:
        assert len(row['hits'])==3
        q=qs[row['question_id']]
        for hit in row['hits']:
            m=hit['metadata'];page=pages[m['page']]
            assert hit['text']==page['text'][m['char_start']:m['char_end']]
            assert m['printed_page']==m['page']-10 and m['chapter']==page['metadata']['chapter']
            assert source_links(hit)
            if row['strategy']=='C' and q.get('filter'):assert m['chapter']==q['filter']['chapter']
        check=evaluate_query(q,row['hits'])
        assert (check['hit1'],check['hit3'])==(row['hit1'],row['hit3'])
    metrics=summarize(traces)
    assert metrics==read_json(RESULTS/'metrics.json')
    for row in metrics:
        line=f"| {row['strategy']} | {row['split']} | {row['hit1_n']}/{row['n']} | {row['hit3_n']}/{row['n']} ({row['hit3']:.0%}) |"
        assert line in report,f"Report retrieval table differs: {row['strategy']}/{row['split']}"
    import statistics
    from collections import defaultdict,Counter
    for strategy in 'ABC':
        chunks=read_json(RESULTS/f'chunks_{"B" if strategy=="C" else strategy}.json')
        lengths=[len(c['text']) for c in chunks]
        line=f"| {strategy} | {len(chunks)} | {min(lengths)} | {max(lengths)} | {statistics.mean(lengths):.1f} | {sum(lengths)} |"
        assert line in report,f'Report chunk statistics differ: {strategy}'

    for strategy in ['A','B']:
        for c in read_json(RESULTS/f'chunks_{strategy}.json'):
            assert len(c['text'])<=1800
            assert c['text']==pages[c['page']]['text'][c['metadata']['char_start']:c['metadata']['char_end']]
    audit=read_json(RESULTS/'qualitative_audit.json')
    assert audit['human_confirmed'] is False
    assert audit['checks']=={'source_pages':43,'gold_quotes':25,'coherence_rows':30,'grounding_rows':30,'metadata_rows':90}
    for group in ['coherence','grounding']:
        assert all(r['score'] in [0,1,2] and r['reason'] for r in audit[group])
    assert len(audit['metadata'])==90 and all(r['correct'] for r in audit['metadata'])
    for strategy in 'ABC':
        anchors=defaultdict(list)
        for row in audit['coherence']:
            if row['strategy']==strategy:anchors[(row['page'],row['anchor'])].append(row['score'])
        mean=statistics.mean(statistics.mean(v) for v in anchors.values())
        grounding=[r['score'] for r in audit['grounding'] if r['strategy']==strategy]
        counts=Counter(grounding)
        md=[r for r in audit['metadata'] if r['strategy']==strategy]
        filtered=[r for r in traces if r['strategy']==strategy and r['split']=='test' and r['filter']]
        compliant=sum(all(h['metadata']['chapter']==r['filter']['chapter'] for h in r['hits']) for r in filtered)
        line=f"| {strategy} | {mean:.2f}/2 | {counts[0]}/{counts[1]}/{counts[2]} | {statistics.mean(grounding):.2f}/2 | {sum(r['correct'] for r in md)}/{len(md)} | {compliant}/{len(filtered)} |"
        assert line in report,f'Report qualitative table differs: {strategy}'
    record=read_json(RESULTS/'verification.json') if (RESULTS/'verification.json').exists() else {}
    record.update({'at':now(),'frozen_hashes':'pass','source_pages':43,'questions':25,'dev':15,'test':10,
       'traces':75,'top3_source_spans_verified':225,'metrics_recomputed':'pass','chunk_source_spans':'pass',
       'source_section_links':'pass','chapter_filter':'pass','assisted_labels_complete':True,'human_review_claimed':False,
       'test_note':'Selection fixed on dev; AI-assisted test authoring from the same book is not external validation.',
       'finalized_report_sha256':final['sha256'],'report_metric_chunk_and_qualitative_tables':'pass'})
    write_json(RESULTS/'verification.json',record)
    print('PASS: frozen hashes, 25 gold quotes, 75 traces, 225 exact source spans, section links, filters, metrics and finalized report tables.')


if __name__=='__main__':main()
