
"""Evaluate DocVersion RAG correctness, grounding, and citations."""

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Tuple

from rag_pipeline import OUTPUT_DIR, run_rag, load_chunks


ROOT = Path(__file__).resolve().parent.parent
TEST_SET_FILE = ROOT / "data" / "evaluation" / "rag_test_set.json"
RESULTS_FILE = OUTPUT_DIR / "rag_evaluation_results.json"
REPORT_FILE = OUTPUT_DIR / "rag_evaluation_summary.md"
CITATION_FILE = OUTPUT_DIR / "rag_citation_checks.json"


def normalize(text: str) -> str:
    """Normalize text for deterministic comparisons."""
    text = re.sub(r"(?m)^\s{0,3}#{1,6}\s*", "", text or "")
    text = re.sub(r"\s+", " ", text)
    return text.strip().lower()


def load_test_set() -> List[Dict[str, Any]]:
    if not TEST_SET_FILE.exists():
        raise FileNotFoundError(
            "Evaluation test set not found: {}".format(TEST_SET_FILE)
        )

    with TEST_SET_FILE.open("r", encoding="utf-8") as file:
        cases = json.load(file)

    if not isinstance(cases, list) or not cases:
        raise ValueError("The evaluation test set is empty or invalid.")

    return cases


def score_correctness(
    answer: str,
    expected_terms: List[str],
    expect_no_source: bool,
    retrieved_count: int,
) -> Tuple[float, List[str]]:
    """
    Score expected-answer term coverage.

    For a no-source test, correctness requires no retrieved chunks and
    an explicit insufficient-evidence response.
    """

    normalized_answer = normalize(answer)

    if expect_no_source:
        safe_fallback = any(
            phrase in normalized_answer
            for phrase in [
                "couldn't find relevant information",
                "not enough matching evidence",
                "can't provide a grounded answer",
                "could not provide a grounded answer",
            ]
        )

        passed = retrieved_count == 0 and safe_fallback

        return (1.0 if passed else 0.0), (
            [] if passed else [
                "Expected a no-source fallback with zero retrieved chunks."
            ]
        )

    if not expected_terms:
        return 0.0, ["No expected answer terms were defined."]

    missing = [
        term for term in expected_terms
        if normalize(term) not in normalized_answer
    ]

    score = (
        float(len(expected_terms) - len(missing))
        / float(len(expected_terms))
    )

    return score, missing


def score_grounding(
    answer: str,
    retrieved: List[Dict[str, Any]],
    expect_no_source: bool,
) -> Tuple[float, List[Dict[str, Any]]]:
    """
    Check whether cited answer lines occur in their cited retrieved
    chunk. This is a deterministic text-support check, not an entailment
    model.
    """

    if expect_no_source:
        fallback = (
            len(retrieved) == 0
            and any(
                phrase in normalize(answer)
                for phrase in [
                    "couldn't find relevant information",
                    "not enough matching evidence",
                    "can't provide a grounded answer",
                ]
            )
        )

        return (
            (1.0 if fallback else 0.0),
            [{
                "check": "no_source_fallback",
                "supported": fallback,
            }],
        )

    citation_lines = []

    for line in answer.splitlines():
        line = line.strip()
        if not line:
            continue

        match = re.match(r"^\[(\d+)\]\s*(.*)$", line)

        if match:
            citation_lines.append({
                "citation_id": match.group(1),
                "claim": match.group(2).strip(),
            })

    if not citation_lines:
        return 0.0, [{
            "check": "answer_has_cited_claim_lines",
            "supported": False,
            "reason": "No citation-labelled answer lines found.",
        }]

    checks = []

    for item in citation_lines:
        citation_number = int(item["citation_id"])
        claim = normalize(item["claim"])

        if citation_number < 1 or citation_number > len(retrieved):
            checks.append({
                "citation": "[{}]".format(citation_number),
                "claim": item["claim"],
                "supported": False,
                "reason": "Citation does not map to a retrieved chunk.",
            })
            continue

        chunk = retrieved[citation_number - 1]
        source_text = normalize(chunk.get("text", ""))

        # Verify the cited claim against the exact chunk it points to.
        supported = bool(claim) and claim in source_text

        checks.append({
            "citation": "[{}]".format(citation_number),
            "claim": item["claim"],
            "chunk_id": chunk.get("chunk_id"),
            "source": chunk.get("metadata", {}).get("source"),
            "supported": supported,
            "reason": (
                "Claim text found in cited chunk."
                if supported else
                "Claim text not found in cited chunk."
            ),
        })

    score = (
        sum(1 for check in checks if check["supported"])
        / float(len(checks))
    )

    return score, checks


def score_citations(
    answer: str,
    retrieved: List[Dict[str, Any]],
    expected_source_ids: List[str],
    expect_no_source: bool,
) -> Tuple[float, Dict[str, Any]]:
    """
    Measure citation mapping validity and whether expected source chunks
    were retrieved and cited.
    """

    references = re.findall(r"\[(\d+)\]", answer)
    retrieved_ids = [
        chunk.get("chunk_id") for chunk in retrieved
    ]

    valid_references = [
        reference for reference in references
        if reference.isdigit()
        and 1 <= int(reference) <= len(retrieved)
    ]

    cited_chunk_ids = [
        retrieved[int(reference) - 1].get("chunk_id")
        for reference in valid_references
    ]

    invalid_references = [
        reference for reference in references
        if reference not in valid_references
    ]

    if expect_no_source:
        passed = (
            len(retrieved) == 0
            and len(references) == 0
            and len(invalid_references) == 0
        )

        return (
            1.0 if passed else 0.0,
            {
                "references": references,
                "cited_chunk_ids": cited_chunk_ids,
                "invalid_references": invalid_references,
                "expected_source_ids": [],
                "expected_sources_retrieved": [],
                "expected_sources_cited": [],
                "no_source_fallback_passed": passed,
            },
        )

    expected_retrieved = [
        source_id for source_id in expected_source_ids
        if source_id in retrieved_ids
    ]
    expected_cited = [
        source_id for source_id in expected_source_ids
        if source_id in cited_chunk_ids
    ]

    # Score whether expected evidence was actually cited, not merely
    # whether a syntactically valid [number] appeared in the answer.
    if not expected_source_ids:
        score = 0.0
    else:
        score = (
            len(expected_cited) / float(len(expected_source_ids))
        )

    # Invalid references always make the citation score zero.
    if invalid_references:
        score = 0.0

    return score, {
        "references": references,
        "cited_chunk_ids": cited_chunk_ids,
        "invalid_references": invalid_references,
        "expected_source_ids": expected_source_ids,
        "expected_sources_retrieved": expected_retrieved,
        "expected_sources_cited": expected_cited,
    }


def evaluate_case(
    case: Dict[str, Any],
) -> Dict[str, Any]:
    """Run and score one evaluation example."""

    print("\nEvaluating: {}".format(case["id"]))
    result = run_rag(case["query"])

    answer = result.get("answer", "")
    retrieved = result.get("retrieved_chunks", [])
    expect_no_source = case.get("expect_no_source", False)

    correctness, missing_terms = score_correctness(
        answer=answer,
        expected_terms=case.get("expected_answer_terms", []),
        expect_no_source=expect_no_source,
        retrieved_count=len(retrieved),
    )

    grounding, grounding_checks = score_grounding(
        answer=answer,
        retrieved=retrieved,
        expect_no_source=expect_no_source,
    )

    citation_accuracy, citation_details = score_citations(
        answer=answer,
        retrieved=retrieved,
        expected_source_ids=case.get(
            "expected_source_chunk_ids", []
        ),
        expect_no_source=expect_no_source,
    )

    expected_sources = case.get("expected_source_chunk_ids", [])
    retrieved_ids = [
        chunk.get("chunk_id") for chunk in retrieved
    ]

    missing_sources = [
        source_id for source_id in expected_sources
        if source_id not in retrieved_ids
    ]

    failures = []

    if correctness < 1.0:
        failures.append(
            "Expected answer terms missing: {}".format(missing_terms)
        )

    if grounding < 1.0:
        failures.append(
            "One or more answer claims could not be matched to cited text."
        )

    if citation_accuracy < 1.0:
        failures.append(
            "Expected source chunks were not all cited correctly."
        )

    if missing_sources:
        failures.append(
            "Expected sources not retrieved: {}".format(missing_sources)
        )

    return {
        "id": case["id"],
        "query": case["query"],
        "answer": answer,
        "generation_mode": result.get("generation_mode"),
        "retrieval_mode": result.get("retrieval_mode"),
        "retrieved_chunk_ids": retrieved_ids,
        "expected_answer_terms": case.get(
            "expected_answer_terms", []
        ),
        "expected_source_chunk_ids": expected_sources,
        "correctness_score": correctness,
        "grounding_score": grounding,
        "citation_accuracy_score": citation_accuracy,
        "grounding_checks": grounding_checks,
        "citation_checks": citation_details,
        "missing_expected_terms": missing_terms,
        "missing_expected_sources": missing_sources,
        "failures": failures,
    }


def build_summary(results: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Calculate mean scores and list notable failures."""

    if not results:
        raise ValueError("There are no evaluation results to summarize.")

    dimensions = [
        "correctness_score",
        "grounding_score",
        "citation_accuracy_score",
    ]

    averages = {
        dimension: sum(
            item[dimension] for item in results
        ) / float(len(results))
        for dimension in dimensions
    }

    return {
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "test_count": len(results),
        "scores": averages,
        "scores_percent": {
            key: round(value * 100.0, 2)
            for key, value in averages.items()
        },
        "fully_passed_cases": sum(
            1 for item in results
            if all(item[dimension] == 1.0 for dimension in dimensions)
        ),
        "failures": [
            {
                "id": item["id"],
                "query": item["query"],
                "causes": item["failures"],
            }
            for item in results if item["failures"]
        ],
    }


def write_reports(
    results: List[Dict[str, Any]],
    summary: Dict[str, Any],
) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    RESULTS_FILE.write_text(
        json.dumps(results, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    CITATION_FILE.write_text(
        json.dumps(
            [
                {
                    "id": item["id"],
                    "query": item["query"],
                    "citation_accuracy_score":
                        item["citation_accuracy_score"],
                    "citation_checks": item["citation_checks"],
                    "grounding_checks": item["grounding_checks"],
                }
                for item in results
            ],
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    lines = [
        "# DocVersion RAG Evaluation Summary",
        "",
        "- Evaluation time: {}".format(summary["created_at"]),
        "- Test cases: {}".format(summary["test_count"]),
        "- Fully passed cases: {}".format(
            summary["fully_passed_cases"]
        ),
        "",
        "## Overall scores",
        "",
        "| Dimension | Score |",
        "|---|---:|",
        "| Correctness | {}% |".format(
            summary["scores_percent"]["correctness_score"]
        ),
        "| Grounding | {}% |".format(
            summary["scores_percent"]["grounding_score"]
        ),
        "| Citation accuracy | {}% |".format(
            summary["scores_percent"]["citation_accuracy_score"]
        ),
        "",
        "## Per-question results",
        "",
        "| Test | Correctness | Grounding | Citation accuracy |",
        "|---|---:|---:|---:|",
    ]

    for item in results:
        lines.append(
            "| {} | {:.0f}% | {:.0f}% | {:.0f}% |".format(
                item["id"],
                item["correctness_score"] * 100,
                item["grounding_score"] * 100,
                item["citation_accuracy_score"] * 100,
            )
        )

    lines.extend([
        "",
        "## Failures and likely causes",
        "",
    ])

    if summary["failures"]:
        for failure in summary["failures"]:
            lines.append(
                "### {} — {}".format(
                    failure["id"], failure["query"]
                )
            )

            for cause in failure["causes"]:
                lines.append("- {}".format(cause))

            lines.append("")
    else:
        lines.append(
            "No failures were detected by the configured checks."
        )

    lines.extend([
        "",
        "## Scoring methodology and limitations",
        "",
        "- Correctness is expected-term coverage, not human judgement.",
        "- Grounding checks whether each citation-labelled answer line "
        "appears in its cited retrieved chunk.",
        "- Citation accuracy measures whether expected source chunks "
        "were cited and rejects invalid citation numbers.",
        "- The no-source test passes only when no chunks are retrieved "
        "and the system returns an insufficient-evidence response.",
        "- These are deterministic checks for a small test set. They "
        "do not prove semantic entailment, factual completeness, or "
        "general performance on unseen questions.",
        "",
    ])

    REPORT_FILE.write_text(
        "\n".join(lines),
        encoding="utf-8",
    )


def main() -> None:
    # Validate that the source corpus exists before evaluating.
    load_chunks()

    test_cases = load_test_set()
    results = []

    for case in test_cases:
        results.append(evaluate_case(case))

    summary = build_summary(results)
    write_reports(results, summary)

    print("\n========== EVALUATION SUMMARY ==========")
    print("Test cases: {}".format(summary["test_count"]))
    print("Correctness: {}%".format(
        summary["scores_percent"]["correctness_score"]
    ))
    print("Grounding: {}%".format(
        summary["scores_percent"]["grounding_score"]
    ))
    print("Citation accuracy: {}%".format(
        summary["scores_percent"]["citation_accuracy_score"]
    ))
    print("Fully passed: {}".format(summary["fully_passed_cases"]))
    print("Results: {}".format(RESULTS_FILE))
    print("Citation checks: {}".format(CITATION_FILE))
    print("Summary: {}".format(REPORT_FILE))


if __name__ == "__main__":
    main()
