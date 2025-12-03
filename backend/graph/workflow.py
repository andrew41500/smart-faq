from typing import Any, Dict, TypedDict, List

from langgraph.graph import StateGraph, END
from langchain_core.documents import Document

from backend.llm import LLMClient
from backend.graph.nodes import (
    intent_classification_node,
    document_retrieval_node,
    general_qa_node,
    answer_generation_node,
    summarization_node,
    fallback_node,
)


class AssistantState(TypedDict, total=False):
    query: str
    intent: str
    retrieved_docs: List[Document]
    answer: str
    final_answer: str
    summarize: bool


def build_workflow(llm: LLMClient, retriever):
    """
    Build the LangGraph workflow for the multi-agent assistant.
    """

    def intent_node(state: Dict[str, Any]) -> Dict[str, Any]:
        return intent_classification_node(state, llm)

    def doc_retrieval_node_wrapped(state: Dict[str, Any]) -> Dict[str, Any]:
        return document_retrieval_node(state, retriever)

    def general_qa_node_wrapped(state: Dict[str, Any]) -> Dict[str, Any]:
        return general_qa_node(state, llm)

    def answer_generation_node_wrapped(state: Dict[str, Any]) -> Dict[str, Any]:
        return answer_generation_node(state, llm)

    def summarization_node_wrapped(state: Dict[str, Any]) -> Dict[str, Any]:
        return summarization_node(state, llm)

    graph = StateGraph(AssistantState)

    graph.add_node("intent_router", intent_node)
    graph.add_node("doc_retrieval", doc_retrieval_node_wrapped)
    graph.add_node("general_qa", general_qa_node_wrapped)
    graph.add_node("answer_generation", answer_generation_node_wrapped)
    graph.add_node("summarization", summarization_node_wrapped)
    graph.add_node("fallback", fallback_node)

    graph.set_entry_point("intent_router")

    def route_after_intent(state: AssistantState) -> str:
        intent = (state.get("intent") or "").upper()
        if intent == "DOCUMENT":
            return "doc_retrieval"
        return "general_qa"

    graph.add_conditional_edges(
        "intent_router",
        route_after_intent,
        {
            "doc_retrieval": "doc_retrieval",
            "general_qa": "general_qa",
        },
    )

    # Document path: retrieval -> answer generation
    graph.add_edge("doc_retrieval", "answer_generation")

    # Both answer generation paths go to summarization
    graph.add_edge("general_qa", "summarization")
    graph.add_edge("answer_generation", "summarization")

    # Fallback is always last
    graph.add_edge("summarization", "fallback")
    graph.add_edge("fallback", END)

    return graph.compile()


