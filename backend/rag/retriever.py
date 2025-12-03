import os
from typing import List

from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_core.documents import Document


CHROMA_DIR = os.getenv("CHROMA_DIR", "./chroma_db")


def _get_embeddings():
    model_name = os.getenv("EMBEDDINGS_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
    return HuggingFaceEmbeddings(model_name=model_name)


def get_vectorstore() -> Chroma:
    embeddings = _get_embeddings()
    return Chroma(
        embedding_function=embeddings,
        persist_directory=CHROMA_DIR,
    )


def get_retriever():
    vs = get_vectorstore()
    return vs.as_retriever(search_kwargs={"k": 4})


def add_documents_to_chroma(docs: List[Document]) -> None:
    vs = get_vectorstore()
    vs.add_documents(docs)
    vs.persist()


