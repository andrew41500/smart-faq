from typing import Dict, Any, List

from langchain_core.documents import Document

from backend.llm import LLMClient


def intent_classification_node(state: Dict[str, Any], llm: LLMClient) -> Dict[str, Any]:
    """
    Simple, deterministic intent classifier.

    We deliberately avoid using the LLM here so that product questions
    consistently go through the DOCUMENT (RAG) path.
    """
    query: str = state["query"]
    q = query.lower().strip()

    # Treat short greetings / meta questions as GENERAL.
    greetings = ["hi", "hello", "hey", "good morning", "good evening"]
    meta_keywords = ["who are you", "what can you do", "how do i use this assistant"]

    if any(q.startswith(g) for g in greetings) or any(k in q for k in meta_keywords):
        intent = "GENERAL"
    else:
        # Everything else is treated as DOCUMENT so that we use the manuals/FAQs.
        intent = "DOCUMENT"

    return {**state, "intent": intent}


def document_retrieval_node(state: Dict[str, Any], retriever) -> Dict[str, Any]:
    query = state["query"]
    docs: List[Document] = retriever.get_relevant_documents(query)
    return {**state, "retrieved_docs": docs}


def general_qa_node(state: Dict[str, Any], llm: LLMClient) -> Dict[str, Any]:
    query = state["query"]
    system_prompt = (
        "You are a helpful FAQ assistant for a fictional SaaS product called SmartSupport Cloud.\n"
        "Answer in a concise, friendly way suitable for customers evaluating the product.\n"
        "If you genuinely do not know the answer, say you don't know instead of inventing details."
    )
    answer = llm.generate(system_prompt, query, max_tokens=512).strip()
    return {**state, "answer": answer}


def answer_generation_node(state: Dict[str, Any], llm: LLMClient) -> Dict[str, Any]:
    query = state["query"]
    docs: List[Document] = state.get("retrieved_docs") or []
    if not docs:
        # Nothing found, let fallback handle
        return state

    context_chunks = []
    for d in docs:
        src = d.metadata.get("source", "unknown")
        context_chunks.append(f"[Source: {src}]\n{d.page_content}")
    context = "\n\n---\n\n".join(context_chunks)

    system_prompt = (
        "You are a documentation-based assistant.\n"
        "Use ONLY the provided context from manuals to answer the question.\n"
        "If the answer is not in the context, say you don't know."
    )
    user_prompt = f"Question:\n{query}\n\nContext from manuals:\n{context}\n\nAnswer:"
    answer = llm.generate(system_prompt, user_prompt, max_tokens=768).strip()
    return {**state, "answer": answer}


def summarization_node(state: Dict[str, Any], llm: LLMClient) -> Dict[str, Any]:
    answer = state.get("answer", "") or ""
    summarize_flag = bool(state.get("summarize", False))

    if not answer:
        return state

    if not summarize_flag and len(answer) < 600:
        # Short enough, no need to summarize
        return {**state, "final_answer": answer}

    system_prompt = (
        "You are a professional technical summarizer.\n"
        "Rewrite the given answer as a short, clear summary (3-6 sentences) while preserving key details."
    )
    summary = llm.generate(system_prompt, answer, max_tokens=256).strip()
    return {**state, "final_answer": summary}


def fallback_node(state: Dict[str, Any]) -> Dict[str, Any]:
    answer = state.get("final_answer") or state.get("answer") or ""
    if not answer or "i don't know" in answer.lower():
        answer = "I’m escalating this to a human. Our team will review your question and get back to you."
    return {**state, "final_answer": answer}


