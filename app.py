"""Streamlit textbook RAG demo: English corpus, questions and interface."""
import pandas as pd
import streamlit as st
from starter.src.project import ROOT,RESULTS,read_json,write_json,now
from starter.src.demo import chat,safe_error
from starter.src.source_links import source_links

st.set_page_config(page_title='Python Book Lab',page_icon=':material/menu_book:',layout='wide')
st.markdown('''<style>
.block-container{max-width:1150px;padding-top:2.5rem;padding-bottom:3rem}
h1{font-family:Georgia,serif;font-weight:500;letter-spacing:-.025em}
[data-testid="stChatMessage"]{background:transparent;border-bottom:1px solid #cdd7d0;border-radius:0;padding:1.2rem 0}
@media(max-width:640px){.block-container{padding-top:1.3rem;padding-left:1rem;padding-right:1rem}}
</style>''',unsafe_allow_html=True)
info=read_json(RESULTS/'ingestion.json')
selection=read_json(RESULTS/'selection.json')
metrics=read_json(RESULTS/'metrics.json')
traces=read_json(RESULTS/'traces.json')
index_ready=(ROOT/'.chroma/chroma.sqlite3').is_file()

with st.sidebar:
    st.header('Python Book Lab')
    st.caption('Đinh Thị Hường · Day 06')
    strategy=st.selectbox('Retrieval strategy',['A','B','C'],index=['A','B','C'].index(selection['selected_strategy']),
        format_func=lambda s:{'A':'A · Fixed windows','B':'B · Section-aware chunks','C':'C · Section-aware + chapter filter'}[s])
    chapter=st.selectbox('Chapter scope',['All chapters','Decisions','Loops'],disabled=strategy!='C')
    st.caption('C applies the chapter you choose. A and B search the full corpus.')
    st.divider()
    st.write('**Introduction to Python Programming**')
    st.caption('OpenStax · 43 content pages · English')
    st.link_button('About the textbook','https://openstax.org/details/books/introduction-python-programming')
    pdf=ROOT/'data/raw/Introduction_to_Python_Programming-WEB.pdf'
    if pdf.is_file():st.download_button('Download source PDF',pdf.read_bytes(),pdf.name,'application/pdf')
    st.caption('Access for free at openstax.org · CC BY-NC-SA 4.0')
    st.caption('text-embedding-3-small · 1536 dimensions\n\nChroma · cosine similarity')
    if st.button('Clear conversation'):
        st.session_state.messages=[]
        st.rerun()

st.title('Ask the book. Inspect the evidence.')
st.write('Explore decisions and loops in Python. Answers use retrieved textbook excerpts with page citations and links to the relevant online sections.')
tabs=st.tabs(['Chat','ABC experiments','Source review'])


def render_sources(hits):
    st.caption('RETRIEVED EVIDENCE · TOP 3')
    for rank,hit in enumerate(hits,1):
        m=hit['metadata']
        with st.expander(f"{rank}. {m['chapter']} · PDF p.{m['page']} / printed p.{m['printed_page']} · cosine {hit['score']:.3f}"):
            st.text(hit['text'])
            st.caption(f"Chunk {hit['chunk_id']} · {m['attribution']}")
            for title,url in source_links(hit):st.link_button(f'View OpenStax source · {title}',url)
    st.caption('Cosine measures vector similarity, not the probability that an answer is correct.')


with tabs[0]:
    if not index_ready:
        st.info('The local vector index is missing. Saved experiment results are available; build the index before chatting.')
        st.code('.\\.venv\\Scripts\\python.exe -m starter.src.run ingest',language='powershell')
    st.caption('GPT-5.4 · English answers grounded in the textbook · API usage is billed')
    scope=(strategy,chapter if strategy=='C' else 'All chapters')
    if st.session_state.get('scope')!=scope:
        st.session_state.scope=scope
        st.session_state.messages=[]
    messages=st.session_state.setdefault('messages',[])
    if not messages:
        st.subheader('What would you like to understand?')
        st.write('Try “How does not toggle a Boolean?” or “When does a loop else block run?”')
    for message in messages:
        with st.chat_message(message['role']):
            st.markdown(message['content'])
            if message.get('hits'):render_sources(message['hits'])
    question=st.chat_input('Ask a question about decisions or loops…',disabled=not index_ready,max_chars=2000)
    if question:
        with st.chat_message('user'):st.markdown(question)
        try:
            with st.chat_message('assistant'):
                with st.spinner('Finding evidence and drafting an answer…'):
                    result=chat(question,strategy,chapter if strategy=='C' and chapter!='All chapters' else None,
                                [{'role':m['role'],'content':m['content']} for m in messages])
                st.markdown(result['answer']);render_sources(result['hits'])
            messages.extend([{'role':'user','content':question},{'role':'assistant','content':result['answer'],'hits':result['hits']}])
        except Exception as exc:st.error(safe_error(exc))

with tabs[1]:
    st.subheader('One corpus. Three retrieval strategies.')
    st.write('A uses 1,800-character windows with 200-character overlap. B respects textbook section boundaries and sentence/line boundaries, up to 1,800 characters. C shares the B index and adds only the requested chapter filter.')
    st.caption('All strategies use the same English queries, model and embedding preprocessing. Excerpts retain the original PDF text and offsets.')
    split=st.radio('Evaluation split',['dev','test'],horizontal=True)
    own=[m for m in metrics if m['split']==split]
    st.dataframe(pd.DataFrame([{'Strategy':m['strategy'],'Hit@1':f"{m['hit1_n']}/{m['n']}",'Evidence Hit@3':f"{m['hit3_n']}/{m['n']}",'Chunks':info['stats'][m['strategy']]['chunk_count']} for m in own]),hide_index=True,width='stretch')
    st.success('Selected on dev: B. Shared size and strategy were fixed before test retrieval.')
    st.caption('15 dev questions; 10 test questions. Exact evidence hit requires the correct source/page and the complete gold quote in one chunk. Retrieval hits do not measure LLM answer accuracy.')
    chosen=st.selectbox('Inspect question',[r['question_id'] for r in traces if r['strategy']=='A' and r['split']==split])
    for row in [r for r in traces if r['question_id']==chosen]:
        with st.expander(f"{row['strategy']} · Hit@1 {row['hit1']} · Hit@3 {row['hit3']}"):
            st.write(row['question']);st.write('Reference answer:',row['expected_answer'])
            st.write('Gold evidence:',row['gold_evidence'][0]['quote']);render_sources(row['hits'])
    st.download_button('Download metrics CSV',(RESULTS/'metrics.csv').read_bytes(),'metrics.csv','text/csv')

with tabs[2]:
    st.subheader('Review the evidence')
    st.write('AI-assisted qualitative labels disclose their provenance. The form records a separate review only when a reader personally checks the source; empty fields are not completed human assessments.')
    path=RESULTS/'manual_audit.json'
    if path.exists():
        audit=read_json(path)
        group=st.selectbox('Review category',['grounding','coherence','metadata'])
        rows=audit[group]
        idx=st.selectbox('Review sample',range(len(rows)),format_func=lambda i:f"{rows[i]['strategy']} · {rows[i].get('question_id','PDF '+str(rows[i].get('page')))} · sample {i+1}")
        row=rows[idx]
        if group=='coherence':
            st.text(row['text']);st.caption(f"PDF p.{row['page']} · character anchor {row['anchor']}")
        else:
            trace=next(t for t in traces if t['strategy']==row['strategy'] and t['question_id']==row['question_id'])
            st.write(trace['question']);st.write('Reference answer:',trace['expected_answer'])
            st.write('Gold evidence:',trace['gold_evidence'][0]['quote'])
            render_sources(trace['hits'] if group=='grounding' else [trace['hits'][row['rank']-1]])
        st.caption('Coherence/grounding: 0 = insufficient, 1 = partial, 2 = complete. Metadata: check the actual source, page and chapter.')
        with st.form(f'audit_{group}_{idx}'):
            reviewer=st.text_input('Reviewer',value=row.get('reviewer',''))
            options=[None,False,True] if group=='metadata' else [None,0,1,2]
            field='correct' if group=='metadata' else 'score'
            score=st.selectbox('Rating',options,index=options.index(row.get(field)),format_func=lambda v:'Not reviewed' if v is None else str(v))
            reason=st.text_area('Reason / observed issue',value=row.get('reason',''))
            confirmed=st.checkbox('I personally read this sample and checked the original PDF page')
            if st.form_submit_button('Save review'):
                if score is None or not reviewer.strip() or not reason.strip() or not confirmed:
                    st.error('Enter a reviewer, rating, reason and confirmation that you checked the PDF.')
                else:
                    rows[idx].update({field:score,'reviewer':reviewer.strip(),'reason':reason.strip(),'verified_at':now()})
                    write_json(path,audit);st.success('Human review saved separately. The finalized report remains unchanged.')
        st.caption(f"Reviewed {sum(r.get('correct' if group=='metadata' else 'score') is not None for r in rows)}/{len(rows)} samples in this category.")
    assisted=RESULTS/'qualitative_audit.json'
    if assisted.exists():
        with st.expander('AI-assisted assessment and provenance'):
            st.json(read_json(assisted))
    final_report=ROOT/'report/individual/2A202603569_DinhThiHuong.md'
    st.caption('The individual report is finalized in Vietnamese and is not regenerated by this interface.')
    st.download_button('Download finalized report',final_report.read_bytes(),final_report.name,'text/markdown')
