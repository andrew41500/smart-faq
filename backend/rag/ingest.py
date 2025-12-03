import os
from pathlib import Path
from typing import List

from langchain_core.documents import Document

from backend.rag.parsers import parse_pdf, parse_docx
from backend.rag.retriever import add_documents_to_chroma


SAMPLE_DOCS_DIR = os.getenv("SAMPLE_DOCS_DIR", "./sample_docs")


def load_documents() -> List[Document]:
    docs: List[Document] = []
    base = Path(SAMPLE_DOCS_DIR)
    if not base.exists():
        return docs

    for path in base.rglob("*"):
        if not path.is_file():
            continue
        suffix = path.suffix.lower()
        if suffix == ".pdf":
            pages = parse_pdf(str(path))
            for i, text in enumerate(pages):
                docs.append(
                    Document(
                        page_content=text,
                        metadata={"source": str(path), "page": i + 1},
                    )
                )
        elif suffix in (".docx", ".doc"):
            paras = parse_docx(str(path))
            for i, text in enumerate(paras):
                docs.append(
                    Document(
                        page_content=text,
                        metadata={"source": str(path), "chunk": i + 1},
                    )
                )
    return docs


def ingest():
    docs = load_documents()
    if not docs:
        print(f"No documents found in {SAMPLE_DOCS_DIR}. Nothing to ingest.")
        return
    print(f"Ingesting {len(docs)} chunks into ChromaDB...")
    add_documents_to_chroma(docs)
    print("Ingestion complete.")


if __name__ == "__main__":
    ingest()


