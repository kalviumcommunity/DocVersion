# DocVersion RAG Evaluation Summary

- Evaluation time: 2026-10-26T14:07:04
- Test cases: 8
- Fully passed cases: 8

## Overall scores

| Dimension | Score |
|---|---:|
| Correctness | 100.0% |
| Grounding | 100.0% |
| Citation accuracy | 100.0% |

## Per-question results

| Test | Correctness | Grounding | Citation accuracy |
|---|---:|---:|---:|
| leave_days | 100% | 100% | 100% |
| leave_request | 100% | 100% | 100% |
| leave_carryover | 100% | 100% | 100% |
| working_hours | 100% | 100% | 100% |
| late_arrival | 100% | 100% | 100% |
| password_sharing | 100% | 100% | 100% |
| incident_reporting | 100% | 100% | 100% |
| mars_fallback | 100% | 100% | 100% |

## Failures and likely causes

No failures were detected by the configured checks.

## Scoring methodology and limitations

- Correctness is expected-term coverage, not human judgement.
- Grounding checks whether each citation-labelled answer line appears in its cited retrieved chunk.
- Citation accuracy measures whether expected source chunks were cited and rejects invalid citation numbers.
- The no-source test passes only when no chunks are retrieved and the system returns an insufficient-evidence response.
- These are deterministic checks for a small test set. They do not prove semantic entailment, factual completeness, or general performance on unseen questions.
