"""
Extract and prepare a reproducible plain-text documentation sample from faq.pdf.

Source:
    Document: Python Frequently Asked Questions (faq.pdf)
    Release: Python 3.13.3 (April 08, 2025)
    Authors: Guido van Rossum and the Python development team
    Publisher: Python Software Foundation (PSF)
    License: Python Software Foundation License Version 2 (PSF-2.0)
    Target Section: Chapter 1 (General Python FAQ), Section 1.1 (General Information)
    Output: data/sample_docs/python_faq_sample.txt
"""

import re
import sys
from pathlib import Path

# Project paths
ROOT = Path(__file__).resolve().parent.parent
RAW_PDF_PATH = ROOT / "data" / "raw" / "faq.pdf"
SAMPLE_OUTPUT_DIR = ROOT / "data" / "sample_docs"
SAMPLE_OUTPUT_FILE = SAMPLE_OUTPUT_DIR / "python_faq_sample.txt"


def extract_raw_pages_pypdfium(pdf_path: Path, start_page: int = 8, end_page: int = 14) -> str:
    """Extract text from specified 0-indexed page range using pypdfium2."""
    import pypdfium2 as pdfium
    pdf = pdfium.PdfDocument(str(pdf_path))
    extracted = []
    for p in range(start_page, min(end_page, len(pdf))):
        text = pdf[p].get_textpage().get_text_range()
        extracted.append(text)
    return "\n".join(extracted)


def extract_raw_pages_fallback(pdf_path: Path, start_page: int = 8, end_page: int = 14) -> str:
    """Fallback text extraction using pypdf or PyPDF2."""
    try:
        from pypdf import PdfReader
    except ImportError:
        from PyPDF2 import PdfReader

    reader = PdfReader(str(pdf_path))
    extracted = []
    for p in range(start_page, min(end_page, len(reader.pages))):
        text = reader.pages[p].extract_text() or ""
        extracted.append(text)
    return "\n".join(extracted)


def extract_raw_text(pdf_path: Path) -> str:
    """Extract raw text from PDF using the best available engine."""
    try:
        return extract_raw_pages_pypdfium(pdf_path)
    except Exception:
        return extract_raw_pages_fallback(pdf_path)


def clean_faq_text(raw_text: str) -> str:
    """
    Clean extracted PDF text into clean, blank-line-separated documentation text:
    1. Reconcile soft-hyphens / line-break artifacts (\\ufffe).
    2. Normalize line endings to Unix newlines.
    3. Filter running headers, page numbers, and chapter banners.
    4. Isolate Section 1.1 (General Information, questions 1.1.1 to 1.1.17).
    5. Reconstruct logical paragraphs separated by blank lines (\\n\\n).
    """
    text = raw_text.replace("\ufffe", "").replace("\r\n", "\n")

    lines = text.splitlines()
    filtered_lines = []
    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        # Filter running headers / footers
        if stripped.startswith("Python Frequently Asked Questions, Release"):
            continue
        if stripped in {"CHAPTER", "ONE", "GENERAL PYTHON FAQ"}:
            continue
        if re.match(r"^\d+\s+Chapter\s+\d+.*", stripped):
            continue
        if re.match(r"^\d+\.\d+\.?\s+General Information\s+\d+$", stripped):
            continue
        if stripped in {"1", "2", "3"}:
            continue
        filtered_lines.append(stripped)

    # Locate Section 1.1 boundaries
    start_idx = -1
    end_idx = len(filtered_lines)
    for i, line in enumerate(filtered_lines):
        if line.startswith("1.1 General Information"):
            start_idx = i
        elif line.startswith("1.2 Python in the real world") and start_idx != -1:
            end_idx = i
            break

    if start_idx == -1:
        start_idx = 0

    section_lines = filtered_lines[start_idx:end_idx]

    # Reconstruct paragraphs separated by double newlines
    paragraphs = []
    current_para = []

    for line in section_lines:
        is_heading = bool(re.match(r"^1\.1(\.\d+)?\s+", line))
        is_bullet = line.startswith("•")

        if current_para:
            prev_line = current_para[-1]
            prev_ends_sentence = prev_line.endswith(
                (".", "?", ":", "”", "’", "'", ".)", "!)", ":)")
            )
            prev_is_heading = bool(re.match(r"^1\.1(\.\d+)?\s+", current_para[0]))

            # Headings and bullet points start new paragraphs
            if is_heading or is_bullet:
                paragraphs.append(" ".join(current_para))
                current_para = [line]
                continue
            # Standalone heading followed by body text starts new paragraph
            elif prev_is_heading:
                paragraphs.append(" ".join(current_para))
                current_para = [line]
                continue
            # Sentences followed by new narrative blocks or distinct topical statements
            elif prev_ends_sentence and line.startswith((
                "I had", "It occurred", "During the", "In February", "Donations to",
                "See the", "The Python logo", "Here’s a", "The pdb module", "Consult the",
                "The documentation", "There are", "Announcements of", "More info",
                "You can also", "For more", "Guido van", "The very first", "Not all releases",
                "Alpha, beta", "In other words", "You may also find", "See PEP", "See Developer",
                "Yes, there", "The standard", "Alpha and beta", "To report"
            )):
                paragraphs.append(" ".join(current_para))
                current_para = [line]
                continue

        current_para.append(line)

    if current_para:
        paragraphs.append(" ".join(current_para))

    # Join paragraphs with clean blank-line separators
    return "\n\n".join(paragraphs)


def prepare_sample(pdf_path: Path = RAW_PDF_PATH, output_file: Path = SAMPLE_OUTPUT_FILE) -> str:
    """Extract, clean, and save the sample documentation file."""
    if not pdf_path.exists():
        raise FileNotFoundError(f"Raw source PDF not found at {pdf_path}")

    print(f"Reading source PDF: {pdf_path}")
    raw_text = extract_raw_text(pdf_path)
    print(f"Extracted {len(raw_text)} raw characters.")

    cleaned = clean_faq_text(raw_text)
    print(f"Cleaned sample has {len(cleaned)} characters.")

    output_file.parent.mkdir(parents=True, exist_ok=True)
    with output_file.open("w", encoding="utf-8") as f:
        f.write(cleaned)

    print(f"Saved prepared plain-text sample to {output_file}")
    return cleaned


if __name__ == "__main__":
    prepare_sample()
