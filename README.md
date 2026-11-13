# Python Book Lab — Data Ingestion Engineering

**Đinh Thị Hường · 2A202603569 · L3A**

An English textbook RAG application with a reproducible A/B/C ingestion experiment. Corpus: **43 content pages** from OpenStax *Introduction to Python Programming*, chapters Decisions and Loops. Embeddings: **text-embedding-3-small, 1536 dimensions**. Chat: **GPT-5.4**. Store: **persistent Chroma**, cosine/HNSW. Interface: **Streamlit**.

## Results

| Strategy | Dev Hit@1 | Dev Hit@3 | Test Hit@1 | Test Hit@3 |
|---|---|---|---|---|
| A · Fixed windows | 7/15 | 10/15 | 6/10 | 8/10 |
| B · Section-aware | 7/15 | 13/15 | 5/10 | 8/10 |
| C · B + chapter filter | 7/15 | 13/15 | 5/10 | 8/10 |

**B was selected on dev before test retrieval.** There are 25 English questions: 15 dev and 10 test, with four chapter-filter test questions. Test scores are not used to change the selection. Questions and qualitative ratings are AI-assisted, not independent human validation. See the report for all five evaluation dimensions, failures, uncertainty and disclosure.

## Setup on Windows PowerShell

Run from this project directory. Requires Python 3.11+ (tested with 3.14.5), network access, an OpenAI key with billing and access to GPT-5.4.

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.lock.txt
```

Copy `.env.example` to `.env` only if `.env` does not already exist, then set:

```dotenv
OPENAI_API_KEY=your-key-here
EMBEDDING_MODEL=text-embedding-3-small
EMBEDDING_DIMENSIONS=1536
CHAT_MODEL=gpt-5.4
```

Keep the key private. The API sends relevant textbook excerpts and queries to OpenAI and incurs fees. No local model, second API provider or Docker is needed. The included PDF and extracts retain OpenStax attribution and CC BY-NC-SA 4.0 terms; see `data/NOTICE.md`.

```powershell
# Build selected A/B indices, verify idempotent reload, reproduce all 75 traces
.\.venv\Scripts\python.exe -m starter.src.run all

# Open the English interface at http://127.0.0.1:8501
.\.venv\Scripts\python.exe -m streamlit run app.py
```

A uses 1,800-character windows with 200-character overlap. B respects textbook sections and sentence/line boundaries, up to 1,800 characters, with no overlap. C shares B's exact index and only adds a chapter filter supplied by the user. All three use the same embedding preprocessing: English chapter/section context and index-only URL/video/footer cleanup. Returned evidence remains exact source text with offsets.

Each answer displays top-3 evidence, PDF/printed pages and links to the corresponding OpenStax online sections. The source PDF can be downloaded. Source-page citation checks reject incomplete or malformed answers; they do not prove factual correctness. Saved experiment results remain viewable without a key/index; chat is disabled until the local index is built.

## Verification and submission

```powershell
# Offline hashes, gold quotes, source offsets, links, filters and exact metrics
.\.venv\Scripts\python.exe starter/scripts/verify_submission.py

# Unit and Streamlit UI tests; no paid model calls
.\.venv\Scripts\python.exe -X utf8 -m unittest discover -s tests -v

# One real GPT-5.4 smoke check; incurs API usage
.\.venv\Scripts\python.exe starter/scripts/check_api.py

# Create and verify the submission ZIP, excluding credentials/caches
.\.venv\Scripts\python.exe starter/scripts/package_submission.py
```

The student-finalized report is preserved unchanged and protected by `report/finalization.json`; automatic regeneration is disabled. The individual report is written in Vietnamese; book-facing questions, evidence and answers are English. Report: `report/individual/2A202603569_DinhThiHuong.md`. Submission map: `SUBMISSION_INDEX.md`. Demo: `docs/DEMO.md`. Explanation: `docs/EXPLANATION.md`. Development plan and pre-retrieval hashes: `configs/english_plan.json`; dev candidate traces and selection: `results/english_run/`. Canonical input hashes are in `benchmark/freeze.json`, assembled for packaging and linked to the earlier plan/selection records.

Do not rerun experiment prepare/build/test to overwrite the recorded selection or first test. `starter.src.run` is the supported rebuild/reproduction command; it uses the frozen configuration and writes a separate reproduction check. The index and API cache are not shipped and must be rebuilt on another machine. The requirements file pins observed direct versions, not all transitive dependencies.

## Limitations and troubleshooting

- A 10-question, AI-assisted, purposive test is small; 8/10 has a Wilson 95% interval of approximately 49%–94%. Do not claim general performance from it.
- C does not outperform B here; a chapter filter limits scope but cannot repair missing evidence. A has the higher test Hit@1 despite B winning the dev selection rule.
- Strict gold matching can reject semantically valid alternatives. Tables/code and concepts can still be cut at PDF page boundaries.
- Qualitative labels disclose AI assistance. Human-only review fields remain separate; they are not filled on the student's behalf.
- 401: update an expired/invalid key. 429: check quota/rate limits. 404: check model access. Network failures: check connectivity; successful cached vectors are reused.
- If the PDF is missing, retrieve it through the source in `data/manifest.json` and verify its SHA-256. Do not silently substitute another edition/model.
- Chroma uses a retained process client and HNSW batch/sync thresholds of 10 for these small indices. Upsert plus stale-ID removal prevents duplicate reloads.
- Costs are usage-based estimates, not a complete historical invoice. See provider request/stage logs and the report.

The ZIP is saved locally in `submission/` with per-file hashes and a SHA-256 checksum. No Git operations or class-channel submission are part of packaging.
