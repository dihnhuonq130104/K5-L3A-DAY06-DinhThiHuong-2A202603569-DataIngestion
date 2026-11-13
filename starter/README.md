# Implementation

The supported stack is OpenAI text-embedding-3-small (1536 dimensions), GPT-5.4, persistent Chroma and Streamlit. Run commands from the project root; see the root README.

| Module | Responsibility |
|---|---|
| ingestion.py | PDF extraction and Unicode/whitespace normalization |
| chunking.py / experiment.py | Fixed windows, section-aware chunk construction and development plan |
| embeddings.py / api_client.py | Real OpenAI requests and usage logging |
| chroma_store.py | Persistent cosine search, upsert, stale removal and chapter filters |
| evaluation.py | Exact evidence metrics and complete query traces |
| pipeline.py | Frozen-input checks, API cache and usage utilities |
| run.py | Rebuild selected indices and reproduce recorded benchmark |
| demo.py / chat.py | English retrieval, GPT-5.4 and source-page citation checks |
| source_links.py | Exact excerpt offsets to OpenStax online sections |
| report.py | Report generated from recorded metrics and disclosed assessment |

`experiment.py` records the original parameter-selection workflow. The supported reproduction entry point is `python -m starter.src.run all`; it does not tune on test or overwrite first-run traces. Human-only review scores remain separate from assisted labels.
