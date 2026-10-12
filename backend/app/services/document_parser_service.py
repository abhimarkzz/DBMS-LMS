import io
import logging
import os
import re
from typing import Tuple

logger = logging.getLogger(__name__)

SUPPORTED_EXTENSIONS = {
    ".pdf": "PDF",
    ".docx": "DOCX",
    ".pptx": "PPTX",
    ".txt": "TXT",
    ".md": "MD"
}


class DocumentParserService:
    """
    Parses and cleans text from PDF, DOCX, PPTX, TXT, and MD files.
    Ensures safe handling of corrupted, scanned, or empty documents without crashing.
    """

    @classmethod
    def clean_text(cls, text: str) -> str:
        """Clean extracted raw text: normalize spaces, strip nulls, standardize newlines."""
        if not text:
            return ""
        # Remove null characters
        text = text.replace("\x00", "")
        # Normalize newlines
        text = text.replace("\r\n", "\n").replace("\r", "\n")
        # Collapse excessive newlines (more than 3 into 2)
        text = re.sub(r'\n{3,}', '\n\n', text)
        # Collapse multiple horizontal whitespaces
        lines = [re.sub(r'[ \t]+', ' ', line).strip() for line in text.split("\n")]
        cleaned = "\n".join(lines).strip()
        return cleaned

    @classmethod
    def parse_document(cls, filename: str, file_bytes: bytes) -> Tuple[str, str]:
        """
        Parse file bytes and return (cleaned_text, file_type).
        Raises ValueError with user-friendly error message on invalid/empty/corrupt files.
        """
        if not file_bytes or len(file_bytes) == 0:
            raise ValueError("File is empty (0 bytes).")

        _, ext = os.path.splitext(filename.lower())
        if ext not in SUPPORTED_EXTENSIONS:
            supported = ", ".join(SUPPORTED_EXTENSIONS.values())
            raise ValueError(f"Unsupported file format '{ext}'. Supported formats: {supported}.")

        file_type = SUPPORTED_EXTENSIONS[ext]
        raw_text = ""

        try:
            if file_type == "PDF":
                raw_text = cls._parse_pdf(file_bytes)
            elif file_type == "DOCX":
                raw_text = cls._parse_docx(file_bytes)
            elif file_type == "PPTX":
                raw_text = cls._parse_pptx(file_bytes)
            elif file_type in ("TXT", "MD"):
                raw_text = cls._parse_plain_text(file_bytes)
        except ValueError:
            raise
        except Exception as e:
            logger.error(f"Error parsing {file_type} file {filename}: {e}", exc_info=True)
            raise ValueError(f"Failed to process {file_type} file: {str(e)}")

        cleaned = cls.clean_text(raw_text)
        if not cleaned:
            raise ValueError(f"No usable text could be extracted from {filename}. The document may be empty or contain only images.")

        return cleaned, file_type

    @classmethod
    def _parse_pdf(cls, file_bytes: bytes) -> str:
        import pypdf
        try:
            reader = pypdf.PdfReader(io.BytesIO(file_bytes))
        except Exception as e:
            raise ValueError(f"Invalid or corrupted PDF file: {e}")

        if reader.is_encrypted:
            try:
                reader.decrypt("")
            except Exception:
                raise ValueError("PDF is encrypted and password-protected.")

        pages_text = []
        for idx, page in enumerate(reader.pages):
            try:
                page_text = page.extract_text()
                if page_text and page_text.strip():
                    pages_text.append(f"--- Page {idx + 1} ---\n{page_text.strip()}")
            except Exception as pe:
                logger.debug(f"Could not extract text from PDF page {idx + 1}: {pe}")
                continue

        extracted = "\n\n".join(pages_text).strip()
        if not extracted:
            raise ValueError("No extractable text found in PDF. The document may be scanned or image-based.")
        return extracted

    @classmethod
    def _parse_docx(cls, file_bytes: bytes) -> str:
        import docx
        try:
            doc = docx.Document(io.BytesIO(file_bytes))
        except Exception as e:
            raise ValueError(f"Invalid or corrupted DOCX file: {e}")

        parts = []
        for p in doc.paragraphs:
            if p.text.strip():
                parts.append(p.text.strip())

        # Also extract text from tables
        for table in doc.tables:
            for row in table.rows:
                row_text = " | ".join(cell.text.strip() for cell in row.cells if cell.text.strip())
                if row_text:
                    parts.append(row_text)

        extracted = "\n\n".join(parts).strip()
        if not extracted:
            raise ValueError("DOCX document contains no readable text.")
        return extracted

    @classmethod
    def _parse_pptx(cls, file_bytes: bytes) -> str:
        import pptx
        try:
            prs = pptx.Presentation(io.BytesIO(file_bytes))
        except Exception as e:
            raise ValueError(f"Invalid or corrupted PPTX file: {e}")

        slides_text = []
        for idx, slide in enumerate(prs.slides):
            slide_parts = []
            title = ""
            if slide.shapes.title and slide.shapes.title.has_text_frame:
                title = slide.shapes.title.text.strip()
                if title:
                    slide_parts.append(f"Slide {idx + 1}: {title}")

            for shape in slide.shapes:
                if shape == slide.shapes.title:
                    continue
                if shape.has_text_frame:
                    for p in shape.text_frame.paragraphs:
                        text = p.text.strip()
                        if text and text != title:
                            slide_parts.append(text)

            if slide_parts:
                slides_text.append("\n".join(slide_parts))

        extracted = "\n\n---\n\n".join(slides_text).strip()
        if not extracted:
            raise ValueError("PPTX presentation contains no extractable slide text.")
        return extracted

    @classmethod
    def _parse_plain_text(cls, file_bytes: bytes) -> str:
        for encoding in ("utf-8", "latin-1", "cp1252"):
            try:
                text = file_bytes.decode(encoding)
                if text.strip():
                    return text
            except UnicodeDecodeError:
                continue

        text = file_bytes.decode("utf-8", errors="replace")
        if not text.strip():
            raise ValueError("Text file is empty.")
        return text
