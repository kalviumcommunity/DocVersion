# Offline Retrieval Tuning Experiment

- Run time: 2026-10-21T17:03:22
- Method: offline keyword-based lexical retrieval
- Corpus: `outputs/sample_chunks.json`
- Test query count: 4

> This experiment does not use embeddings or ChromaDB. It evaluates lexical retrieval against the actual saved chunks and their expected source/chunk labels.

## Test queries

- **query_01:** Employee Handbook Working Hours: Employees generally work from 9:00 AM to 5:00 | Expected source: `employee_handbook.txt` | Expected chunk: `employee_handbook_chunk_000`
- **query_02:** # Leave Policy | Expected source: `leave_policy.md` | Expected chunk: `leave_policy_chunk_000`
- **query_03:** Security Policy Security Policy Employees must protect their account credentials. Passwords must | Expected source: `security_policy.html` | Expected chunk: `security_policy_chunk_000`
- **query_04:** Workplace Guidelines Employees should maintain a respectful workplace. Company documents should be | Expected source: `workplace_guidelines.pdf` | Expected chunk: `workplace_guidelines_chunk_000`

## Compared settings and measured relevance

| Setting | k | Source filter | Top-1 source hit | Source hit@k | Exact chunk hit@k |
|---|---:|---|---:|---:|---:|
| unfiltered_k1 | 1 | None | 100.0% | 100.0% | 100.0% |
| unfiltered_k3 | 3 | None | 100.0% | 100.0% | 100.0% |
| oracle_source_filter_k3 | 3 | Oracle diagnostic | 100.0% | 100.0% | 100.0% |

## Selected configuration

**unfiltered_k1 (k=1)**

Selection uses exact-chunk hit@k, then source hit@k, among unfiltered settings only. When those scores tie, the smaller k is selected to reduce unnecessary context.

The source-filter experiment is an oracle diagnostic: it filters by the expected answer source already known from the labels. It is not a fair production setting unless the source is independently known at query time.

## Limitations

The initial test queries are short snippets taken from their target chunks. This is a smoke test, not an independent evaluation of realistic user questions. For stronger evidence, replace them with natural questions and manually verify the expected relevant chunks.

The score is a weighted lexical overlap heuristic. It is not cosine similarity, BM25, or semantic retrieval. Results must not be presented as vector-search performance.
