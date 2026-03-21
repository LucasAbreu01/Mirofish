from __future__ import annotations

from fastapi import UploadFile

from app.config import settings
from app.utils.logger import get_logger

logger = get_logger("mirofish.document_processor")


async def process_file(file: UploadFile) -> str:
    """Read an uploaded file and return its text content.

    Supports ``.pdf``, ``.txt``, and ``.md`` files.  The returned string is
    truncated to :pyattr:`settings.MAX_DOCUMENT_CHARS`.
    """
    filename = (file.filename or "").lower()
    raw_bytes = await file.read()

    if filename.endswith(".pdf"):
        text = _extract_pdf_text(raw_bytes)
    elif filename.endswith((".txt", ".md")):
        text = raw_bytes.decode("utf-8", errors="replace")
    else:
        raise ValueError(f"Unsupported file type: {filename}")

    return process_text(text)


def process_text(text: str) -> str:
    """Clean whitespace and truncate *text* to the configured maximum length."""
    # Collapse runs of whitespace while preserving paragraph breaks.
    cleaned = "\n".join(
        line.strip() for line in text.splitlines()
    )
    # Remove leading/trailing whitespace.
    cleaned = cleaned.strip()

    if len(cleaned) > settings.MAX_DOCUMENT_CHARS:
        logger.info(
            "Truncating document from %d to %d chars",
            len(cleaned),
            settings.MAX_DOCUMENT_CHARS,
        )
        cleaned = cleaned[: settings.MAX_DOCUMENT_CHARS]

    return cleaned


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _extract_pdf_text(data: bytes) -> str:
    """Extract text from PDF bytes using PyPDF2."""
    import io

    from PyPDF2 import PdfReader

    reader = PdfReader(io.BytesIO(data))
    pages: list[str] = []
    for page in reader.pages:
        page_text = page.extract_text()
        if page_text:
            pages.append(page_text)

    return "\n\n".join(pages)
