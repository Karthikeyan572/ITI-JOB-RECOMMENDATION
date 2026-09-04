import io
from pathlib import Path
import re
from docx import Document
import pymupdf


def clean_text(text: str) -> str:
    """
    Basic cleaning of extracted resume text.
    Standardizes whitespace, strips non-printable artifacts, and removes blank lines.
    """
    if not text:
        return ""

    # Replace multiple spaces/tabs with a single space
    text = re.sub(r"[ \t]+", " ", text)

    # Standardize newline characters
    text = text.replace("\r\n", "\n").replace("\r", "\n")

    # Remove excessive blank lines (more than 2 consecutive newlines)
    text = re.sub(r"\n\s*\n+", "\n\n", text)

    # Strip leading/trailing whitespace
    return text.strip()


def extract_pdf_text(file_source) -> str:
    """
    Extract text from a PDF resume.
    Supports file path (str, Path), bytes, or a file-like stream (e.g. BytesIO, UploadedFile).
    Uses PyMuPDF (fitz replacement).
    """
    text = ""
    try:
        if isinstance(file_source, (str, Path)):
            doc = pymupdf.open(str(file_source))
        elif isinstance(file_source, (bytes, bytearray)):
            doc = pymupdf.open(stream=file_source, filetype="pdf")
        elif hasattr(file_source, "read"):
            # File-like object (e.g., Streamlit UploadedFile or BytesIO)
            content = file_source.read()
            if hasattr(file_source, "seek"):
                file_source.seek(0)
            doc = pymupdf.open(stream=content, filetype="pdf")
        else:
            raise ValueError(f"Unsupported PDF source type: {type(file_source)}")

        with doc:
            for page in doc:
                text += page.get_text() + "\n"

    except Exception as e:
        raise RuntimeError(f"Failed to extract text from PDF: {e}") from e

    return clean_text(text)


def extract_docx_text(file_source) -> str:
    """
    Extract text from a DOCX resume.
    Supports file path (str, Path), bytes, or a file-like stream (e.g. BytesIO, UploadedFile).
    Uses python-docx.
    """
    try:
        if isinstance(file_source, (str, Path)):
            document = Document(str(file_source))
        elif isinstance(file_source, (bytes, bytearray)):
            document = Document(io.BytesIO(file_source))
        elif hasattr(file_source, "read"):
            content = file_source.read()
            if hasattr(file_source, "seek"):
                file_source.seek(0)
            document = Document(io.BytesIO(content))
        else:
            raise ValueError(f"Unsupported DOCX source type: {type(file_source)}")

        paragraphs = []
        for paragraph in document.paragraphs:
            if paragraph.text and paragraph.text.strip():
                paragraphs.append(paragraph.text.strip())

        # Also extract text from tables if present
        for table in document.tables:
            for row in table.rows:
                row_text = " | ".join(cell.text.strip() for cell in row.cells if cell.text.strip())
                if row_text:
                    paragraphs.append(row_text)

        text = "\n".join(paragraphs)
    except Exception as e:
        raise RuntimeError(f"Failed to extract text from DOCX: {e}") from e

    return clean_text(text)


def parse_resume(file_source, filename_hint: str = None) -> str:
    """
    Detect file type and extract resume text.
    file_source can be:
      - str or Path representing a file path
      - bytes / bytearray (requires filename_hint)
      - file-like object with a .name attribute (e.g. Streamlit UploadedFile)
    """
    extension = None

    if isinstance(file_source, (str, Path)):
        p = Path(file_source)
        if not p.exists():
            raise FileNotFoundError(f"Resume file not found: {file_source}")
        extension = p.suffix.lower()
    elif hasattr(file_source, "name") and file_source.name:
        extension = Path(file_source.name).suffix.lower()
    elif filename_hint:
        extension = Path(filename_hint).suffix.lower()

    if not extension:
        raise ValueError("Could not determine file type. Please specify a file with a .pdf or .docx extension.")

    if extension == ".pdf":
        return extract_pdf_text(file_source)
    elif extension == ".docx":
        return extract_docx_text(file_source)
    elif extension == ".txt":
        if isinstance(file_source, (str, Path)):
            with open(file_source, "r", encoding="utf-8", errors="ignore") as f:
                return clean_text(f.read())
        elif isinstance(file_source, (bytes, bytearray)):
            return clean_text(file_source.decode("utf-8", errors="ignore"))
        elif hasattr(file_source, "read"):
            content = file_source.read()
            if isinstance(content, bytes):
                content = content.decode("utf-8", errors="ignore")
            return clean_text(str(content))
        return clean_text(str(file_source))
    else:
        raise ValueError(
            f"Unsupported file format '{extension}'. Please upload a PDF, DOCX, or TXT resume."
        )


if __name__ == "__main__":
    print("Resume Parser Module")
    print("--------------------")
    file_path = input("Enter resume file path: ").strip().strip('"')

    try:
        text = parse_resume(file_path)
        print("\n========== EXTRACTED RESUME TEXT ==========\n")
        print(text)
        print("\n============================================")
        print(f"\nCharacters extracted: {len(text)}")
    except Exception as e:
        print(f"\nError: {e}")