"""
droit/ingestion/loader.py
--------------------------
Stage 1: Document Loading

Responsible for reading a raw document from disk and returning its text.
This is the single entry point for all file types into the pipeline.

OCR HOOK
--------
When OCR support is added (next iteration), it will live here as a new
`load_pdf_ocr()` function and be dispatched automatically by `load_document()`
based on file extension. No other module needs to change.

Supported now:
  - .txt   (plain text)

Coming soon (OCR):
  - .pdf   (scanned or native PDF via pdfplumber / pytesseract)
  - .docx  (via python-docx)
  - .png / .jpg (via pytesseract)
"""

from __future__ import annotations

import logging
from pathlib import Path

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def load_document(file_path: str | Path) -> str:
    """
    Load a legal document from disk and return its raw text content.

    Parameters
    ----------
    file_path : str | Path
        Absolute or relative path to the document.

    Returns
    -------
    str
        Raw text extracted from the document.

    Raises
    ------
    FileNotFoundError
        If the file does not exist.
    ValueError
        If the file type is not yet supported.
    """
    path = Path(file_path).resolve()

    if not path.exists():
        raise FileNotFoundError(f"Document not found: {path}")

    suffix = path.suffix.lower()
    logger.info("Loading document: %s (type: %s)", path.name, suffix)

    if suffix == ".txt":
        return _load_txt(path)

    elif suffix == ".pdf":
        return _load_pdf_ocr(path)
    elif suffix in (".png", ".jpg", ".jpeg", ".tiff"):
        return _load_image_ocr(path)
    elif suffix == ".docx":
        return _load_docx(path)

    raise ValueError(
        f"Unsupported file type '{suffix}'. "
        "Supported types: .txt  |  OCR (.pdf, .png, .jpg) coming soon."
    )


# ---------------------------------------------------------------------------
# Private loaders — one per file type
# ---------------------------------------------------------------------------

def _load_txt(path: Path) -> str:
    """Read a plain-text file with UTF-8 encoding."""
    with open(path, "r", encoding="utf-8") as fh:
        text = fh.read()
    logger.debug("Loaded %d characters from %s", len(text), path.name)
    return text


# ---------------------------------------------------------------------------
# OCR stubs (to be implemented in the next iteration)
# ---------------------------------------------------------------------------

def _load_pdf_ocr(path: Path) -> str:
    """
    Extract text from a PDF using pdfplumber for native text and
    pytesseract for scanned/image-only pages.
    """
    import pdfplumber
    import pytesseract

    text_parts = []
    try:
        with pdfplumber.open(path) as pdf:
            for i, page in enumerate(pdf.pages):
                page_text = page.extract_text()
                
                # If page is mostly image/scanned, native text will be empty or very short
                if page_text and len(page_text.strip()) > 50:
                    text_parts.append(page_text)
                else:
                    logger.debug("Running OCR on page %d of %s", i + 1, path.name)
                    # Fallback to OCR on the page image
                    img = page.to_image(resolution=300).original
                    ocr_text = pytesseract.image_to_string(img)
                    text_parts.append(ocr_text)
                    
        return "\n\n".join(text_parts)
    except Exception as exc:
        logger.error("Failed to extract text from PDF %s: %s", path.name, exc)
        raise

def _load_image_ocr(path: Path) -> str:
    """Run pytesseract on a single image file."""
    import pytesseract
    from PIL import Image
    try:
        logger.debug("Running OCR on image %s", path.name)
        img = Image.open(path)
        text = pytesseract.image_to_string(img)
        return text
    except Exception as exc:
        logger.error("Failed to extract text from image %s: %s", path.name, exc)
        raise

def _load_docx(path: Path) -> str:
    """Extract text from a .docx file using python-docx."""
    import docx
    try:
        doc = docx.Document(path)
        text_parts = [para.text for para in doc.paragraphs]
        return "\n\n".join(text_parts)
    except Exception as exc:
        logger.error("Failed to extract text from docx %s: %s", path.name, exc)
        raise
