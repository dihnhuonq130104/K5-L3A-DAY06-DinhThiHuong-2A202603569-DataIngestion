"""OpenAI embeddings for documents and queries; no local fallback."""
import os
from .api_client import create_client
from typing import Protocol


class Embedder(Protocol):
    model_name: str
    dimensions: int

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        """Return one vector per input text, in the same order."""
        ...

    def embed_query(self, question: str) -> list[float]:
        """Return a query vector compatible with the stored document vectors."""
        ...


class MyEmbedder:
    """Real OpenAI embeddings; keep the same configuration for A/B/C."""

    def __init__(self, model_name: str | None = None) -> None:
        self.client = create_client()
        self.model_name = model_name or os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")
        self.dimensions = int(os.getenv("EMBEDDING_DIMENSIONS", "1536"))
        self.total_tokens = 0

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        if any(not text.strip() for text in texts):
            raise ValueError("Cannot embed empty text")
        vectors = []
        for start in range(0, len(texts), 32):
            batch = texts[start:start + 32]
            response = self.client.embeddings.create(
                model=self.model_name, input=batch, dimensions=self.dimensions,
                encoding_format="float",
            )
            items = sorted(response.data, key=lambda item: item.index)
            if len(items) != len(batch) or any(len(item.embedding) != self.dimensions for item in items):
                raise ValueError("Unexpected embedding count/dimensions")
            vectors.extend(item.embedding for item in items)
            self.total_tokens += response.usage.total_tokens
            from .project import RESULTS, now
            import json
            RESULTS.mkdir(exist_ok=True)
            with (RESULTS/'api_calls.jsonl').open('a', encoding='utf-8') as log:
                log.write(json.dumps({'at': now(), 'endpoint': 'embeddings',
                    'model': response.model, 'input_count': len(batch),
                    'usage': response.usage.model_dump()}) + '\n')
        return vectors

    def embed_query(self, question: str) -> list[float]:
        return self.embed_documents([question])[0]
