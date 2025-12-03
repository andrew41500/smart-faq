from typing import List

from PyPDF2 import PdfReader
from docx import Document as DocxDocument


def parse_pdf(path: str) -> List[str]:
    """
    Extract text from a PDF file, returning a list of page texts.
    """
    reader = PdfReader(path)
    pages = []
    for page in reader.pages:
        text = page.extract_text() or ""
        if text.strip():
            pages.append(text.strip())
    return pages


def parse_docx(path: str) -> List[str]:
    """
    Extract text from a DOCX file, returning paragraphs as chunks.
    """
    doc = DocxDocument(path)
    chunks = []
    for para in doc.paragraphs:
        text = para.text.strip()
        if text:
            chunks.append(text)
    return chunks


