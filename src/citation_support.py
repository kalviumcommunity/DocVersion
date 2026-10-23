
"""Citation validation and source verification for DocVersion RAG."""

import json
import re
from pathlib import Path
from typing import Any, Dict, List, Tuple


def normalize_text(text: str) -> str:
    """Normalize whitespace for source-text comparison."""
    return " ".join((text or "").split())


def build_citation_map(
    results: List[Dict[str, Any]],
    original_chunks: List[Dict[str, Any]],
) -> Dict[str, Dict[str, Any]]:
    """
    Map [1], [2], etc. to actual retrieved chunks and verify them
    against the original chunk corpus.
    """

    originals = {
        chunk["chunk_id"]: chunk
        for chunk in original_chunks
        if chunk.get("chunk_id")
    }

    citation_map = {}

    for number, result in enumerate(results, start=1):
        chunk_id = result.get("chunk_id", "")
        original = originals.get(chunk_id)
        metadata = (
            original.get("metadata", {})
            if original else result.get("metadata", {})
        )

        retrieved_text = result.get("text", "")
        original_text = original.get("text", "") if original else ""

        text_matches = (
            original is not None
            and normalize_text(retrieved_text)
            == normalize_text(original_text)
        )

        retrieved_source = result.get("metadata", {}).get("source")
        original_source = metadata.get("source")

        source_matches = (
            original is not None
            and (
                not retrieved_source
                or not original_source
                or retrieved_source == original_source
            )
        )

        citation_map[str(number)] = {
            "citation": "[{}]".format(number),
            "source": original_source or retrieved_source or "Unknown source",
            "source_path": metadata.get("source_path", ""),
            "chunk_id": chunk_id,
            "chunk_index": metadata.get("chunk_index"),
            "page": metadata.get("page"),
            "section": metadata.get("section", ""),
            "retrieval_method": result.get("retrieval_method", ""),
            "retrieved_text": retrieved_text,
            "original_chunk_text": original_text,
            "verified_against_original": bool(
                text_matches and source_matches
            ),
            "verification_details": {
                "chunk_id_found": original is not None,
                "text_matches_original": text_matches,
                "source_matches_original": source_matches,
            },
        }

    return citation_map


def validate_answer_citations(
    answer: str,
    citation_map: Dict[str, Dict[str, Any]],
) -> Tuple[bool, str]:
    """
    Reject unknown citations, citations to unverified sources,
    and answer lines that lack citations.

    The answer format expects one cited claim per line.
    """

    if not citation_map:
        return False, "No source chunks are available to cite."

    lines = [
        line.strip()
        for line in answer.splitlines()
        if line.strip()
    ]

    if lines and lines[0].startswith(
        "Offline extractive answer"
    ):
        lines = lines[1:]

    if not lines:
        return False, "The answer is empty."

    for line in lines:
        references = re.findall(r"\[(\d+)\]", line)

        if not references:
            return False, (
                "An answer line has no citation: {}".format(line)
            )

        for reference in references:
            source = citation_map.get(reference)

            if source is None:
                return False, (
                    "Unknown citation [{}] was used.".format(reference)
                )

            if not source["verified_against_original"]:
                return False, (
                    "Citation [{}] could not be verified against "
                    "the original chunk.".format(reference)
                )

    return True, "All citation references map to verified chunks."


def verify_citation(
    citation_id: str,
    citation_map: Dict[str, Dict[str, Any]],
) -> Dict[str, Any]:
    """Return the source evidence for a specific citation."""

    source = citation_map.get(str(citation_id))

    if source is None:
        return {
            "citation": "[{}]".format(citation_id),
            "verified": False,
            "reason": "Citation does not exist in the citation map.",
        }

    return {
        "citation": source["citation"],
        "verified": source["verified_against_original"],
        "source": source["source"],
        "source_path": source["source_path"],
        "chunk_id": source["chunk_id"],
        "chunk_index": source["chunk_index"],
        "page": source["page"],
        "section": source["section"],
        "original_chunk_text": source["original_chunk_text"],
        "verification_details": source["verification_details"],
    }


def save_json(path: Path, data: Any) -> None:
    """Save JSON using UTF-8 encoding."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(data, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
