"""
PDF Parsing service powered by PyMuPDF (fitz)
Provides file validation, integrity checks, and text extraction.
"""
import io
import fitz  # PyMuPDF


class PDFParsingError(Exception):
    """Custom exception raised when PDF parsing or validation fails."""
    pass


def validate_pdf_content(file_bytes: bytes, max_size_mb: int = 10) -> None:
    """
    Validate PDF file integrity, size, and header signatures.
    Raises PDFParsingError if validation fails.
    """
    if not file_bytes:
        raise PDFParsingError("Uploaded file is empty.")

    max_size_bytes = max_size_mb * 1024 * 1024
    if len(file_bytes) > max_size_bytes:
        raise PDFParsingError(f"File size exceeds maximum allowed limit of {max_size_mb}MB.")

    # Check for PDF magic header (%PDF-)
    if not file_bytes.startswith(b"%PDF-"):
        raise PDFParsingError("Invalid file signature. File is not a valid PDF document.")


def extract_text_from_pdf(file_bytes: bytes) -> str:
    """
    Extract readable text from a PDF document using PyMuPDF.
    Returns cleaned text string or raises PDFParsingError on failure.
    """
    validate_pdf_content(file_bytes)

    try:
        # Open PDF from in-memory byte stream
        doc = fitz.open(stream=file_bytes, filetype="pdf")
    except Exception as exc:
        raise PDFParsingError(f"Failed to open PDF document: {str(exc)}") from exc

    try:
        if doc.is_encrypted:
            raise PDFParsingError("Password-protected or encrypted PDFs are not supported.")

        if doc.page_count == 0:
            raise PDFParsingError("PDF document has 0 pages.")

        extracted_pages = []
        for page_idx in range(doc.page_count):
            page = doc.load_page(page_idx)
            text = page.get_text("text")
            if text:
                extracted_pages.append(text.strip())

        full_text = "\n\n".join(extracted_pages).strip()

        if not full_text:
            raise PDFParsingError(
                "No selectable text found in the PDF. The document may be an image-only scan or empty."
            )

        # Normalize line endings and whitespace
        cleaned_text = "\n".join(line.rstrip() for line in full_text.splitlines() if line.strip())
        return cleaned_text

    finally:
        doc.close()
