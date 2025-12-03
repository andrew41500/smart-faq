from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
from dotenv import load_dotenv
import os
import sys
from pathlib import Path

# Load environment variables from .env file (project root) if present
load_dotenv()

# Ensure project root is importable when running `python backend/app.py`
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.graph.workflow import build_workflow
from backend.rag.retriever import get_retriever
from backend.llm import LLMClient


def create_app() -> Flask:
    app = Flask(__name__, template_folder="../frontend/templates", static_folder="../frontend/static")
    CORS(app)

    # Initialize shared components
    llm_client = LLMClient()
    retriever = get_retriever()
    workflow = build_workflow(llm_client, retriever)

    @app.route("/")
    def index():
        return render_template("index.html")

    @app.route("/api/chat", methods=["POST"])
    def chat():
        data = request.get_json(force=True)
        query = data.get("message", "").strip()
        summarize = bool(data.get("summarize", False))

        if not query:
            return jsonify({"error": "Message cannot be empty."}), 400

        initial_state = {
            "query": query,
            "summarize": summarize,
        }

        try:
            final_state = workflow.invoke(initial_state)
            return jsonify(
                {
                    "answer": final_state.get("final_answer") or final_state.get("answer"),
                    "intent": final_state.get("intent"),
                    "source_docs": [
                        {"id": d.metadata.get("source"), "content": d.page_content[:400]}
                        for d in final_state.get("retrieved_docs", []) or []
                    ],
                }
            )
        except Exception as exc:
            # In production you'd log this properly
            return jsonify({"error": str(exc)}), 500

    return app


if __name__ == "__main__":
    # For local dev only; in production use gunicorn
    app = create_app()
    port = int(os.environ.get("PORT", 8000))
    app.run(host="0.0.0.0", port=port, debug=True)


