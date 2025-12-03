## Smart Multi-Agent FAQ & Knowledge Assistant – Usage & Demo Script

This markdown focuses on **how to run, use, and demo** the project step by step.

---

## 1. Local Usage – Step by Step

These instructions assume **Windows + PowerShell** (adjust paths for other OSes).

### 1.1 Clone and Install

```powershell
git clone <your-repo-url> smart-faq
cd smart-faq

python -m venv .venv
.\.venv\Scripts\Activate.ps1

pip install -r requirements.txt
```

### 1.2 Configure Environment Variables

Choose one LLM provider. For interviews, **Google Gemini** is a nice choice.

#### Option A – Google Gemini

```powershell
$env:LLM_PROVIDER="google"
$env:GOOGLE_API_KEY="your-google-api-key"
```

#### Option B – Hugging Face

```powershell
$env:LLM_PROVIDER="huggingface"
$env:HUGGINGFACE_API_TOKEN="your-hf-token"
```

You can verify by printing:

```powershell
echo $env:LLM_PROVIDER
```

### 1.3 Generate Sample Docs

```powershell
python -m backend.sample_docs_generator
```

This will create:

- `sample_docs/smartsupport_faq.docx`
- `sample_docs/smartsupport_manual.pdf`

These are the documents the RAG system will use.

### 1.4 Ingest Docs into ChromaDB

```powershell
python -m backend.rag.ingest
```

What happens here:

- The script scans the `sample_docs` folder.
- Parses PDF and DOCX into text chunks.
- Embeds them using `sentence-transformers/all-MiniLM-L6-v2`.
- Saves embeddings + metadata into a ChromaDB folder (default `./chroma_db`).

### 1.5 Run the App (Dev Mode)

```powershell
python backend/app.py
```

You should see Flask start, listening on `0.0.0.0:8000`.

### 1.6 Open the Web UI

- Visit: `http://localhost:8000`
- Try asking:
  - “What is SmartSupport Cloud and who is it for?”
  - “Explain the onboarding steps from the manual.”
  - “What is your refund policy for on-premise appliances?”
- Toggle **“Summarize long answers”** and ask a long question to see summarization kick in.

---

## 2. Docker Usage

### 2.1 Build Image

```bash
docker build -t smart-faq .
```

### 2.2 Run Container

On Windows PowerShell:

```powershell
docker run -p 8000:8000 `
  -e LLM_PROVIDER=google `
  -e GOOGLE_API_KEY=your-google-api-key `
  -v ${PWD}/chroma_data:/data/chroma_db `
  smart-faq
```

This:

- Exposes the app on `localhost:8000`.
- Mounts `chroma_data` from your host to `/data/chroma_db` in the container.

### 2.3 Ingest Inside Container

If you want ingestion to run **inside** the container (using container paths):

```powershell
docker exec -it <container-id-or-name> bash -lc "python -m backend.sample_docs_generator && python -m backend.rag.ingest"
```

Now the container has:

- Sample docs in `/app/sample_docs`.
- Chroma vector store in `/data/chroma_db` (mapped to `chroma_data` on your host).

---

## 3. Railway Deployment – Step by Step

### 3.1 Prepare GitHub Repo

1. Commit all code.
2. Push to GitHub:

```bash
git remote add origin <your-github-repo-url>
git push -u origin main
```

### 3.2 Create Railway Project

1. Go to the Railway dashboard.
2. Click **New Project**.
3. Choose **Deploy from GitHub**.
4. Select your repo.

Railway will automatically:

- Detect your `Dockerfile`.
- Build and run the container.

### 3.3 Configure Environment Variables on Railway

In the Railway service settings, add variables:

- `LLM_PROVIDER=google` (or `huggingface`).
- `GOOGLE_API_KEY=<your-key>` or `HUGGINGFACE_API_TOKEN=<your-token>`.
- `CHROMA_DIR=/data/chroma_db`
- `SAMPLE_DOCS_DIR=/app/sample_docs`

### 3.4 Configure a Volume for Chroma

1. In the same Railway service, add a **Volume**:
   - Mount path: `/data`
2. Because `CHROMA_DIR` is `/data/chroma_db`, Chroma data will persist across deploys.

### 3.5 Seed the Vector Store on Railway

Use Railway CLI (locally) or the web console to run:

```bash
railway run "python -m backend.sample_docs_generator && python -m backend.rag.ingest"
```

This will:

- Generate sample docs in `/app/sample_docs`.
- Ingest them into Chroma at `/data/chroma_db`.

### 3.6 Confirm Deployment

- Railway gives you a public URL (e.g., `https://your-app.up.railway.app`).
- Visit it and make sure:
  - The frontend loads.
  - Queries work.

You can then add this URL to the README in the **Deployment URL** section.

---

## 4. CI/CD – How It Works in Practice

### 4.1 GitHub Actions Flow

File: `.github/workflows/ci.yml`

On each push to `main` or `master`:

1. **build-test job**:
   - Check out the code.
   - Set up Python 3.11.
   - Install dependencies.
   - Run:
     - `flake8 backend`
     - `pytest`
2. If `build-test` passes and branch is `main`:
   - **deploy-railway job**:
     - Installs Railway CLI.
     - Runs:

       ```bash
       railway up --service smart-faq-app --detach
       ```

### 4.2 Setting Secrets

In GitHub:

1. Go to **Settings → Secrets and variables → Actions**.
2. Add:
   - `RAILWAY_TOKEN` = token generated from your Railway account.

Now, every push to `main` can automatically:

- Run tests.
- Deploy the latest image to Railway.

---

## 5. 2-Minute Demo Script (Interview-Friendly)

You can literally read or paraphrase this during an interview demo.

### 5.1 Intro (20–30 seconds)

> “This is a Smart Multi-Agent FAQ & Knowledge Assistant I built. It answers questions about a fictional SaaS product called SmartSupport Cloud. Under the hood, it uses LangGraph to orchestrate multiple LLM-based agents — intent classification, document retrieval, answer generation, summarization, and fallback — and uses ChromaDB for vector search over PDFs and DOCX manuals.”

### 5.2 Architecture (30–40 seconds)

Open `docs/PROJECT_OVERVIEW_AND_CODE_WALKTHROUGH.md` (or the README diagram) and say:

> “Every query first goes through an intent classification node that decides whether it’s a general FAQ or requires documentation. If it’s document-based, I use a LangChain retriever over ChromaDB to pull relevant chunks from PDFs/DOCX. Then another node uses an LLM to answer based strictly on that context. Both paths then go through a summarization node, and finally a fallback node that escalates to a human if the answer is unknown.”

Mention:

> “All those nodes are defined as separate functions in `backend/graph/nodes.py` and wired together as a LangGraph `StateGraph` in `backend/graph/workflow.py`.”

### 5.3 Live Queries (40–60 seconds)

In the browser:

1. Ask a **general** question:
   - “What is SmartSupport Cloud and who is it for?”
   - Explain: intent is GENERAL, answer comes from general FAQ prompt.
2. Ask a **document-based** question:
   - “Explain the onboarding steps from the manual.”
   - Explain: intent is DOCUMENT, retrieval node fetches manual chunks from Chroma, answer mentions onboarding steps.
3. Ask a **fallback** question:
   - “What is your refund policy for on-premise appliances?”
   - Explain: docs don’t contain this, so after summarization, fallback replaces answer with “I’m escalating this to a human.”
4. Toggle **Summarize long answers** and show a more compact response to a long query.

### 5.4 Production & DevOps (20–30 seconds)

> “The app runs with Flask in development and with gunicorn in production. I built a Docker image that Railway can run directly, and I wired up a GitHub Actions pipeline that runs linting and tests before calling the Railway CLI to deploy. ChromaDB is backed by a persistent volume, so document embeddings survive redeploys. The LLM access is abstracted so I can switch between Gemini and Hugging Face by flipping environment variables.”

### 5.5 Extensibility (10–20 seconds)

> “If we wanted to add a translation or sentiment agent, we’d just define another node in `nodes.py` and wire it into the graph in `workflow.py`. The shared `AssistantState` and `LLMClient` make that very straightforward.”

---

Use this file to practice **how to run** and **how to demo**.  
Use `PROJECT_OVERVIEW_AND_CODE_WALKTHROUGH.md` to practice **explaining the internals**.+


