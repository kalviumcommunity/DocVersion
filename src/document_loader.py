from pathlib import Path
from typing import Any, Dict, List, Optional

from bs4 import BeautifulSoup

try:
    from pypdf import PdfReader
except ImportError:
    try:
        from PyPDF2 import PdfReader
    except ImportError:
        PdfReader = None


# Project paths
ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DATA_DIR = ROOT / "data" / "sample_corpus"

# Supported document formats
SUPPORTED_EXTENSIONS = {".txt", ".md", ".html", ".htm", ".pdf"}


def load_document(file_path: Path) -> Optional[Dict[str, Any]]:
    """
    Load a document from a supported file format.

    Returns a dictionary containing the source filename, file path,
    and extracted text. Returns None if the document cannot be loaded.
    """

    try:
        # Check whether the file exists
        if not file_path.exists():
            print(f"[SKIP] File does not exist: {file_path}")
            return None

        # Ensure the path points to a file
        if not file_path.is_file():
            print(f"[SKIP] Not a regular file: {file_path}")
            return None

        # Check the file extension
        extension = file_path.suffix.lower()

        if extension not in SUPPORTED_EXTENSIONS:
            print(f"[SKIP] Unsupported format: {file_path.name}")
            return None

        text = ""

        # Load TXT and Markdown files
        if extension in {".txt", ".md"}:
            text = file_path.read_text(
                encoding="utf-8",
                errors="replace"
            )

        # Load HTML files and extract readable text
        elif extension in {".html", ".htm"}:
            html_content = file_path.read_text(
                encoding="utf-8",
                errors="replace"
            )

            soup = BeautifulSoup(html_content, "html.parser")

            # Remove scripts and styles
            for element in soup(["script", "style"]):
                element.decompose()

            text = soup.get_text(
                separator=" ",
                strip=True
            )

        # Load PDF files
        elif extension == ".pdf":
            if PdfReader is None:
                print(f"[SKIP] No PDF library available: {file_path.name}")
                return None

            reader = PdfReader(str(file_path))

            # Skip encrypted PDFs
            if reader.is_encrypted:
                print(f"[SKIP] Encrypted PDF: {file_path.name}")
                return None

            # Extract text from every page
            extracted_pages = []

            for page in reader.pages:
                page_text = page.extract_text() or ""
                extracted_pages.append(page_text)

            text = "\n".join(extracted_pages)

        # Preserve document metadata
        document = {
            "source": file_path.name,
            "source_path": str(file_path),
            "text": text.strip(),
        }

        # Print loading information
        print(f"[LOADED] Source: {document['source']}")
        print(
            f"         Text length: "
            f"{len(document['text'])} characters"
        )
        print(
            f"         Sample: "
            f"{document['text'][:150]!r}"
        )

        return document

    except Exception as exc:
        # Handle corrupted or unreadable files gracefully
        print(
            f"[ERROR] Could not load "
            f"{file_path.name}: {exc}"
        )
        return None


def load_corpus(
    data_dir: Path = DEFAULT_DATA_DIR
) -> List[Dict[str, Any]]:
    """
    Load all supported documents from a directory and its subdirectories.

    Unsupported files are skipped, and errors in individual files
    do not prevent other documents from loading.
    """

    # Validate the corpus directory
    if not data_dir.exists():
        print(
            f"[ERROR] Corpus directory does not exist: "
            f"{data_dir}"
        )
        return []

    if not data_dir.is_dir():
        print(
            f"[ERROR] Corpus path is not a directory: "
            f"{data_dir}"
        )
        return []

    documents = []

    # Recursively discover files
    for file_path in sorted(data_dir.rglob("*")):

        if not file_path.is_file():
            continue

        # Skip unsupported formats
        if file_path.suffix.lower() not in SUPPORTED_EXTENSIONS:
            print(
                f"[SKIP] Unsupported format: "
                f"{file_path.name}"
            )
            continue

        # Load each supported document
        document = load_document(file_path)

        if document is not None:
            documents.append(document)

    print(f"\nLoaded {len(documents)} document(s).")

    return documents


if __name__ == "__main__":
    load_corpus()