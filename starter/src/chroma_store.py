"""Persistent cosine vector retrieval; model/config isolated collections."""
from dataclasses import asdict
from pathlib import Path
import chromadb
from chromadb.config import Settings
from functools import lru_cache


@lru_cache(maxsize=4)
def persistent_client(path):
    # Retain a single client for the process lifetime. Multiple short-lived
    # clients can invalidate in-memory HNSW segment readers during ingestion.
    return chromadb.PersistentClient(path, settings=Settings(anonymized_telemetry=False))


class ChromaStore:
    def __init__(self, path: Path, collection: str, dimensions: int):
        self.client = persistent_client(str(Path(path).resolve()))
        self.collection = self.client.get_or_create_collection(
            collection, configuration={"hnsw": {"space": "cosine", "batch_size": 10, "sync_threshold": 10}})
        self.collection.modify(configuration={"hnsw": {"batch_size": 10, "sync_threshold": 10}})
        self.dimensions = dimensions

    def replace(self, chunks, vectors):
        if len(chunks) != len(vectors) or any(len(v) != self.dimensions for v in vectors):
            raise ValueError("Chunk/vector count or dimensions do not match")
        ids = [c.chunk_id for c in chunks]
        if len(set(ids)) != len(ids):
            raise ValueError("Duplicate chunk IDs")
        old = set(self.collection.get(include=[])['ids'])
        for start in range(0, len(chunks), 100):
            batch = chunks[start:start+100]
            self.collection.upsert(
                ids=[c.chunk_id for c in batch], documents=[c.text for c in batch],
                embeddings=vectors[start:start+100],
                metadatas=[{**c.metadata, "document_id": c.document_id,
                            "source": c.source, "page": c.page} for c in batch])
        stale = old - set(ids)
        if stale:
            self.collection.delete(ids=sorted(stale))
        return self.collection.count()

    def search(self, query_vector, top_k=3, filters=None):
        if len(query_vector) != self.dimensions:
            raise ValueError("Query dimensions do not match collection")
        if self.collection.count() == 0:
            return []
        if filters and set(filters) != {"chapter"}:
            raise ValueError("Only a user-supplied chapter filter is supported")
        kwargs = {"where": filters} if filters else {}
        result = self.collection.query(query_embeddings=[query_vector], n_results=min(top_k,self.collection.count()),
                                       include=["documents", "metadatas", "distances"], **kwargs)
        return [{"chunk_id": id_, "text": text, "metadata": metadata,
                 "score": 1 - distance} for id_,text,metadata,distance in zip(
                     result['ids'][0],result['documents'][0],result['metadatas'][0],result['distances'][0])]
