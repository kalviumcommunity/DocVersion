"""
Unit and integration tests for document chunking strategies.

Tests cover:
- Paragraph-based chunking (normal text, blank lines, trimming, empty input).
- Fixed-size chunking with overlap (boundaries, stride, overlap verification, termination).
- Parameter validation for fixed-size chunking (zero, negative, overlap >= chunk_size).
- Statistics calculation and safe empty-list handling.
- Strategy comparison execution on the committed documentation sample.
"""

import pytest
import sys
from pathlib import Path

# Add src to Python path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from chunking_strategies import (
    chunk_by_paragraphs,
    chunk_by_fixed_size,
    chunk_by_paragraphs_with_metadata,
    chunk_by_fixed_size_with_metadata,
    calculate_chunk_statistics,
    compare_strategies,
)


# ============================================================================
# 1. Paragraph-Based Chunking Tests
# ============================================================================

def test_paragraph_chunking_normal_text():
    text = (
        "First paragraph line 1.\nFirst paragraph line 2.\n\n"
        "Second paragraph.\n\n"
        "Third paragraph line 1.\nThird paragraph line 2."
    )
    chunks = chunk_by_paragraphs(text)
    assert len(chunks) == 3
    assert chunks[0] == "First paragraph line 1.\nFirst paragraph line 2."
    assert chunks[1] == "Second paragraph."
    assert chunks[2] == "Third paragraph line 1.\nThird paragraph line 2."


def test_paragraph_chunking_empty_and_whitespace():
    assert chunk_by_paragraphs("") == []
    assert chunk_by_paragraphs("   ") == []
    assert chunk_by_paragraphs("\n\n\n   \n\t\n") == []


def test_paragraph_chunking_trims_whitespace_and_discards_blank_paragraphs():
    text = "\n\n   Paragraph one with spaces.   \n\n\n\n   \n\n  Paragraph two.  \n\n"
    chunks = chunk_by_paragraphs(text)
    assert len(chunks) == 2
    assert chunks[0] == "Paragraph one with spaces."
    assert chunks[1] == "Paragraph two."


def test_paragraph_chunking_single_paragraph_without_trailing_newlines():
    text = "Just a single standalone paragraph without trailing newlines."
    chunks = chunk_by_paragraphs(text)
    assert len(chunks) == 1
    assert chunks[0] == text


def test_paragraph_chunking_metadata():
    text = "Para 1.\n\nPara 2 is longer."
    chunks = chunk_by_paragraphs_with_metadata(text, source_name="test.txt")
    assert len(chunks) == 2
    assert chunks[0]["chunk_index"] == 0
    assert chunks[0]["text"] == "Para 1."
    assert chunks[0]["char_length"] == len("Para 1.")
    assert chunks[0]["source"] == "test.txt"
    assert chunks[1]["chunk_index"] == 1
    assert chunks[1]["text"] == "Para 2 is longer."


# ============================================================================
# 2. Fixed-Size Chunking with Overlap Tests
# ============================================================================

def test_fixed_size_chunking_normal_text():
    # 26 lowercase alphabet letters
    text = "abcdefghijklmnopqrstuvwxyz"
    # chunk_size=10, overlap=3 -> stride=7
    # Chunk 0: 0..10  ("abcdefghij")
    # Chunk 1: 7..17  ("hijklmnopq")
    # Chunk 2: 14..24 ("opqrstuvwx")
    # Chunk 3: 21..26 ("vwxyz")
    chunks = chunk_by_fixed_size(text, chunk_size=10, overlap=3)
    assert len(chunks) == 4
    assert chunks[0] == "abcdefghij"
    assert chunks[1] == "hijklmnopq"
    assert chunks[2] == "opqrstuvwx"
    assert chunks[3] == "vwxyz"


def test_fixed_size_chunking_overlap_content():
    text = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    chunk_size = 15
    overlap = 5
    chunks = chunk_by_fixed_size(text, chunk_size=chunk_size, overlap=overlap)
    
    # Overlap verification: last 5 chars of chunk 0 should match first 5 chars of chunk 1
    assert chunks[0][-overlap:] == chunks[1][:overlap]
    assert chunks[1][-overlap:] == chunks[2][:overlap]


def test_fixed_size_chunking_exact_multiple():
    # Length = 20, chunk_size=10, overlap=5 -> stride=5
    # Chunk 0: 0..10
    # Chunk 1: 5..15
    # Chunk 2: 10..20
    text = "01234567890123456789"
    chunks = chunk_by_fixed_size(text, chunk_size=10, overlap=5)
    assert len(chunks) == 3
    assert chunks[0] == "0123456789"
    assert chunks[1] == "5678901234"
    assert chunks[2] == "0123456789"


def test_fixed_size_chunking_text_shorter_than_chunk_size():
    text = "Short text"
    chunks = chunk_by_fixed_size(text, chunk_size=100, overlap=20)
    assert len(chunks) == 1
    assert chunks[0] == "Short text"


def test_fixed_size_chunking_empty_input():
    assert chunk_by_fixed_size("", chunk_size=100, overlap=20) == []


def test_fixed_size_chunking_zero_overlap():
    text = "ABCDEFGHIJ"
    chunks = chunk_by_fixed_size(text, chunk_size=4, overlap=0)
    assert chunks == ["ABCD", "EFGH", "IJ"]


# ============================================================================
# 3. Fixed-Size Parameter Validation Tests
# ============================================================================

def test_fixed_size_invalid_chunk_size_zero_or_negative():
    with pytest.raises(ValueError, match="chunk_size must be a positive integer"):
        chunk_by_fixed_size("Some text", chunk_size=0, overlap=0)

    with pytest.raises(ValueError, match="chunk_size must be a positive integer"):
        chunk_by_fixed_size("Some text", chunk_size=-10, overlap=0)


def test_fixed_size_negative_overlap():
    with pytest.raises(ValueError, match="overlap must be a non-negative integer"):
        chunk_by_fixed_size("Some text", chunk_size=100, overlap=-5)


def test_fixed_size_overlap_greater_or_equal_to_chunk_size():
    with pytest.raises(ValueError, match="overlap .* must be strictly less than chunk_size"):
        chunk_by_fixed_size("Some text", chunk_size=100, overlap=100)

    with pytest.raises(ValueError, match="overlap .* must be strictly less than chunk_size"):
        chunk_by_fixed_size("Some text", chunk_size=100, overlap=150)


# ============================================================================
# 4. Statistics Calculation Tests
# ============================================================================

def test_statistics_empty_list():
    stats = calculate_chunk_statistics([])
    assert stats["chunk_count"] == 0
    assert stats["total_characters"] == 0
    assert stats["average_chunk_size"] == 0.0
    assert stats["min_chunk_size"] == 0
    assert stats["max_chunk_size"] == 0


def test_statistics_normal_chunks():
    chunks = ["short", "a much longer chunk here", "medium length"]
    # lengths: 5, 24, 13 -> sum = 42, count = 3 -> avg = 42 / 3 = 14.0
    stats = calculate_chunk_statistics(chunks)
    assert stats["chunk_count"] == 3
    assert stats["total_characters"] == 42
    assert stats["average_chunk_size"] == 14.0
    assert stats["min_chunk_size"] == 5
    assert stats["max_chunk_size"] == 24


def test_statistics_average_rounding_two_decimal_places():
    # lengths: 10, 10, 11 -> sum = 31, count = 3 -> 31 / 3 = 10.3333... -> 10.33
    chunks = ["1234567890", "1234567890", "12345678901"]
    stats = calculate_chunk_statistics(chunks)
    assert stats["average_chunk_size"] == 10.33


# ============================================================================
# 5. Integration and Sample Comparison Tests
# ============================================================================

def test_comparison_on_sample_document():
    sample_path = ROOT / "data" / "sample_docs" / "python_faq_sample.txt"
    assert sample_path.exists(), "Committed sample document must exist"

    sample_text = sample_path.read_text(encoding="utf-8")
    assert len(sample_text) > 5000, "Sample document should contain substantial technical documentation"

    result = compare_strategies(
        text=sample_text,
        chunk_size=500,
        overlap=100,
        source_name=sample_path.name,
    )

    p_stats = result["paragraph_based"]["statistics"]
    f_stats = result["fixed_size_baseline"]["statistics"]

    # Verify paragraph stats
    assert p_stats["chunk_count"] == 64
    assert p_stats["total_characters"] == 10810
    assert p_stats["average_chunk_size"] == 168.91
    assert p_stats["min_chunk_size"] == 20
    assert p_stats["max_chunk_size"] == 881

    # Verify fixed-size stats
    assert f_stats["chunk_count"] == 28
    assert f_stats["total_characters"] == 13636
    assert f_stats["average_chunk_size"] == 487.0
    assert f_stats["min_chunk_size"] == 136
    assert f_stats["max_chunk_size"] == 500

    # Overlap character repetition: total characters in fixed-size > raw text length
    assert f_stats["total_characters"] > len(sample_text)
