"""ABC: larger page chunks, section-aware B, shared context embeddings.

Preserves all original A/B/C and D artifacts. Select sizes using original dev
only. Freeze a fresh 10-question test before any v2 retrieval. No gold in ranking.
"""
from dataclasses import asdict
import json
import re
import time
from .project import ROOT,RESULTS,read_json,write_json,digest,now
from .models import DocumentPage
from .chunking import fixed_size,by_paragraph
from .source_links import page_sections,source_links
from .hybrid import GLOSSARY
from .embeddings import MyEmbedder
from .chroma_store import ChromaStore
from .pipeline import cached_embed,append_usage,validate_frozen
from .evaluation import evaluate_query,compact

OUT=RESULTS/'english_run'
PLAN=ROOT/'configs/english_plan.json'
QUESTIONS=ROOT/'benchmark/english_questions.json'


def query_text(question):
    return question.strip()


def chunks_for(strategy,size):
    pages=[DocumentPage(**p) for p in read_json(ROOT/'data/processed/pages.json')]
    chunks=[]
    for page in pages:
        if strategy=='A':
            chunks.extend(fixed_size(page,size,200))
        else:
            for left,right,section in page_sections()[page.page][1]:
                part=DocumentPage(page.document_id,page.source,page.page,page.text[left:right],page.metadata)
                batch=by_paragraph(part,size)
                for chunk in batch:
                    chunk.metadata['char_start']+=left
                    chunk.metadata['char_end']+=left
                    chunk.metadata['section']=section
                    chunk.metadata['chunk_method']='section_sentence_v2'
                chunks.extend(batch)
    return chunks


def indexed_text(chunk):
    data=asdict(chunk)
    data['metadata'].update(page=chunk.page)
    sections=', '.join(title for title,_ in source_links(data))
    text=chunk.text
    # Index-only cleanup; returned evidence remains byte-for-byte source text.
    text=re.sub(r'https?://\S+',' ',text)
    text=re.sub(r'(?m)^.*; ch \d+, video \d+.*$','',text)
    text=re.sub(r'(?m)^\d+\s+[45] • (?:Decisions|Loops)\s*$','',text)
    return f"Introduction to Python Programming. Chapter: {chunk.metadata['chapter']}. Sections: {sections}.\n{text}"


def prepare():
    if PLAN.exists() or QUESTIONS.exists():raise ValueError('ABC already prepared')
    validate_frozen()
    original=[q for q in read_json(ROOT/'benchmark/questions.json') if q['split']=='dev']
    specs=[
     (100,'Theo PEP 8 trong Decisions, thân if nên thụt vào mấy dấu cách?',
      'Bốn dấu cách cho mỗi mức thụt lề.','The PEP 8 style guide\nrecommends four spaces per indentation level.','Decisions'),
     (102,'else phải có mức thụt lề như thế nào so với if đi kèm?',
      'Cùng mức thụt lề với if; phần thân else thụt vào.',
      'Note: The else statement is at the\nsame level of indentation as the if statement, and the body is indented.',None),
     (106,'Nếu is_on ban đầu là True thì lệnh is_on = not is_on đổi nó thành gì?',
      'False: not đảo giá trị Boolean.',
      "not is a useful operator that can make a condition more readable and can be used to toggle a Boolean's value.\nEx: is_on = not is_on.",None),
     (110,'Trong Decisions, PEP 8 có khuyến nghị đặt khoảng trắng ngay bên trong ngoặc đơn không?',
      'Không, tránh khoảng trắng ngay bên trong ngoặc.',
      '• Avoid spaces immediately inside parentheses.\nAvoid: x = ( 4 * y )\nBetter: x = (4 * y)','Decisions'),
     (120,'Với x=100 và offset=10, result = x + offset if x < 100 else x - offset cho kết quả nào?',
      '90 vì điều kiện x < 100 là False.',
      'Given x = 100 and offset = 10, what is the value of result?\nresult = x + offset if x < 100 else x - offset',None),
     (127,'Trong Loops, step size âm làm biến đếm tăng hay giảm?',
      'Giảm theo thứ tự giảm dần.',
      'if the step size\nis a negative number, the counter counts in descending order.','Loops'),
     (131,'Dùng range với các đối số nào để lấy mọi số nguyên từ 5 xuống 1, có cả 1?',
      'range(5, 0, -1).',
      'What are the arguments to the range() function for the decreasing sequence of every integer from 5\nto 1 (inclusive of both ends)?\na. range(5, 1, 1)\nb. range(5, 1, -1)\nc. range(5, 0, -1)',None),
     (133,'Ví dụ lịch hẹn mỗi 30 phút từ 8 giờ đến trước 10 giờ in ra những thời điểm nào?',
      '8:00, 8:30, 9:00 và 9:30.',
      "The above code's output is:\n8 : 0\n8 : 30\n9 : 0\n9 : 30",None),
     (136,'Trong Loops có thể đặt while bên trong for để tạo vòng lặp lồng nhau không?',
      'Có, sách cho ví dụ for ở ngoài và while ở trong.',
      'The two for and while loop constructs can also be mixed in a nested loop construct.','Loops'),
     (142,'Với numbers = [1, 2, 2, 6], chương trình gặp i >= 5 thì in gì và có chạy loop else không?',
      'In Not all numbers are less than 5. rồi break; không chạy loop else.',
      'numbers = [1, 2, 2, 6]\nfor i in numbers:\n  if i >= 5:\n    print("Not all numbers are less than 5.")\n    break\n  else:\n    print(i)\n    continue\nelse:\n  print("all numbers are less than 5.")',None),
    ]
    pages={p['page']:p['text'] for p in read_json(ROOT/'data/processed/pages.json')}
    new=[]
    for i,(page,question,answer,quote,chapter) in enumerate(specs,1):
        assert compact(quote) in compact(pages[page]),(i,page)
        new.append({'id':f'v2t{i:02}','split':'test','question':question,'expected_answer':answer,
                    'gold_page':page,'gold_source_id':'openstax-python-2026','evidence_quote':quote,
                    'filter':{'chapter':chapter} if chapter else None})
    dev_questions=[
      ('How do zero, an empty string, a nonzero number and a nonempty string convert to bool?', 'Zero and an empty string are False; nonzero numbers and nonempty strings are True.'),
      ('Which Python operators test equality and inequality?', '== tests equality; != tests inequality.'),
      ('How must an if body be indented, and what happens if its body is empty?', 'Indent one level; PEP 8 recommends four spaces. An empty body causes an error.'),
      ('In Decisions, how many condition operands does and take, and when is its result True?', 'Two operands; True only when both conditions are true.'),
      ('How does not transform a Boolean, and what can it be used for?', 'It reverses True/False and can toggle a Boolean or improve readability.'),
      ('Why is 1 + 2 * 3 equal to 7, but (1 + 2) * 3 equal to 9?', 'Multiplication precedes addition; parentheses override that order.'),
      ('Besides changing evaluation order, how do parentheses help a reader?', 'They reduce confusion.'),
      ('When is an elif condition checked, and which statement must it follow?', 'When the previous condition is false; it follows if or elif.'),
      ('What is a nested decision, and how is it indicated in Python?', 'A decision inside another decision, indicated by indentation.'),
      ('What is another name for a conditional expression, and what is its general syntax?', 'Ternary operator: expression_if_true if condition else expression_if_false.'),
      ('How do positive and negative step sizes affect a loop counter?', 'Positive counts upward; negative counts downward.'),
      ('Which types of containers can a for loop iterate over according to the book?', 'A range of numbers, a string of characters, or a list of values.'),
      ('In Loops, does a range include its start and its end?', 'It includes the start and excludes the end.'),
      ('In nested loops, what does the outer loop control about the inner loop?', 'The number of complete executions of the inner loop.'),
      ('In Loops, which loop types support break, and what does break do?', 'for and while; it exits the loop when the triggering condition is reached.'),
    ]
    for i,(q,(question,answer)) in enumerate(zip(original,dev_questions),1):
        q.update(id=f'dev{i:02}',question=question,expected_answer=answer)
    translations=[
      ('According to PEP 8 in Decisions, how many spaces should an if body be indented?', 'Four spaces per indentation level.'),
      ('How is else indented relative to its matching if?', 'At the same indentation level; the else body is indented.'),
      ('If is_on is initially True, what does is_on = not is_on change it to?', 'False; not toggles the Boolean value.'),
      ('In Decisions, does PEP 8 recommend spaces immediately inside parentheses?', 'No. Avoid spaces immediately inside parentheses.'),
      ('With x=100 and offset=10, what is result = x + offset if x < 100 else x - offset?', '90 because x < 100 is false.'),
      ('In Loops, does a negative step size make a counter ascend or descend?', 'Descend.'),
      ('Which range arguments generate every integer from 5 down to 1, including 1?', 'range(5, 0, -1).'),
      ('Which appointment times does the 30-minute example from 8:00 until before 10:00 print?', '8:00, 8:30, 9:00 and 9:30.'),
      ('In Loops, may a while loop be nested inside a for loop?', 'Yes. The book gives a mixed nested-loop example.'),
      ('For numbers = [1, 2, 2, 6], what does the example print when i >= 5, and does loop else run?', 'It prints Not all numbers are less than 5., then breaks. Loop else does not run.'),
    ]
    for i,(q,(question,answer)) in enumerate(zip(new,translations),1):
        q.update(id=f'test{i:02}',question=question,expected_answer=answer)
    write_json(QUESTIONS,original+new)
    plan={'prepared_at':now(),'version':'ABC','profile_sizes':[1000,1400,1800],
          'A':'fixed-size, overlap 200 characters','B':'sentence-aware within exact section spans, no overlap',
          'C':'same chunks/index as B; only user-supplied chapter filter',
          'shared_preprocessing':'English queries throughout. Section/chapter prefix for embedding only; remove URL/video/footer boilerplate from indexed text only. Original evidence text/offsets retained.',
          'embedding_model':'text-embedding-3-small','dimensions':1536,
          'selection_rule':'Choose shared size by total dev Hit@3 across ABC; then total dev Hit@1; then smaller size. Choose strategy by dev Hit@3, then Hit@1, then fewer chunks, then alphabetic.',
          'questions_sha256':digest(QUESTIONS),'code_sha256':digest(ROOT/'starter/src/experiment.py'),
          'glossary_module_sha256':digest(ROOT/'starter/src/hybrid.py'),
          'pages_sha256':digest(ROOT/'data/processed/pages.json'),
          'new_test_not_yet_retrieved':True,'test_not_used_for_selection':True,
          'limitations':'Development used this textbook and a known dev set. Test questions were frozen before retrieval; AI-assisted purposive sampling, not external human evaluation.'}
    write_json(PLAN,plan)
    print('ABC plan and 25 questions frozen: original 15 dev + fresh 10 test, 4 test filters, 5 test questions per chapter.')


def validate():
    validate_frozen()
    plan=read_json(PLAN)
    for path,key in [(QUESTIONS,'questions_sha256'),(ROOT/'starter/src/experiment.py','code_sha256'),
                     (ROOT/'starter/src/hybrid.py','glossary_module_sha256'),(ROOT/'data/processed/pages.json','pages_sha256')]:
        assert digest(path)==plan[key],key
    return plan


def build():
    plan=validate()
    if (OUT/'selection.json').exists():raise ValueError('Selection frozen; use replay instead')
    embedder=MyEmbedder()
    assert (embedder.model_name,embedder.dimensions)==(plan['embedding_model'],plan['dimensions'])
    questions=[q for q in read_json(QUESTIONS) if q['split']=='dev']
    vectors=cached_embed(embedder,[query_text(q['question']) for q in questions])
    profiles=[]
    for size in plan['profile_sizes']:
        stores={};counts={};names={}
        for strategy in ['A','B']:
            chunks=chunks_for(strategy,size)
            name=f'python-en-{strategy.lower()}-{size}-{plan["code_sha256"][:10]}'
            store=ChromaStore(ROOT/'.chroma',name,embedder.dimensions)
            embeddings=cached_embed(embedder,[indexed_text(c) for c in chunks])
            count=store.replace(chunks,embeddings)
            assert store.replace(chunks,embeddings)==count
            stores[strategy]=store;counts[strategy]=count;names[strategy]=name
            write_json(OUT/f'chunks_{strategy}_{size}.json',[asdict(c) for c in chunks])
        stores['C']=stores['B'];counts['C']=counts['B'];names['C']=names['B']
        traces=[]
        for strategy in 'ABC':
            for q,vector in zip(questions,vectors):
                scope=q.get('filter') if strategy=='C' else None
                hits=stores[strategy].search(vector,filters=scope)
                traces.append({**evaluate_query(q,hits),'strategy':strategy,'applied_filter':scope})
        metrics=[{'strategy':s,'n':15,'hit1_n':sum(r['hit1'] for r in traces if r['strategy']==s),
                  'hit3_n':sum(r['hit3'] for r in traces if r['strategy']==s),'chunks':counts[s]} for s in 'ABC']
        profile={'size':size,'metrics':metrics,'collections':names,
                 'total_hit3':sum(r['hit3_n'] for r in metrics),'total_hit1':sum(r['hit1_n'] for r in metrics)}
        profiles.append(profile)
        write_json(OUT/f'dev_{size}.json',traces)
        print('Dev size',size,metrics,flush=True)
    best=sorted(profiles,key=lambda p:(-p['total_hit3'],-p['total_hit1'],p['size']))[0]
    strategy=sorted(best['metrics'],key=lambda r:(-r['hit3_n'],-r['hit1_n'],r['chunks'],r['strategy']))[0]['strategy']
    write_json(OUT/'selection.json',{'selected_at':now(),'plan_sha256':digest(PLAN),'size':best['size'],
        'selected_strategy':strategy,'collections':best['collections'],'profiles':profiles,
        'dev_metrics':best['metrics'],'test_not_yet_retrieved':True,'api_tokens_this_run':embedder.total_tokens})
    append_usage('english_dev_and_ingest',embedder.total_tokens)
    print('Selected size',best['size'],'strategy',strategy,'before fresh test retrieval.')


def test(replay=False):
    validate()
    selection=read_json(OUT/'selection.json')
    assert selection['plan_sha256']==digest(PLAN)
    path=OUT/('replay.json' if replay else 'test_traces.json')
    if path.exists() and not replay:raise ValueError('Test already recorded')
    embedder=MyEmbedder()
    plan=read_json(PLAN)
    assert (embedder.model_name,embedder.dimensions)==(plan['embedding_model'],plan['dimensions'])
    questions=[q for q in read_json(QUESTIONS) if q['split']=='test']
    vectors=cached_embed(embedder,[query_text(q['question']) for q in questions])
    traces=[]
    for strategy in 'ABC':
        store=ChromaStore(ROOT/'.chroma',selection['collections'][strategy],embedder.dimensions)
        for q,vector in zip(questions,vectors):
            scope=q.get('filter') if strategy=='C' else None
            started=time.perf_counter()
            hits=store.search(vector,filters=scope)
            traces.append({**evaluate_query(q,hits),'strategy':strategy,'applied_filter':scope,
                           'retrieval_seconds':time.perf_counter()-started})
    write_json(path,traces)
    if replay:
        original=read_json(OUT/'test_traces.json')
        assert [[h['chunk_id'] for h in t['hits']] for t in traces]==[[h['chunk_id'] for h in t['hits']] for t in original]
        print('Replay: all 30 top-3 results identical to first run.')
    else:
        metrics=[{'strategy':s,'n':10,'hit1_n':sum(r['hit1'] for r in traces if r['strategy']==s),
                  'hit3_n':sum(r['hit3'] for r in traces if r['strategy']==s)} for s in 'ABC']
        write_json(OUT/'summary.json',{'at':now(),'selection':selection['selected_strategy'],'size':selection['size'],
            'dev_metrics':selection['dev_metrics'],'test_metrics':metrics,'api_tokens_test':embedder.total_tokens,
            'limitations':read_json(PLAN)['limitations']})
        print(json.dumps(metrics,ensure_ascii=False,indent=2))
    append_usage('english_replay' if replay else 'english_new_test',embedder.total_tokens)


if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser();parser.add_argument('command',choices=['prepare','build','test','replay'])
    args=parser.parse_args()
    {'prepare':prepare,'build':build,'test':test,'replay':lambda:test(True)}[args.command]()
