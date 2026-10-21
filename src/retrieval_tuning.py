
import json
import re
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple


# --------------------------------------------------
# Configuration
# --------------------------------------------------

ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIR = ROOT / "outputs"

CHUNKS_FILE = OUTPUT_DIR / "sample_chunks.json"
QUERY_FILE = OUTPUT_DIR / "retrieval_test_queries.json"
RESULTS_FILE = OUTPUT_DIR / "retrieval_tuning_results.json"
REPORT_FILE = OUTPUT_DIR / "retrieval_tuning_report.md"

TOP_K_VALUES = [1, 3]
MAX_TEST_QUERIES = 5

# These common words contribute little to lexical relevance.
STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "by", "for",
    "from", "in", "is", "it", "of", "on", "or", "that", "the",
    "this", "to", "was", "were", "with", "can", "may", "must",
    "should", "their", "they", "you", "your", "we", "our",
}


# --------------------------------------------------
# File helpers
# --------------------------------------------------

def read_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", encoding="utf-8") as file:
        json.dump(
            value,
            file,
            indent=2,
            ensure_ascii=False,
        )


def tokenize(text: str) -> List[str]:
    """Normalize text into searchable lexical tokens."""

    tokens = re.findall(r"\b[a-z0-9]+\b", text.lower())

    return [
        token for token in tokens
        if token not in STOPWORDS
    ]


def get_metadata(chunk: Dict[str, Any]) -> Dict[str, Any]:
    metadata = chunk.get("metadata", {})
    return metadata if isinstance(metadata, dict) else {}


def get_source(chunk: Dict[str, Any]) -> str:
    return str(get_metadata(chunk).get("source", ""))


# --------------------------------------------------
# Test queries
# --------------------------------------------------

def generate_test_queries(
    chunks: List[Dict[str, Any]],
) -> List[Dict[str, str]]:
    """
    Generate reproducible smoke-test queries from actual chunks.

    These initial queries use text from the target chunk. They
    establish a basic retrieval test but are not an independent
    benchmark of natural user questions.
    """

    queries = []
    seen_sources = set()

    for chunk in chunks:
        text = str(chunk.get("text", "")).strip()
        source = get_source(chunk)
        chunk_id = str(chunk.get("chunk_id", ""))

        if not text or not source or not chunk_id:
            continue

        if source in seen_sources:
            continue

        # Choose a short snippet from the actual source chunk.
        words = text.split()

        if len(words) < 3:
            continue

        query_text = " ".join(words[:12])

        queries.append({
            "query_id": "query_{:02d}".format(len(queries) + 1),
            "query": query_text,
            "expected_source": source,
            "expected_chunk_id": chunk_id,
        })

        seen_sources.add(source)

        if len(queries) >= MAX_TEST_QUERIES:
            break

    return queries


def load_or_create_queries(
    chunks: List[Dict[str, Any]],
) -> List[Dict[str, str]]:
    """
    Reuse a saved test set when present; otherwise create one.

    You can edit retrieval_test_queries.json to use realistic
    questions while preserving the expected source and chunk ID.
    """

    if QUERY_FILE.exists():
        queries = read_json(QUERY_FILE)
        print("Using saved test queries: {}".format(QUERY_FILE))
    else:
        queries = generate_test_queries(chunks)
        write_json(QUERY_FILE, queries)
        print("Created test queries: {}".format(QUERY_FILE))

    if not isinstance(queries, list) or not queries:
        raise ValueError("No test queries were found.")

    for query in queries:
        required = [
            "query_id",
            "query",
            "expected_source",
            "expected_chunk_id",
        ]

        if not all(query.get(key) for key in required):
            raise ValueError(
                "Each test query must contain: {}".format(required)
            )

    return queries


# --------------------------------------------------
# Offline lexical retrieval
# --------------------------------------------------

def score_chunk(
    query_tokens: List[str],
    chunk_tokens: List[str],
    document_frequency: Counter,
    total_documents: int,
) -> float:
    """
    Score a chunk by weighted lexical overlap.

    This is a simple offline ranking heuristic, not BM25,
    a vector similarity score, or a trained retrieval model.
    """

    if not query_tokens or not chunk_tokens:
        return 0.0

    query_terms = set(query_tokens)
    chunk_term_counts = Counter(chunk_tokens)

    # Rare terms contribute more than corpus-wide common terms.
    weighted_total = 0.0
    weighted_matched = 0.0

    for term in query_terms:
        frequency = document_frequency[term]

        # Smoothed inverse-document-frequency weight.
        weight = 1.0 + (
            __import__("math").log(
                (total_documents + 1) / (frequency + 1)
            )
        )

        weighted_total += weight

        if chunk_term_counts[term] > 0:
            weighted_matched += weight

    if weighted_total == 0:
        return 0.0

    return weighted_matched / weighted_total


def build_search_index(
    chunks: List[Dict[str, Any]],
) -> Tuple[List[Dict[str, Any]], Counter]:
    """Tokenize chunks and calculate document frequencies."""

    indexed_chunks = []
    document_frequency = Counter()

    for chunk in chunks:
        text = str(chunk.get("text", ""))

        if not chunk.get("chunk_id"):
            raise ValueError("A chunk is missing chunk_id.")

        tokens = tokenize(text)

        indexed_chunks.append({
            "chunk_id": str(chunk["chunk_id"]),
            "text": text,
            "metadata": get_metadata(chunk),
            "tokens": tokens,
        })

        document_frequency.update(set(tokens))

    return indexed_chunks, document_frequency


def retrieve(
    query: str,
    indexed_chunks: List[Dict[str, Any]],
    document_frequency: Counter,
    k: int,
    source_filter: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Return the top-k lexical matches."""

    query_tokens = tokenize(query)

    if not query_tokens:
        return []

    candidates = []

    for chunk in indexed_chunks:
        source = str(chunk["metadata"].get("source", ""))

        if source_filter is not None and source != source_filter:
            continue

        score = score_chunk(
            query_tokens=query_tokens,
            chunk_tokens=chunk["tokens"],
            document_frequency=document_frequency,
            total_documents=len(indexed_chunks),
        )

        # Exclude chunks with no matching query terms.
        if score <= 0:
            continue

        candidates.append({
            "chunk_id": chunk["chunk_id"],
            "text": chunk["text"],
            "metadata": chunk["metadata"],
            "score": score,
        })

    # Deterministic tie-breaking makes repeated runs reproducible.
    candidates.sort(
        key=lambda item: (
            -item["score"],
            item["chunk_id"],
        )
    )

    return candidates[:k]


# --------------------------------------------------
# Evaluation
# --------------------------------------------------

def evaluate_setting(
    queries: List[Dict[str, str]],
    indexed_chunks: List[Dict[str, Any]],
    document_frequency: Counter,
    k: int,
    use_expected_source_filter: bool = False,
) -> Dict[str, Any]:
    """Evaluate top-1, source hit@k, and exact-chunk hit@k."""

    per_query = []
    top1_source_hits = 0
    source_hits = 0
    exact_chunk_hits = 0
    returned_total = 0

    for test in queries:
        # This is an oracle diagnostic, not a fair production
        # configuration: it uses the answer's known source.
        filter_source = (
            test["expected_source"]
            if use_expected_source_filter
            else None
        )

        results = retrieve(
            query=test["query"],
            indexed_chunks=indexed_chunks,
            document_frequency=document_frequency,
            k=k,
            source_filter=filter_source,
        )

        returned_total += len(results)

        top1_hit = bool(
            results
            and results[0]["metadata"].get("source")
            == test["expected_source"]
        )

        source_hit = any(
            result["metadata"].get("source")
            == test["expected_source"]
            for result in results
        )

        chunk_hit = any(
            result["chunk_id"] == test["expected_chunk_id"]
            for result in results
        )

        top1_source_hits += int(top1_hit)
        source_hits += int(source_hit)
        exact_chunk_hits += int(chunk_hit)

        per_query.append({
            "query_id": test["query_id"],
            "query": test["query"],
            "expected_source": test["expected_source"],
            "expected_chunk_id": test["expected_chunk_id"],
            "top1_source_hit": top1_hit,
            "source_hit_at_k": source_hit,
            "exact_chunk_hit_at_k": chunk_hit,
            "results": results,
        })

    query_count = len(queries)

    if query_count == 0:
        raise ValueError("Cannot evaluate an empty query set.")

    return {
        "setting": (
            "oracle_source_filter_k{}".format(k)
            if use_expected_source_filter
            else "unfiltered_k{}".format(k)
        ),
        "k": k,
        "source_filter": use_expected_source_filter,
        "query_count": query_count,
        "top1_source_hit_rate": top1_source_hits / query_count,
        "source_hit_at_k": source_hits / query_count,
        "exact_chunk_hit_at_k": exact_chunk_hits / query_count,
        "average_returned_results": returned_total / query_count,
        "per_query": per_query,
    }


# --------------------------------------------------
# Reporting
# --------------------------------------------------

def write_report(
    queries: List[Dict[str, str]],
    settings: List[Dict[str, Any]],
    selected_setting: str,
) -> None:
    """Write the measured experiment and chosen configuration."""

    lines = [
        "# Offline Retrieval Tuning Experiment",
        "",
        "- Run time: {}".format(datetime.now().isoformat(timespec="seconds")),
        "- Method: offline keyword-based lexical retrieval",
        "- Corpus: `outputs/sample_chunks.json`",
        "- Test query count: {}".format(len(queries)),
        "",
        "> This experiment does not use embeddings or ChromaDB. "
        "It evaluates lexical retrieval against the actual saved "
        "chunks and their expected source/chunk labels.",
        "",
        "## Test queries",
        "",
    ]

    for query in queries:
        lines.append(
            "- **{}:** {} | Expected source: `{}` | "
            "Expected chunk: `{}`".format(
                query["query_id"],
                query["query"],
                query["expected_source"],
                query["expected_chunk_id"],
            )
        )

    lines.extend([
        "",
        "## Compared settings and measured relevance",
        "",
        "| Setting | k | Source filter | Top-1 source hit | Source hit@k | Exact chunk hit@k |",
        "|---|---:|---|---:|---:|---:|",
    ])

    for result in settings:
        lines.append(
            "| {} | {} | {} | {:.1%} | {:.1%} | {:.1%} |".format(
                result["setting"],
                result["k"],
                "Oracle diagnostic" if result["source_filter"] else "None",
                result["top1_source_hit_rate"],
                result["source_hit_at_k"],
                result["exact_chunk_hit_at_k"],
            )
        )

    lines.extend([
        "",
        "## Selected configuration",
        "",
        "**{}**".format(selected_setting),
        "",
        (
            "Selection uses exact-chunk hit@k, then source hit@k, "
            "among unfiltered settings only. When those scores tie, "
            "the smaller k is selected to reduce unnecessary context."
        ),
        "",
        (
            "The source-filter experiment is an oracle diagnostic: "
            "it filters by the expected answer source already known "
            "from the labels. It is not a fair production setting "
            "unless the source is independently known at query time."
        ),
        "",
        "## Limitations",
        "",
        (
            "The initial test queries are short snippets taken from "
            "their target chunks. This is a smoke test, not an "
            "independent evaluation of realistic user questions. "
            "For stronger evidence, replace them with natural questions "
            "and manually verify the expected relevant chunks."
        ),
        "",
        (
            "The score is a weighted lexical overlap heuristic. "
            "It is not cosine similarity, BM25, or semantic retrieval. "
            "Results must not be presented as vector-search performance."
        ),
        "",
    ])

    REPORT_FILE.parent.mkdir(parents=True, exist_ok=True)
    REPORT_FILE.write_text("\n".join(lines), encoding="utf-8")


# --------------------------------------------------
# Main
# --------------------------------------------------

def main() -> None:
    if not CHUNKS_FILE.exists():
        raise FileNotFoundError(
            "Missing corpus chunks: {}".format(CHUNKS_FILE)
        )

    chunks = read_json(CHUNKS_FILE)

    if not isinstance(chunks, list) or not chunks:
        raise ValueError("The sample corpus is empty or invalid.")

    ids = [chunk.get("chunk_id") for chunk in chunks]

    if any(not chunk_id for chunk_id in ids):
        raise ValueError("Every chunk must have a chunk_id.")

    if len(set(ids)) != len(ids):
        raise ValueError("Duplicate chunk IDs found in corpus.")

    queries = load_or_create_queries(chunks)

    indexed_chunks, document_frequency = build_search_index(chunks)

    print("\n===== OFFLINE RETRIEVAL TUNING =====")
    print("Corpus chunks: {}".format(len(indexed_chunks)))
    print("Test queries: {}".format(len(queries)))
    print("Method: keyword-based lexical retrieval")

    settings = []

    # Fair comparisons: identical queries without answer-source filters.
    for k in TOP_K_VALUES:
        settings.append(
            evaluate_setting(
                queries,
                indexed_chunks,
                document_frequency,
                k=k,
                use_expected_source_filter=False,
            )
        )

    # Diagnostic only: answer source is known in advance.
    settings.append(
        evaluate_setting(
            queries,
            indexed_chunks,
            document_frequency,
            k=3,
            use_expected_source_filter=True,
        )
    )

    fair_settings = [
        item for item in settings
        if not item["source_filter"]
    ]

    best = max(
        fair_settings,
        key=lambda item: (
            item["exact_chunk_hit_at_k"],
            item["source_hit_at_k"],
            -item["k"],
        ),
    )

    selected_setting = "{} (k={})".format(
        best["setting"],
        best["k"],
    )

    output = {
        "method": "offline keyword-based lexical retrieval",
        "corpus_file": str(CHUNKS_FILE.relative_to(ROOT)),
        "corpus_chunk_count": len(indexed_chunks),
        "queries": queries,
        "settings": settings,
        "selected_setting": selected_setting,
        "selection_basis": (
            "Exact chunk hit@k, then source hit@k, then smaller k; "
            "oracle source-filter results excluded from selection."
        ),
    }

    write_json(RESULTS_FILE, output)
    write_report(queries, settings, selected_setting)

    print("\n===== MEASURED RESULTS =====")

    for result in settings:
        print(
            "{} | top1={:.1%} | source_hit@k={:.1%} | "
            "exact_chunk_hit@k={:.1%}".format(
                result["setting"],
                result["top1_source_hit_rate"],
                result["source_hit_at_k"],
                result["exact_chunk_hit_at_k"],
            )
        )

    print("\nSelected setting: {}".format(selected_setting))
    print("Results: {}".format(RESULTS_FILE))
    print("Report: {}".format(REPORT_FILE))


if __name__ == "__main__":
    main()
