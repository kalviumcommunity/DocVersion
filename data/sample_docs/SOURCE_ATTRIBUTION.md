# Source Attribution & Provenance: Python FAQ Sample

## Document Provenance

- **Document Title**: Python Frequently Asked Questions (FAQ)
- **Release Version**: Python 3.13.3
- **Publication Date**: April 08, 2025
- **Authors**: Guido van Rossum and the Python Development Team
- **Publisher**: Python Software Foundation (PSF)
- **Official Documentation URL**: <https://docs.python.org/3/faq/>
- **Raw File Stored Locally**: `data/raw/faq.pdf` (561,192 bytes, 125 pages, ignored by Git via `.gitignore`)
- **Committed Plain-Text Sample**: `data/sample_docs/python_faq_sample.txt` (10,936 characters, 64 paragraphs)

## Licensing and Redistribution

- **Primary License**: [Python Software Foundation License Version 2 (PSF-2.0)](https://docs.python.org/3/license.html#psf-license)
- **Code Examples License**: [Zero-Clause BSD License (0BSD)](https://docs.python.org/3/license.html#bsd0)
- **Redistribution Terms**: The PSF-2.0 license permits copying, modifying, and redistributing Python documentation and software in source or binary form, provided the copyright notice and license text are retained.

## Selected Section Details

- **Chapter**: Chapter 1 — General Python FAQ
- **Section**: 1.1 — General Information
- **Entries Included**:
  1. `1.1.1 What is Python?`
  2. `1.1.2 What is the Python Software Foundation?`
  3. `1.1.3 Are there copyright restrictions on the use of Python?`
  4. `1.1.4 Why was Python created in the first place?`
  5. `1.1.5 What is Python good for?`
  6. `1.1.6 How does the Python version numbering scheme work?` *(highly relevant to Version-Aware Doc Assistant)*
  7. `1.1.7 How do I obtain a copy of the Python source?`
  8. `1.1.8 How do I get documentation on Python?`
  9. `1.1.9 I’ve never programmed before. Is there a Python tutorial?`
  10. `1.1.10 Is there a newsgroup or mailing list devoted to Python?`
  11. `1.1.11 How do I get a beta test version of Python?`
  12. `1.1.12 How do I submit bug reports and patches for Python?`
  13. `1.1.13 Are there any published articles about Python that I can reference?`
  14. `1.1.14 Are there any books on Python?`
  15. `1.1.15 Where in the world is www.python.org located?`
  16. `1.1.16 Why is it called Python?`
  17. `1.1.17 Do I have to like “Monty Python’s Flying Circus”?`

## Text Preparation & Cleaning Steps

1. **Extraction**: Raw text extracted from pages 9–14 of `data/raw/faq.pdf`.
2. **Artifact Correction**: Removed font soft-hyphen anomalies (`\ufffe`) produced during line wraps (e.g., `ver\ufffesions` -> `versions`).
3. **Header/Footer Stripping**: Filtered running page headers (`Python Frequently Asked Questions, Release 3.13.3`), chapter titles (`CHAPTER ONE`), and printed page numbers.
4. **Paragraph Preservation**: Logical paragraphs, section headings, and bullet points were normalized and delineated by blank-line boundaries (`\n\n`), ensuring valid input for paragraph-based chunking.

## Reproducibility

To re-extract and verify the plain-text sample from the original PDF:
```bash
python src/extract_faq_sample.py
```
Reviewers without access to the local raw PDF can directly run the comparison against `data/sample_docs/python_faq_sample.txt`.
