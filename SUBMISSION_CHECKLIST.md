# Submission checklist — Đinh Thị Hường

- [x] Correct name, student ID 2A202603569 and class L3A.
- [x] 43 content pages with license, attribution, source hash and metadata.
- [x] English questions and interface; 15 dev + 10 test, gold quotes source-checked.
- [x] A/B/C use the same corpus/model/preprocessing; B/C differ only in requested chapter filtering.
- [x] Shared chunk size and strategy selected on dev before test retrieval.
- [x] Real OpenAI embeddings, persistent Chroma, idempotent reload and 75 saved top-3 traces.
- [x] Coherence at ten stratified anchors per strategy; grounding for all ten test questions; 90 metadata checks, with AI provenance.
- [x] Vietnamese report covers all five dimensions, failures, uncertainty and API costs.
- [x] Student-finalized report preserved byte-for-byte and checked against report/finalization.json.
- [x] Source links resolve to textbook sections; citation page checks are implemented.
- [x] Final technical checks passed: 12/12 tests, report-table consistency, extracted-package smoke check and ZIP hash verification.
- [ ] Student personally completes any manual marking required by the instructor.
- [ ] Submit the local artifact through the instructor's specified channel and deadline.

Technical verification and ZIP hashes are recorded in results/verification.json, results/reproduction.json, results/package_smoke.json and submission/submission_manifest.json. Empty human-review fields do not count as completed manual marking.
