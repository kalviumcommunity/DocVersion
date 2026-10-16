"""
Document Chunking Strategies and Comparison Module.

Implements two primary chunking approaches for developer documentation:
1. Paragraph-Based Chunking (our chosen initial strategy).
2. Fixed-Size Chunking with Overlap (the baseline comparison strategy).

Both strategies operate on identical cleaned text input and provide
reusable, well-tested functions, statistics calculators, and inspectable outputs.
"""

import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_SAMPLE_PATH = ROOT / "data" / "sample_docs" / "python_faq_sample.txt"
DEFAULT_OUTPUT_PATH = ROOT / "outputs" / "chunking_comparison_output.json"


def chunk_by_paragraphs(text: str) -> List[str]:
    """
    Split text into chunks using blank-line boundaries.

    Rules:
    - Splits on blank lines (two or more newlines, with optional whitespace).
    - Trims leading and trailing whitespace from each paragraph.
    - Discards empty paragraphs.
    - Operates safely on empty or whitespace-only strings (returns empty list).
    """
    if not text or not text.strip():
        return []

    # Split on one or more blank lines (e.g. \n\n, \r\n\r\n, \n  \n)
    raw_paragraphs = re.split(r"\n\s*\n", text)
    chunks = []
    for paragraph in raw_paragraphs:
        trimmed = paragraph.strip()
        if trimmed:
            chunks.append(trimmed)

    return chunks


def chunk_by_fixed_size(
    text: str,
    chunk_size: int = 500,
    overlap: int = 100,
) -> List[str]:
    """
    Split text into fixed-size character chunks with overlap.

    Rules:
    - Validates parameters to prevent zero/negative chunk size, negative overlap,
      or overlap >= chunk_size which would produce infinite loops or zero/negative stride.
    - Uses a safe stride of (chunk_size - overlap).
    - Terminates cleanly when the final character of text is reached.
    - Operates safely on empty strings (returns empty list).
    """
    if chunk_size <= 0:
        raise ValueError(
            f"chunk_size must be a positive integer (> 0), got {chunk_size}"
        )
    if overlap < 0:
        raise ValueError(
            f"overlap must be a non-negative integer (>= 0), got {overlap}"
        )
    if overlap >= chunk_size:
        raise ValueError(
            f"overlap ({overlap}) must be strictly less than chunk_size ({chunk_size})"
        )

    if not text:
        return []

    stride = chunk_size - overlap
    text_len = len(text)
    chunks = []
    start = 0

    while start < text_len:
        end = min(start + chunk_size, text_len)
        chunk = text[start:end]
        chunks.append(chunk)

        # Stop when the current chunk reaches the end of the text
        if end == text_len:
            break

        start += stride

    return chunks


def chunk_by_paragraphs_with_metadata(
    text: str,
    source_name: str = "python_faq_sample.txt",
) -> List[Dict[str, Any]]:
    """
    Generate paragraph-based chunks enriched with character offsets and metadata.
    """
    if not text or not text.strip():
        return []

    # Match non-blank blocks separated by blank lines while tracking exact positions
    pattern = re.compile(r"\S.*?(?=\n\s*\n|\Z)", re.DOTALL)
    chunks = []
    chunk_index = 0

    for match in pattern.finditer(text):
        raw_block = match.group(0).strip()
        if not raw_block:
            continue

        start_char = match.start()
        end_char = start_char + len(match.group(0).rstrip())

        chunk = {
            "chunk_id": f"para_chunk_{chunk_index:03d}",
            "chunk_index": chunk_index,
            "strategy": "paragraph_based",
            "start_char": start_char,
            "end_char": end_char,
            "char_length": len(raw_block),
            "text": raw_block,
            "source": source_name,
        }
        chunks.append(chunk)
        chunk_index += 1

    return chunks


def chunk_by_fixed_size_with_metadata(
    text: str,
    chunk_size: int = 500,
    overlap: int = 100,
    source_name: str = "python_faq_sample.txt",
) -> List[Dict[str, Any]]:
    """
    Generate fixed-size chunks enriched with character offsets and metadata.
    """
    raw_chunks = chunk_by_fixed_size(text, chunk_size=chunk_size, overlap=overlap)
    stride = chunk_size - overlap
    chunks = []

    for index, chunk_text in enumerate(raw_chunks):
        start_char = index * stride
        end_char = min(start_char + chunk_size, len(text))
        chunk = {
            "chunk_id": f"fixed_chunk_{index:03d}",
            "chunk_index": index,
            "strategy": "fixed_size_overlap",
            "start_char": start_char,
            "end_char": end_char,
            "char_length": len(chunk_text),
            "chunk_size": chunk_size,
            "overlap": overlap,
            "text": chunk_text,
            "source": source_name,
        }
        chunks.append(chunk)

    return chunks


def calculate_chunk_statistics(chunks: List[str]) -> Dict[str, Any]:
    """
    Calculate statistics for a list of string chunks.

    Returns:
    - chunk_count: Number of chunks.
    - total_characters: Sum of lengths across returned chunks.
    - average_chunk_size: Total characters divided by chunk count (2 decimal places).
    - min_chunk_size: Smallest chunk length in characters.
    - max_chunk_size: Largest chunk length in characters.
    """
    count = len(chunks)
    if count == 0:
        return {
            "chunk_count": 0,
            "total_characters": 0,
            "average_chunk_size": 0.0,
            "min_chunk_size": 0,
            "max_chunk_size": 0,
        }

    lengths = [len(c) for c in chunks]
    total_chars = sum(lengths)
    avg_size = round(total_chars / count, 2)

    return {
        "chunk_count": count,
        "total_characters": total_chars,
        "average_chunk_size": avg_size,
        "min_chunk_size": min(lengths),
        "max_chunk_size": max(lengths),
    }


def compare_strategies(
    text: str,
    chunk_size: int = 500,
    overlap: int = 100,
    source_name: str = "python_faq_sample.txt",
) -> Dict[str, Any]:
    """
    Run both strategies on the identical cleaned text input and compile comparative statistics.
    """
    para_chunks = chunk_by_paragraphs(text)
    fixed_chunks = chunk_by_fixed_size(text, chunk_size=chunk_size, overlap=overlap)

    para_stats = calculate_chunk_statistics(para_chunks)
    fixed_stats = calculate_chunk_statistics(fixed_chunks)

    para_metadata = chunk_by_paragraphs_with_metadata(text, source_name=source_name)
    fixed_metadata = chunk_by_fixed_size_with_metadata(
        text, chunk_size=chunk_size, overlap=overlap, source_name=source_name
    )

    # Pick representative chunks (first 2, middle 1, last 1)
    def select_samples(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        if not items:
            return []
        indices = [0, 1, len(items) // 2, len(items) - 1]
        unique_indices = sorted(list(dict.fromkeys(indices)))
        return [items[i] for i in unique_indices if i < len(items)]

    comparison = {
        "document_info": {
            "source_name": source_name,
            "total_characters": len(text),
        },
        "chosen_strategy": {
            "name": "paragraph_based",
            "rationale": (
                "Preserves structural cohesion of technical explanations, FAQ Q&A units, "
                "bulleted version rules, and code blocks without arbitrary mid-word/mid-sentence splits."
            ),
        },
        "paragraph_based": {
            "settings": {
                "delimiter": "blank_line (\\n\\s*\\n)",
                "trim_whitespace": True,
                "discard_empty": True,
            },
            "statistics": para_stats,
            "representative_samples": select_samples(para_metadata),
            "all_chunks": [
                {
                    "chunk_id": c["chunk_id"],
                    "chunk_index": c["chunk_index"],
                    "char_length": c["char_length"],
                    "start_char": c["start_char"],
                    "end_char": c["end_char"],
                    "preview": c["text"][:100] + ("..." if len(c["text"]) > 100 else ""),
                }
                for c in para_metadata
            ],
        },
        "fixed_size_baseline": {
            "settings": {
                "chunk_size": chunk_size,
                "overlap": overlap,
                "stride": chunk_size - overlap,
            },
            "statistics": fixed_stats,
            "overlap_explanation": (
                "Fixed-size chunking with overlap repeats characters across adjacent chunks. "
                "Consequently, the total characters across chunks exceeds the original text length, "
                "and overlapping regions are counted multiple times in total and average calculations."
            ),
            "representative_samples": select_samples(fixed_metadata),
            "all_chunks": [
                {
                    "chunk_id": c["chunk_id"],
                    "chunk_index": c["chunk_index"],
                    "char_length": c["char_length"],
                    "start_char": c["start_char"],
                    "end_char": c["end_char"],
                    "preview": c["text"][:100] + ("..." if len(c["text"]) > 100 else ""),
                }
                for c in fixed_metadata
            ],
        },
    }

    return comparison


def main() -> None:
    """Execute chunking comparison on the committed sample and save output."""
    if not DEFAULT_SAMPLE_PATH.exists():
        raise FileNotFoundError(
            f"Sample text document not found at {DEFAULT_SAMPLE_PATH}. "
            "Run src/extract_faq_sample.py first or ensure the file is checked out."
        )

    text = DEFAULT_SAMPLE_PATH.read_text(encoding="utf-8")
    comparison = compare_strategies(
        text=text,
        chunk_size=500,
        overlap=100,
        source_name=DEFAULT_SAMPLE_PATH.name,
    )

    # Save to outputs/chunking_comparison_output.json
    DEFAULT_OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with DEFAULT_OUTPUT_PATH.open("w", encoding="utf-8") as f:
        json.dump(comparison, f, indent=2, ensure_ascii=False)

    print(f"=== Document Chunking Comparison ===")
    print(f"Source: {DEFAULT_SAMPLE_PATH.name} ({len(text)} characters)")
    print(f"Output saved: {DEFAULT_OUTPUT_PATH}\n")

    p_stats = comparison["paragraph_based"]["statistics"]
    f_stats = comparison["fixed_size_baseline"]["statistics"]

    print(f"{'Metric':<25} | {'Paragraph-Based (Chosen)':<25} | {'Fixed-Size Baseline (500/100)':<25}")
    print("-" * 80)
    print(f"{'Chunk Count':<25} | {p_stats['chunk_count']:<25} | {f_stats['chunk_count']:<25}")
    print(f"{'Total Characters':<25} | {p_stats['total_characters']:<25} | {f_stats['total_characters']:<25}")
    print(f"{'Average Chunk Size':<25} | {p_stats['average_chunk_size']:<25.2f} | {f_stats['average_chunk_size']:<25.2f}")
    print(f"{'Min Chunk Size':<25} | {p_stats['min_chunk_size']:<25} | {f_stats['min_chunk_size']:<25}")
    print(f"{'Max Chunk Size':<25} | {p_stats['max_chunk_size']:<25} | {f_stats['max_chunk_size']:<25}")


if __name__ == "__main__":
    main()
