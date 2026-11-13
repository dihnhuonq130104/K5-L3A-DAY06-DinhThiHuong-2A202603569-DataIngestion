# Benchmark

25 English questions: 15 dev and 10 test. Test is balanced across Decisions/Loops, with four explicit chapter filters. Questions include direct facts, conditions, code output and source-specific examples.

Each record contains question, expected answer, source ID, physical PDF page, exact gold quote and optional user-supplied chapter scope. All gold quotes are source-checked. No answer or gold page enters retrieval.

The development plan fixes candidate sizes, ranking code and question hashes before retrieval. Dev selects the size and A/B/C winner; the test is retrieved only after selection. configs/english_plan.json and results/english_run/selection.json record that chronology. freeze.json is the canonical packaging hash manifest and explicitly identifies its role.

Exact evidence metrics normalize whitespace and require the full quote in one chunk on the correct source/page. AI-assisted labels are not human validation. Ten test questions from the same textbook do not constitute an external benchmark.
