import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from document_loader import load_corpus


# Project paths
ROOT = Path(__file__).resolve().parent.parent
OUTPUT_FILE = ROOT / "outputs" / "sample_chunks.json"

# Chunk configuration
CHUNK_SIZE = 500

# Consistent metadata fields for every chunk
METADATA_FIELDS = [
    "source",
    "source_path",
    "section",
    "page",
    "chunk_index",
    "start_char",
    "end_char",
]


def find_sections(text: str) -> List[Tuple[int, str]]:
    """
    Find Markdown-style section headings and their positions.

    If no headings are found, chunks use 'Document body'
    as their section.
    """
    sections = []

    heading_pattern = re.compile(
        r"(?m)^#{1,6}\s+(.+?)\s*$"
    )

    for match in heading_pattern.finditer(text):
        sections.append(
            (match.start(), match.group(1).strip())
        )

    return sections


def get_section(
    start_char: int,
    sections: List[Tuple[int, str]]
) -> str:
    """Return the section heading closest before a chunk."""

    current_section = "Document body"

    for position, heading in sections:
        if position > start_char:
            break

        current_section = heading

    return current_section


def make_chunks(
    document: Dict[str, Any],
    chunk_size: int = CHUNK_SIZE,
) -> List[Dict[str, Any]]:
    """
    Split a loaded document into chunks with consistent metadata.

    Each chunk stores its source, section, page, index,
    and character positions.
    """

    if chunk_size <= 0:
        raise ValueError("chunk_size must be greater than zero")

    text = document.get("text", "")

    if not text:
        print(
            "[SKIP] Empty document: "
            + str(document.get("source", "unknown"))
        )
        return []

    source = document["source"]

    # Prefer a project-relative path for portable metadata.
    original_path = Path(document["source_path"])

    try:
        source_path = original_path.resolve().relative_to(
            ROOT.resolve()
        ).as_posix()
    except ValueError:
        source_path = str(original_path)

    sections = find_sections(text)
    chunks = []

    start = 0
    chunk_index = 0

    while start < len(text):
        end = min(start + chunk_size, len(text))

        # Avoid splitting across a Markdown section boundary
        # when a heading occurs inside the proposed chunk.
        for position, _ in sections:
            if start < position < end:
                end = position
                break

        # Prevent an empty chunk if a heading begins at start.
        if end <= start:
            end = min(start + chunk_size, len(text))

        chunk_text = text[start:end]

        metadata = {
            "source": source,
            "source_path": source_path,
            "section": get_section(start, sections),
            "page": None,
            "chunk_index": chunk_index,
            "start_char": start,
            "end_char": end,
        }

        # Guard against inconsistent metadata structures.
        assert list(metadata.keys()) == METADATA_FIELDS

        chunk = {
            "chunk_id": "{}_chunk_{:03d}".format(
                Path(source).stem,
                chunk_index,
            ),
            "text": chunk_text,
            "metadata": metadata,
        }

        chunks.append(chunk)

        # The next chunk begins where this chunk ends.
        # This makes character positions easy to trace.
        start = end
        chunk_index += 1

    return chunks


def chunk_corpus(
    data_dir: Optional[Path] = None,
) -> List[Dict[str, Any]]:
    """Load the corpus and generate metadata-tagged chunks."""

    if data_dir is None:
        documents = load_corpus()
    else:
        documents = load_corpus(data_dir)

    all_chunks = []

    for document in documents:
        document_chunks = make_chunks(document)
        all_chunks.extend(document_chunks)

    return all_chunks


def save_chunks(
    chunks: List[Dict[str, Any]],
    output_file: Path = OUTPUT_FILE,
) -> None:
    """Save chunks and metadata as readable JSON."""

    output_file.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with output_file.open("w", encoding="utf-8") as file:
        json.dump(
            chunks,
            file,
            indent=2,
            ensure_ascii=False,
        )

    print("\nSaved {} chunk(s).".format(len(chunks)))
    print("Output: {}".format(output_file))


def retrieve_chunk(
    chunks: List[Dict[str, Any]],
    query: str,
) -> Optional[Dict[str, Any]]:
    """
    Demonstrate retrieval using simple keyword overlap.

    This is a demonstration, not vector or embedding retrieval.
    """

    query_terms = set(
        re.findall(r"\b\w+\b", query.lower())
    )

    best_chunk = None
    best_score = 0

    for chunk in chunks:
        chunk_terms = set(
            re.findall(
                r"\b\w+\b",
                chunk["text"].lower(),
            )
        )

        score = len(query_terms.intersection(chunk_terms))

        if score > best_score:
            best_score = score
            best_chunk = chunk

    if best_chunk is None:
        print(
            "\n[RETRIEVAL] No matching chunk found "
            "for query: {!r}".format(query)
        )
        return None

    print("\n[RETRIEVAL] Query: {}".format(query))
    print("Match score: {}".format(best_score))
    print("Chunk ID: {}".format(best_chunk["chunk_id"]))
    print("Retrieved text: {}".format(best_chunk["text"][:200]))

    trace_chunk(best_chunk)

    return best_chunk


def trace_chunk(chunk: Dict[str, Any]) -> None:
    """Display the metadata needed to trace a chunk to its source."""

    metadata = chunk["metadata"]

    print("\n[TRACE] Source information")
    print("Source document: {}".format(metadata["source"]))
    print("Source path: {}".format(metadata["source_path"]))
    print("Section: {}".format(metadata["section"]))
    print("Page: {}".format(metadata["page"]))
    print("Chunk index: {}".format(metadata["chunk_index"]))
    print(
        "Character range: {}-{}".format(
            metadata["start_char"],
            metadata["end_char"],
        )
    )


def main() -> None:
    """Run chunking, save sample chunks, and demonstrate tracing."""

    print("Loading documents and creating chunks...")

    chunks = chunk_corpus()

    if not chunks:
        print(
            "No chunks were generated. "
            "Check your sample corpus and document loader."
        )
        return

    # Every chunk must have the same metadata fields.
    for chunk in chunks:
        assert list(chunk["metadata"].keys()) == METADATA_FIELDS

    save_chunks(chunks)

    print("\nTotal chunks: {}".format(len(chunks)))

    # Demonstrate retrieval and source tracing.
    # Change this query to match your sample corpus.
    retrieve_chunk(chunks, "workplace safety")

    print("\nMetadata structure verified for all chunks.")


if __name__ == "__main__":
    main()