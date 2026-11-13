"""English textbook retrieval and grounded chat."""
from .project import ROOT,RESULTS,read_json
from .embeddings import MyEmbedder
from .chroma_store import ChromaStore
from .chat import GroundedChat
from .pipeline import cached_embed,append_usage
from .experiment import query_text


def retrieve(question,strategy='B',chapter=None):
    if not question.strip():raise ValueError('Question is empty')
    ingestion=read_json(RESULTS/'ingestion.json')
    if strategy not in ['A','B','C']:raise ValueError('Unknown strategy')
    if chapter and chapter not in ['Decisions','Loops']:raise ValueError('Unknown chapter')
    embedder=MyEmbedder()
    if (embedder.model_name,embedder.dimensions)!=(ingestion['model'],ingestion['dimensions']):
        raise ValueError('Embedding model changed; rebuild the index')
    store=ChromaStore(ROOT/'.chroma',ingestion['collections'][strategy],embedder.dimensions)
    if not store.collection.count():raise ValueError('Index is empty; run ingest first')
    vector=cached_embed(embedder,[query_text(question)])[0]
    scope={'chapter':chapter} if strategy=='C' and chapter else None
    hits=store.search(vector,filters=scope)
    append_usage('chat_retrieval',embedder.total_tokens)
    return hits


def chat(question,strategy,chapter=None,history=None):
    earlier=[m['content'] for m in (history or []) if m['role']=='user']
    followup=len(question.split())<=7 and earlier
    query=earlier[-1]+'\n'+question if followup else question
    hits=retrieve(query,strategy,chapter)
    result=GroundedChat().answer(question,hits,history=history)
    append_usage('chat',0,{'chat_model':result.get('model'),'chat_usage':result.get('usage'),
                           'citation_check':result.get('citation_check')})
    return {**result,'hits':hits}


def safe_error(exc):
    status=getattr(exc,'status_code',None)
    if status==401:return 'The OpenAI key is invalid or expired. Update OPENAI_API_KEY in .env.'
    if status==429:return 'OpenAI quota or rate limit reached. Check billing and try again.'
    if status==404:return 'The configured model is unavailable to this account. Check model access.'
    if isinstance(exc,FileNotFoundError):return 'A required artifact is missing. Follow the setup instructions in README.'
    if type(exc).__name__ in ['APIConnectionError','APITimeoutError']:return 'Could not reach OpenAI. Check your connection and try again.'
    return f'The operation could not be completed ({type(exc).__name__}). Check the index and configuration in README.'
