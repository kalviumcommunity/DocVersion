import json
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv
from openai import OpenAI


# --------------------------------------------------
# Configuration
# --------------------------------------------------

ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIR = ROOT / "outputs"

CHUNKS_FILE = OUTPUT_DIR / "sample_chunks.json"
CACHE_FILE = OUTPUT_DIR / "embeddings_cache.json"
SUMMARY_FILE = OUTPUT_DIR / "batch_embedding_summary.md"

MODEL_NAME = "text-embedding-3-small"

# Configurable settings
BATCH_SIZE = int(os.getenv("EMBEDDING_BATCH_SIZE", "16"))
MAX_RETRIES = int(os.getenv("EMBEDDING_MAX_RETRIES", "3"))
INITIAL_BACKOFF_SECONDS = 1.0

# Approximate price per million input tokens.
# Verify the current price before using this estimate for budgeting.
PRICE_PER_MILLION_TOKENS = float(
    os.getenv("EMBEDDING_PRICE_PER_MILLION_TOKENS", "0.02")
)

# Set EMBEDDING_DRY_RUN=true to test the pipeline without an API.
DRY_RUN = (
    os.getenv("EMBEDDING_DRY_RUN", "false").lower()
    == "true"
)


# --------------------------------------------------
# Helpers
# --------------------------------------------------

def load_json(path: Path, default: Any) -> Any:
    """Load JSON or return a default if the file does not exist."""

    if not path.exists():
        return default

    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def save_json(path: Path, data: Any) -> None:
    """Save JSON to disk."""

    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", encoding="utf-8") as file:
        json.dump(data, file, indent=2, ensure_ascii=False)


def get_chunk_id(chunk: Dict[str, Any]) -> str:
    """Return a stable identifier for a chunk."""

    chunk_id = chunk.get("chunk_id")

    if not chunk_id:
        raise ValueError(
            "Every chunk must have a chunk_id."
        )

    return str(chunk_id)


def estimate_tokens(texts: List[str]) -> int:
    """
    Estimate token usage.

    This is a rough estimate, not an exact tokenizer count.
    Actual API usage should be used for billing reconciliation.
    """

    return sum(max(1, (len(text) + 3) // 4) for text in texts)


def split_batches(
    items: List[Dict[str, Any]],
    batch_size: int,
) -> List[List[Dict[str, Any]]]:
    """Split items into batches of configurable size."""

    if batch_size <= 0:
        raise ValueError(
            "Batch size must be greater than zero."
        )

    return [
        items[index:index + batch_size]
        for index in range(0, len(items), batch_size)
    ]


# --------------------------------------------------
# Cache management
# --------------------------------------------------

def load_cache() -> Dict[str, Any]:
    """
    Load previously generated embeddings.

    Each cache entry stores its model and original text.
    A changed text or model will be re-embedded.
    """

    cache = load_json(CACHE_FILE, {})

    if not isinstance(cache, dict):
        raise ValueError(
            "Embedding cache must be a JSON object."
        )

    return cache


def is_cached(
    chunk: Dict[str, Any],
    cache: Dict[str, Any],
) -> bool:
    """Check whether a chunk has a reusable embedding."""

    chunk_id = get_chunk_id(chunk)
    entry = cache.get(chunk_id)

    if not isinstance(entry, dict):
        return False

    return (
        entry.get("model") == MODEL_NAME
        and entry.get("text") == chunk.get("text", "")
        and isinstance(entry.get("embedding"), list)
        and len(entry["embedding"]) > 0
    )


# --------------------------------------------------
# Embedding generation
# --------------------------------------------------

def embed_batch_with_retry(
    client: Any,
    batch: List[Dict[str, Any]],
    batch_number: int,
    retry_log: List[str],
) -> Optional[List[List[float]]]:
    """
    Generate embeddings for a batch.

    Retries transient API failures using exponential backoff.
    Failed batches are recorded in the run summary.
    """

    texts = [chunk["text"] for chunk in batch]

    for attempt in range(MAX_RETRIES + 1):
        try:
            response = client.embeddings.create(
                model=MODEL_NAME,
                input=texts,
            )

            # Sort by the response index to preserve input order.
            response_data = sorted(
                response.data,
                key=lambda item: item.index,
            )

            vectors = [
                item.embedding for item in response_data
            ]

            if len(vectors) != len(batch):
                raise ValueError(
                    "The API returned an unexpected number "
                    "of embeddings."
                )

            print(
                "[SUCCESS] Batch {}: {} embedding(s)".format(
                    batch_number,
                    len(vectors),
                )
            )

            return vectors

        except Exception as exc:
            if attempt >= MAX_RETRIES:
                message = (
                    "Batch {} failed after {} attempt(s): {}"
                ).format(
                    batch_number,
                    attempt + 1,
                    str(exc),
                )

                retry_log.append(message)
                print("[FAILED] " + message)

                return None

            delay = INITIAL_BACKOFF_SECONDS * (2 ** attempt)

            message = (
                "Batch {} attempt {} failed: {}. "
                "Retrying in {:.1f}s."
            ).format(
                batch_number,
                attempt + 1,
                str(exc),
                delay,
            )

            retry_log.append(message)
            print("[RETRY] " + message)

            time.sleep(delay)

    return None


# --------------------------------------------------
# Main pipeline
# --------------------------------------------------

def run_pipeline() -> Dict[str, Any]:
    """Embed new chunks, reuse cached vectors, and report totals."""

    if BATCH_SIZE <= 0:
        raise ValueError(
            "EMBEDDING_BATCH_SIZE must be greater than zero."
        )

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    chunks = load_json(CHUNKS_FILE, [])

    if not isinstance(chunks, list):
        raise ValueError(
            "sample_chunks.json must contain a JSON list."
        )

    cache = load_cache()

    # Validate chunk identifiers and content.
    seen_ids = set()

    for chunk in chunks:
        if not isinstance(chunk, dict):
            raise ValueError(
                "Each chunk must be a JSON object."
            )

        chunk_id = get_chunk_id(chunk)

        if chunk_id in seen_ids:
            raise ValueError(
                "Duplicate chunk_id found: {}".format(chunk_id)
            )

        seen_ids.add(chunk_id)

        if not isinstance(chunk.get("text"), str):
            raise ValueError(
                "Chunk {} must contain text.".format(chunk_id)
            )

    skipped = []
    pending = []

    for chunk in chunks:
        if is_cached(chunk, cache):
            skipped.append(chunk)
        else:
            pending.append(chunk)

    print("\n========== BATCH EMBEDDING RUN ==========")
    print("Total chunks: {}".format(len(chunks)))
    print("Already embedded and skipped: {}".format(len(skipped)))
    print("Chunks requiring embeddings: {}".format(len(pending)))
    print("Batch size: {}".format(BATCH_SIZE))
    print("Model: {}".format(MODEL_NAME))
    print("Dry run: {}".format(DRY_RUN))

    retry_log = []
    failed_batches = []
    generated = 0
    estimated_tokens = 0
    actual_api_calls = 0

    if DRY_RUN:
        # Validate batching without inventing embeddings.
        batches = split_batches(pending, BATCH_SIZE)

        print(
            "\n[DRY RUN] Would send {} batch(es).".format(
                len(batches)
            )
        )

        for index, batch in enumerate(batches, start=1):
            print(
                "[DRY RUN] Batch {} contains {} chunk(s).".format(
                    index,
                    len(batch),
                )
            )

        print(
            "[DRY RUN] No API calls made and no embeddings generated."
        )

    elif pending:
        load_dotenv(ROOT / ".env")

        api_key = os.getenv("OPENAI_API_KEY")

        if not api_key:
            raise RuntimeError(
                "OPENAI_API_KEY is missing. Add it to .env, "
                "or set EMBEDDING_DRY_RUN=true to test batching."
            )

        client = OpenAI(api_key=api_key)
        batches = split_batches(pending, BATCH_SIZE)

        for batch_number, batch in enumerate(batches, start=1):
            batch_texts = [
                chunk["text"] for chunk in batch
            ]

            batch_tokens = estimate_tokens(batch_texts)

            vectors = embed_batch_with_retry(
                client,
                batch,
                batch_number,
                retry_log,
            )

            if vectors is None:
                failed_batches.append({
                    "batch_number": batch_number,
                    "chunk_ids": [
                        get_chunk_id(chunk) for chunk in batch
                    ],
                })
                continue

            actual_api_calls += 1
            estimated_tokens += batch_tokens

            for chunk, vector in zip(batch, vectors):
                chunk_id = get_chunk_id(chunk)

                cache[chunk_id] = {
                    "model": MODEL_NAME,
                    "text": chunk["text"],
                    "embedding": vector,
                    "metadata": chunk.get("metadata", {}),
                }

                generated += 1

            # Save after each successful batch.
            # If the script stops, completed work remains cached.
            save_json(CACHE_FILE, cache)

    # Cost is based on successfully embedded texts only.
    estimated_cost = (
        estimated_tokens
        / 1_000_000
        * PRICE_PER_MILLION_TOKENS
    )

    summary = {
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "model": MODEL_NAME,
        "dry_run": DRY_RUN,
        "batch_size": BATCH_SIZE,
        "total_chunks": len(chunks),
        "skipped_chunks": len(skipped),
        "pending_chunks": len(pending),
        "embeddings_generated": generated,
        "failed_batches": failed_batches,
        "failure_count": sum(
            len(batch["chunk_ids"])
            for batch in failed_batches
        ),
        "retry_events": retry_log,
        "api_batches_succeeded": actual_api_calls,
        "estimated_tokens_embedded": estimated_tokens,
        "price_per_million_tokens_usd": PRICE_PER_MILLION_TOKENS,
        "approximate_cost_usd": round(estimated_cost, 8),
        "cache_entries": len(cache),
        "note": (
            "Token usage is estimated from text length. "
            "The cost is approximate, not an invoice."
        ),
    }

    save_json(
        OUTPUT_DIR / "batch_embedding_summary.json",
        summary,
    )

    write_markdown_summary(summary)

    print("\n========== RUN SUMMARY ==========")
    print("Total chunks: {}".format(summary["total_chunks"]))
    print("Embeddings generated: {}".format(generated))
    print("Skipped chunks: {}".format(len(skipped)))
    print("Failed chunks: {}".format(summary["failure_count"]))
    print("Failed batches: {}".format(len(failed_batches)))
    print("Retry events: {}".format(len(retry_log)))
    print("Estimated tokens: {}".format(estimated_tokens))
    print(
        "Approximate cost: ${:.8f}".format(estimated_cost)
    )

    if DRY_RUN:
        print(
            "\nNOTE: This was a dry run; no real vectors were generated."
        )

    return summary


def write_markdown_summary(summary: Dict[str, Any]) -> None:
    """Write a human-readable summary for the assignment."""

    lines = [
        "# Batch Embedding Run Summary",
        "",
        "- Timestamp: {}".format(summary["timestamp"]),
        "- Model: `{}`".format(summary["model"]),
        "- Dry run: {}".format(summary["dry_run"]),
        "- Configured batch size: {}".format(summary["batch_size"]),
        "- Total chunks: {}".format(summary["total_chunks"]),
        "- Embeddings generated: {}".format(
            summary["embeddings_generated"]
        ),
        "- Skipped chunks: {}".format(summary["skipped_chunks"]),
        "- Failed chunks: {}".format(summary["failure_count"]),
        "- Failed batches: {}".format(
            len(summary["failed_batches"])
        ),
        "- Retry events: {}".format(
            len(summary["retry_events"])
        ),
        "- Successful API batches: {}".format(
            summary["api_batches_succeeded"]
        ),
        "- Estimated tokens embedded: {}".format(
            summary["estimated_tokens_embedded"]
        ),
        "- Approximate cost (USD): ${:.8f}".format(
            summary["approximate_cost_usd"]
        ),
        "",
        "## Retry log",
        "",
    ]

    if summary["retry_events"]:
        for event in summary["retry_events"]:
            lines.append("- " + event)
    else:
        lines.append(
            "No retry events occurred during this run."
        )

    lines.extend([
        "",
        "## Failed batches",
        "",
    ])

    if summary["failed_batches"]:
        for batch in summary["failed_batches"]:
            lines.append(
                "- Batch {}: {}".format(
                    batch["batch_number"],
                    ", ".join(batch["chunk_ids"]),
                )
            )
    else:
        lines.append("No batches failed.")

    lines.extend([
        "",
        "## Cost estimation note",
        "",
        summary["note"],
        "",
    ])

    if summary["dry_run"]:
        lines.append(
            "**Dry run:** No API calls were made and no embeddings "
            "were generated. The output validates batching logic only."
        )

    with SUMMARY_FILE.open("w", encoding="utf-8") as file:
        file.write("\n".join(lines))


if __name__ == "__main__":
    run_pipeline()