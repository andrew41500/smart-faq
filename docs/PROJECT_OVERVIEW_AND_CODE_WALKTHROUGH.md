## Smart Multi-Agent FAQ & Knowledge Assistant – Project Overview & Code Walkthrough

This document is written for **interview prep**.  
You can use it to clearly explain:

- What the project does.
- How the architecture fits together.
- What each important file does.
- How the LangGraph workflow and RAG pieces work.

---

## 1. High-Level Concept

**What is this project?**

- A **web-based AI assistant** that answers FAQs about a fictional SaaS product called **SmartSupport Cloud**.
- It uses **multiple AI “agents”** orchestrated by **LangGraph**:
  - **Intent Classification Agent** – decides if a question is a simple FAQ or requires deep documentation.
  - **Document Retrieval Agent** – searches PDFs/DOCX using **ChromaDB** (vector database).
  - **Answer Generation Agent** – uses an LLM to answer based on retrieved docs (RAG).
  - **General QA Agent** – uses an LLM to answer high-level questions without docs.
  - **Summarization Agent** – rewrites long answers into shorter summaries.
  - **Fallback Agent** – if nothing is confident, it says: _“I’m escalating this to a human.”_
- The frontend is a **simple chat UI** (HTML/CSS/JS).
- The backend is **Flask** with a **LangGraph workflow** and **LangChain + ChromaDB** for RAG.
- The entire project is **Dockerized** and has **CI/CD via GitHub Actions** plus instructions to deploy to **Railway**.

In interviews, you can describe this as:

> “I built a multi-agent FAQ assistant that uses LangGraph to orchestrate LLM agents over a RAG stack (ChromaDB + embeddings). It exposes a simple Flask-based web UI and can be deployed to Railway with CI/CD.”

---

## 2. Architecture and Data Flow

### 2.1 End-to-End Flow (Simple Story)

1. User opens the web page.
2. User types a question (e.g., “Explain the onboarding steps from the manual.”).
3. The frontend sends the question to the Flask backend (`/api/chat`).
4. The backend **runs the LangGraph workflow**:
   - **Intent node**: decide GENERAL vs DOCUMENT.
   - If DOCUMENT → **retrieve docs from Chroma** → **answer from docs**.
   - If GENERAL → **answer with general FAQ prompt**.
   - Pass the answer through **Summarization node**.
   - Pass through **Fallback node** to handle “I don’t know” cases.
5. The final answer and some metadata (intent + sources) are returned to the frontend.
6. The frontend displays the response in a chat bubble.

### 2.2 ASCII Diagram

```text
[User Query]
      |
      v
Intent Classification (GENERAL vs DOCUMENT)
      |
      +------------------------------+
      | DOCUMENT                     | GENERAL
      v                              v
Document Retrieval (ChromaDB)   General QA Agent
      |                              |
      +--------------+---------------+
                     v
           Answer Generation (doc-based)
                     |
                     v
             Summarization (optional)
                     |
                     v
           Fallback (human escalation)
                     |
                     v
               Final Answer
```

You can show this during the interview to prove you understand the workflow.

---

## 3. Backend – Flask + LangGraph + RAG

### 3.1 `backend/app.py` – Flask Entry Point

**What it does:**

- Creates the Flask app.
- Initializes:
  - `LLMClient` (the abstraction around Gemini / Hugging Face).
  - `ChromaDB retriever`.
  - Compiled **LangGraph** workflow.
- Exposes:
  - `GET /` → serves the HTML page.
  - `POST /api/chat` → runs the LangGraph workflow with the user query.

**Key ideas:**

- The app follows a **“single workflow per request”** pattern.
- The API returns:
  - `answer`: the text returned to the user.
  - `intent`: GENERAL or DOCUMENT.
  - `source_docs`: short snippets and metadata for debugging / UI hints.

**Example to explain:**

> “When the frontend calls `/api/chat`, `app.py` builds an initial state containing the user’s query and whether summarization is requested. It then invokes the compiled LangGraph workflow, waits for the final state, pulls out the `final_answer`, and returns it as JSON.”

---

### 3.2 `backend/llm.py` – LLM Abstraction Layer

**Purpose:**

- Provide a **single interface** for calling an LLM, while allowing different providers underneath.
- Keeps the rest of the code independent from provider-specific details.

**Supported providers:**

- `LLM_PROVIDER=google`:
  - Uses `google-generativeai` (e.g., `gemini-1.5-flash`).
  - Requires `GOOGLE_API_KEY`.
- `LLM_PROVIDER=huggingface`:
  - Uses `huggingface-hub`’s `InferenceClient`.
  - Requires `HUGGINGFACE_API_TOKEN`.

**Key method:**

- `generate(system_prompt: str, user_prompt: str, max_tokens: int = 512) -> str`
  - You pass a `system_prompt` describing the role (“You are a summarization agent ...”).
  - You pass a `user_prompt` with the actual question/context.
  - It returns the model’s answer.

**Example explanation:**

> “I use one general-purpose LLM and just vary the prompts per node. The `LLMClient` hides whether I’m using Gemini or a Hugging Face model, which makes swapping providers easy.”

---

### 3.3 `backend/graph/workflow.py` – LangGraph StateGraph

**What it defines:**

- `AssistantState`: a typed dictionary representing the state that flows through nodes:
  - `query`: the user’s question.
  - `intent`: `GENERAL` or `DOCUMENT`.
  - `retrieved_docs`: documents from Chroma (for doc-based questions).
  - `answer`: intermediate answer before summarization/fallback.
  - `final_answer`: final answer after summarization and fallback.
  - `summarize`: a boolean flag from the frontend.

- `build_workflow(llm, retriever)`:
  - Creates a `StateGraph`.
  - Registers nodes:
    - `"intent"`
    - `"doc_retrieval"`
    - `"general_qa"`
    - `"answer_generation"`
    - `"summarization"`
    - `"fallback"`
  - Sets `"intent"` as the **entry point**.
  - Adds a **conditional edge**:
    - If state.intent == `DOCUMENT` → `"doc_retrieval"`.
    - Else → `"general_qa"`.
  - Wires edges:
    - `doc_retrieval → answer_generation`.
    - `general_qa → summarization`.
    - `answer_generation → summarization`.
    - `summarization → fallback → END`.

**How to explain:**

> “The workflow is a LangGraph `StateGraph`. Each node is a Python function that takes the current state, updates some fields, and returns a new state. The graph uses conditionals to route between nodes based on `intent`, and eventually all paths converge into `summarization` and `fallback`.”

---

### 3.4 `backend/graph/nodes.py` – Node Implementations

Each function here is a **node** in the LangGraph.

1. **`intent_classification_node`**
   - Input: `state["query"]`.
   - Calls LLM with a prompt:
     - “Classify as GENERAL or DOCUMENT. Respond with one word.”
   - Cleans the model’s output and sets `state["intent"]`.

   **Example:**

   - Question: _“Explain the onboarding steps from the manual.”_ → likely `DOCUMENT`.
   - Question: _“What is SmartSupport Cloud?”_ → likely `GENERAL`.

2. **`document_retrieval_node`**
   - Calls `retriever.get_relevant_documents(query)` from Chroma.
   - Stores result in `state["retrieved_docs"]`.

3. **`general_qa_node`**
   - Uses a **general FAQ prompt** that describes SmartSupport Cloud.
   - Good for high-level marketing / product questions.

4. **`answer_generation_node`**
   - Builds a big **context** from `retrieved_docs` (each chunk includes a source).
   - Prompts the LLM:
     - “Use ONLY the provided context. If answer is not there, say you don’t know.”
   - Stores the result in `state["answer"]`.

5. **`summarization_node`**
   - If `state["summarize"]` is true or answer is long, calls LLM:
     - “Rewrite answer into a 3–6 sentence summary.”
   - Stores final text in `state["final_answer"]`.

6. **`fallback_node`**
   - Checks `final_answer` or `answer`.
   - If empty or contains “I don’t know”:
     - Overrides with: `“I’m escalating this to a human. Our team will review your question and get back to you.”`

**Interview soundbite:**

> “Each node is intentionally small and self-contained, which makes it very easy to add new agents later, like a translation node or a sentiment node. I just define another function here and wire it into the graph.”

---

### 3.5 RAG Components – `backend/rag/*`

#### a) `backend/rag/parsers.py`

- `parse_pdf(path)`: uses **PyPDF2** to read each page and extract text.
- `parse_docx(path)`: uses **python-docx** to read each paragraph.
- Both functions return lists of text chunks.

#### b) `backend/rag/retriever.py`

- `CHROMA_DIR`: folder where ChromaDB stores its data (configurable via env).
- `_get_embeddings()`: creates a `HuggingFaceEmbeddings` object:
  - by default `"sentence-transformers/all-MiniLM-L6-v2"`.
- `get_vectorstore()`: opens or creates a Chroma instance.
- `get_retriever()`: returns a retriever object (`.as_retriever(k=4)`).
- `add_documents_to_chroma(docs)`: adds `langchain` `Document` objects and persists the DB.

#### c) `backend/rag/ingest.py`

- `SAMPLE_DOCS_DIR`: where the sample docs live (default `./sample_docs`).
- `load_documents()`:
  - Walks the directory.
  - For each `.pdf` → uses `parse_pdf`.
  - For each `.doc`/`.docx` → uses `parse_docx`.
  - Wraps text chunks in `Document` objects with metadata (source path, page/chunk number).
- `ingest()`:
  - Calls `load_documents()`, then `add_documents_to_chroma`.
  - This is what you run once to populate Chroma.

**Example explanation:**

> “I have a small ingestion pipeline that reads PDFs and DOCX files, chunks them, and adds them into ChromaDB with metadata. At query time, LangGraph calls the retriever to pull the most relevant chunks for document-based questions.”

---

### 3.6 `backend/sample_docs_generator.py` – Sample Data

**What it does:**

- Generates **one DOCX** and **one PDF** with realistic-looking SmartSupport Cloud content:
  - `smartsupport_faq.docx`: Q&A style FAQs.
  - `smartsupport_manual.pdf`: onboarding steps and security details.
- Uses:
  - `python-docx` to create the DOCX.
  - `reportlab` to create the PDF.

This makes the project completely self-contained:

- You don’t have to manually create documents.
- Interviewers can see RAG working with real files.

---

## 4. Frontend – HTML / CSS / JS

### 4.1 `frontend/templates/index.html`

**Purpose:**

- Basic but polished chat UI with:
  - Chat window (`#chat-window`).
  - Input form (`#chat-form`).
  - Summarize toggle.
  - Sample queries list.

**Integration:**

- Uses `{{ url_for('static', ...) }}` to reference CSS and JS.
- On load, it fetches `app.js`, which attaches all event handlers.

### 4.2 `frontend/static/css/style.css`

**Design goals:**

- Modern, dark theme.
- Chat bubbles for user vs assistant.
- Responsive layout.

You can mention:

> “The UI is intentionally simple: no frameworks, just clean HTML/CSS so the focus is on the AI orchestration and backend design.”

### 4.3 `frontend/static/js/app.js`

**Main responsibilities:**

- Handle the chat form submit.
- Send requests to `/api/chat`.
- Render responses to the chat window.

**Key functions:**

- `appendMessage(role, text, meta)`: creates chat bubbles in the DOM.
- `sendMessage(text)`:
  - Sends POST to `/api/chat` with JSON:
    - `{ "message": text, "summarize": <bool> }`
  - Receives JSON:
    - `answer`, `intent`, `source_docs`.
  - Renders the answer and metadata (intent, source files).
- Binds click handlers for `.sample-query` elements to pre-fill the input.

**Example explanation:**

> “The frontend is deliberately lightweight. It posts the user’s message as JSON, displays the assistant’s response, and shows which intent path and documents were used. This gives good visibility into how the multi-agent workflow behaves.”

---

## 5. Infra – Docker, CI/CD, Tests

### 5.1 `requirements.txt`

- Central list of dependencies, including:
  - `flask`, `flask-cors` for the web server.
  - `langgraph`, `langchain`, `langchain-community` for workflow and RAG.
  - `chromadb`, `sentence-transformers` for vector search.
  - `PyPDF2`, `python-docx`, `reportlab` for document handling.
  - `google-generativeai`, `huggingface-hub` for LLMs.
  - `gunicorn`, `pytest`, `flake8` for serving and CI.

You can say:

> “I pinned explicit version ranges for stability and reproducibility in CI and on Railway.”

### 5.2 `Dockerfile`

**What it does:**

- Uses `python:3.11-slim` as base.
- Installs build essentials (for some Python packages).
- Installs Python dependencies from `requirements.txt`.
- Copies project code into `/app`.
- Ensures `/data/chroma_db` exists for Chroma.
- Exposes port `8000`.
- Starts the app via `gunicorn backend.app:create_app()`.

**Why this matters in interviews:**

> “The Docker image is production-oriented (gunicorn, not Flask dev server). It’s compatible with Railway’s container runtime and supports persistent Chroma storage via a volume.”

### 5.3 `docker-compose.yml`

- Defines a single service: `app`.
- Binds host port `8000` to container `8000`.
- Maps a named volume `chroma_data` to `/data/chroma_db`.
- Sets some environment variables (you still need to set API keys).

### 5.4 `.github/workflows/ci.yml` – CI & Deployment

- **build-test job:**
  - Runs on every push/PR to `main` or `master`.
  - Installs dependencies.
  - Runs `flake8 backend`.
  - Runs `pytest`.

- **deploy-railway job:**
  - Runs only on `main` after `build-test` succeeds.
  - Installs Railway CLI.
  - Calls `railway up --service smart-faq-app --detach`.
  - Uses `RAILWAY_TOKEN` secret configured in GitHub.

You can explain:

> “I wired up a simple CI pipeline to catch syntax issues and basic regressions before deployment, and then a second job handles automated deployment to Railway when changes land on the main branch.”

### 5.5 `tests/test_smoke.py`

- Minimal **smoke test**:
  - Sets environment for Hugging Face provider (with a dummy token).
  - Calls `create_app()` from `backend.app`.
  - Asserts the app is created successfully.

Reasoning:

> “This ensures the application can at least start in CI without hitting real LLM endpoints.”

---

## 6. How to Use the Project – Step-by-Step

This is a **step-by-step script** you can follow when you first set it up or demo it live.

### 6.1 Local Setup (Windows, PowerShell)

1. **Clone the repo**

```powershell
git clone <your-repo-url> smart-faq
cd smart-faq
```

2. **Create a virtual environment and install requirements**

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

3. **Set environment variables**

- For **Gemini**:

```powershell
$env:LLM_PROVIDER="google"
$env:GOOGLE_API_KEY="your-google-api-key"
```

- Or for **Hugging Face**:

```powershell
$env:LLM_PROVIDER="huggingface"
$env:HUGGINGFACE_API_TOKEN="your-hf-token"
```

4. **Generate sample documents**

```powershell
python -m backend.sample_docs_generator
```

This creates `sample_docs/smartsupport_faq.docx` and `sample_docs/smartsupport_manual.pdf`.

5. **Ingest documents into ChromaDB**

```powershell
python -m backend.rag.ingest
```

You should see log messages like:

- “Ingesting X chunks into ChromaDB...”
- “Ingestion complete.”

6. **Run the Flask app**

```powershell
python backend/app.py
```

You should see Flask’s dev server running on port 8000.

7. **Open the UI**

- Go to `http://localhost:8000` in your browser.
- You’ll see the chat interface and a welcome message.

8. **Try sample questions**

- General:
  - “What is SmartSupport Cloud and who is it for?”
- Document-based:
  - “Explain the onboarding steps from the manual.”
  - “How is my data stored and secured?”
- Fallback:
  - “What is your refund policy for on-premise appliances?”
- Toggle “Summarize long answers” and ask something like:
  - “Explain all the features of SmartSupport Cloud in detail.”

This will walk through all major workflow paths in a demo.

---

## 7. How to Explain this Project in an Interview

Here is a short **storyline** you can follow:

1. **Problem**
   - “Companies often have a lot of FAQs and product manuals. I wanted to build a demo that shows how to use multi-agent LLM orchestration with RAG to answer questions about such a product.”

2. **Solution Overview**
   - “I built a Smart FAQ & Knowledge Assistant using Flask, LangGraph, and ChromaDB. The assistant routes questions through different agents: intent classification, document retrieval, answer generation, summarization, and fallback.”

3. **Architecture**
   - Point to the LangGraph diagram and the `AssistantState`.
   - Mention that all nodes share a single LLM client but use different prompts.

4. **RAG Stack**
   - “Documents are stored in ChromaDB. I parse PDFs and DOCX files, generate embeddings with sentence-transformers, and then retrieve relevant chunks for document-heavy questions.”

5. **Deployment & DevOps**
   - “I containerized the app with Docker, run it with gunicorn, and set up a GitHub Actions pipeline that runs lint/tests and can deploy to Railway using the Railway CLI. ChromaDB is persisted via a mounted volume.”

6. **Extensibility**
   - “Because the workflow is defined as a graph of nodes, adding new agents like translation or sentiment analysis is as simple as writing another node function and wiring it into the graph.”

If you want, you can print this file and keep it as a **cheat sheet** while practicing.


