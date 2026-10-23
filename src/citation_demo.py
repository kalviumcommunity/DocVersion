
"""Run the RAG pipeline and produce citation-verification artifacts."""

import os
import re
from pathlib import Path
from typing import Any, Dict, List

from rag_pipeline import (
    OUTPUT_DIR,
    extractive_answer,
    load_chunks,
    run_rag,
)
from citation_support import (
    build_citation_map,
    save_json,
    validate_answer_citations,
    verify_citation,
)


def save_markdown(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def create_cited_answer(
    query: str,
) -> Dict[str, Any]:
    """Run RAG, validate its citations, and reject unverified sources."""

    result = run_rag(query)
    original_chunks = load_chunks()
    retrieved = result.get("retrieved_chunks", [])

    citation_map = build_citation_map(
        retrieved,
        original_chunks,
    )

    # Never cite a chunk that cannot be verified against the corpus.
    verified_results = [
        chunk
        for number, chunk in enumerate(retrieved, start=1)
        if citation_map[str(number)]["verified_against_original"]
    ]

    if len(verified_results) != len(retrieved):
        print(
            "[WARNING] Some retrieved chunks failed source verification "
            "and will not be cited."
        )

    if not verified_results:
        answer = (
            "I couldn't verify any retrieved source against the original "
            "chunk corpus, so I can't provide a reliably cited answer."
        )
        generation_mode = "no_verified_sources"
        citation_map = {}
    else:
        # Rebuild the map after filtering, so [1], [2], etc. always
        # correspond to the chunks actually available for citation.
        citation_map = build_citation_map(
            verified_results,
            original_chunks,
        )

        answer = result.get("answer", "")
        valid, reason = validate_answer_citations(
            answer,
            citation_map,
        )

        if not valid:
            print(
                "[WARNING] Answer citation validation failed: {}. "
                "Using a verified extractive fallback.".format(reason)
            )

            answer, generation_mode = extractive_answer(
                query,
                verified_results,
            )

            # Validate the fallback too.
            valid, reason = validate_answer_citations(
                answer,
                citation_map,
            )

            if not valid:
                answer = (
                    "The retrieved text could not be converted into "
                    "a reliably cited answer. Please inspect the "
                    "verified source chunks below."
                )
                generation_mode = "citation_validation_fallback"
        else:
            generation_mode = result.get(
                "generation_mode",
                "extractive_fallback",
            )

    return {
        "query": query,
        "answer": answer,
        "generation_mode": generation_mode,
        "citation_map": citation_map,
        "retrieved_chunks": verified_results,
    }


def save_citation_artifacts(
    result: Dict[str, Any],
) -> None:
    """Write sample answer, source map, and verification artifacts."""

    citation_map = result["citation_map"]
    answer = result["answer"]

    save_json(
        OUTPUT_DIR / "citation_source_map.json",
        {
            "query": result["query"],
            "citations": citation_map,
        },
    )

    verification_records = [
        verify_citation(number, citation_map)
        for number in citation_map
    ]

    save_json(
        OUTPUT_DIR / "citation_verification.json",
        {
            "query": result["query"],
            "verification_results": verification_records,
            "all_sources_verified": bool(verification_records)
            and all(
                item["verified"]
                for item in verification_records
            ),
        },
    )

    lines = [
        "# Sample Answer with Verifiable Citations",
        "",
        "**Question:** {}".format(result["query"]),
        "",
        "**Answer mode:** {}".format(result["generation_mode"]),
        "",
        "## Answer",
        "",
        answer,
        "",
        "## Citation-to-source mapping",
        "",
    ]

    if citation_map:
        for number, source in citation_map.items():
            lines.extend([
                "### [{}] {}".format(number, source["source"]),
                "",
                "- Source path: `{}`".format(source["source_path"]),
                "- Chunk ID: `{}`".format(source["chunk_id"]),
                "- Chunk index: `{}`".format(source["chunk_index"]),
                "- Page: `{}`".format(source["page"]),
                "- Section: `{}`".format(source["section"]),
                "- Verified against original: **{}**".format(
                    source["verified_against_original"]
                ),
                "",
                "**Original chunk text:**",
                "",
                "> {}".format(
                    source["original_chunk_text"].replace(
                        "\n", "\n> "
                    )
                ),
                "",
            ])
    else:
        lines.append("No verified source chunks were available.")

    save_markdown(
        OUTPUT_DIR / "cited_answer_sample.md",
        "\n".join(lines),
    )

    no_source_answer = (
        "I couldn't find relevant information in the available "
        "documents, so I can't provide a grounded, cited answer."
    )

    save_markdown(
        OUTPUT_DIR / "no_source_fallback_example.md",
        "\n".join([
            "# No-Source Fallback Example",
            "",
            "**Example query:** What is the capital of Mars?",
            "",
            "**Result:**",
            "",
            no_source_answer,
            "",
            "**Citations:** None. No source chunks were retrieved, "
            "so the answer does not invent references.",
            "",
        ]),
    )

    # Include an explicit source-verification demonstration.
    verification_lines = [
        "# Citation Verification Example",
        "",
        "This report checks that each citation points to a real chunk "
        "and that the retrieved text matches the original corpus.",
        "",
    ]

    if citation_map:
        first_id = next(iter(citation_map))
        first_verification = verify_citation(
            first_id,
            citation_map,
        )

        verification_lines.extend([
            "## Example citation: {}".format(
                first_verification["citation"]
            ),
            "",
            "- Verified: **{}**".format(
                first_verification["verified"]
            ),
            "- Source: `{}`".format(
                first_verification.get("source", "")
            ),
            "- Chunk ID: `{}`".format(
                first_verification.get("chunk_id", "")
            ),
            "- Section: `{}`".format(
                first_verification.get("section", "")
            ),
            "",
            "### Original text used for verification",
            "",
            first_verification.get("original_chunk_text", ""),
            "",
        ])
    else:
        verification_lines.append(
            "No verified citations were produced in this run."
        )

    # Demonstrate that an unknown citation is rejected.
    unknown_citation_valid, unknown_reason = (
        validate_answer_citations(
            "This claim is cited as [999].",
            citation_map,
        )
    )

    verification_lines.extend([
        "## Fabricated citation check",
        "",
        "- Input: `This claim is cited as [999].`",
        "- Accepted: **{}**".format(unknown_citation_valid),
        "- Validation result: {}".format(unknown_reason),
        "",
    ])

    save_markdown(
        OUTPUT_DIR / "citation_verification_example.md",
        "\n".join(verification_lines),
    )


def main() -> None:
    query = os.getenv(
        "RAG_QUERY",
        "How many days of annual leave do employees receive each year?",
    )

    result = create_cited_answer(query)
    save_citation_artifacts(result)

    print("\n========== CITED ANSWER ==========")
    print(result["answer"])

    print("\n========== CITATION MAP ==========")
    for number, source in result["citation_map"].items():
        print(
            "[{}] {} | chunk={} | section={} | verified={}".format(
                number,
                source["source"],
                source["chunk_id"],
                source["section"],
                source["verified_against_original"],
            )
        )

    print("\nSaved citation artifacts in: {}".format(OUTPUT_DIR))


if __name__ == "__main__":
    main()
