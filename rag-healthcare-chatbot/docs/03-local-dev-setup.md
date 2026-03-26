# Local Development Setup & Startup Guide

This document covers everything needed to start the full stack — ChromaDB, Ollama LLM, FastAPI backend, and React frontend — after any system restart or on a fresh machine.

---

## TL;DR — Quick Start

```bash
cd rag-healthcare-chatbot
chmod +x start.sh stop.sh  # one-time — make scripts executable
bash start.sh              # starts ChromaDB + Ollama + FastAPI backend + React frontend
```

Then open **http://localhost:3000** in your browser.

---

## Port Map

| Service          | URL                        | Notes                          |
|------------------|----------------------------|--------------------------------|
| FastAPI backend  | http://localhost:8000      | REST + streaming chat API      |
| FastAPI Swagger  | http://localhost:8000/docs | Interactive API explorer       |
| ChromaDB         | http://localhost:8001      | Vector database HTTP server    |
| Ollama           | http://localhost:11434     | Local LLM inference engine     |
| React frontend   | http://localhost:3000      | Chat UI (dev server)           |

---

## Prerequisites (One-Time, Per Machine)

### 1. Homebrew (macOS)

```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

### 2. Python 3.11+

```bash
brew install python@3.11
python3 --version   # should print 3.11.x or higher
```

### 3. Node.js 18+ and npm

```bash
brew install node
node --version      # should print v18.x or higher
npm --version
```

### 4. Ollama (local LLM engine)

```bash
brew install ollama
brew services start ollama          # registers it as a persistent background service
ollama pull qwen2.5                 # downloads ~4.7 GB model (one-time)
```

> **After a system restart:** Ollama starts automatically if registered as a brew service. If not, run `ollama serve &`.

---

## One-Time Backend Setup

Run these steps **once** when first cloning the repository.

### 1. Create the Python virtual environment

```bash
# From the repo root (aichatbot/)
python3 -m venv .venv
source .venv/bin/activate
```

> The virtual environment is created **one level above** `rag-healthcare-chatbot/` so it is shared and not committed. The `start.sh` script resolves it automatically.

### 2. Install Python dependencies

```bash
pip install -r rag-healthcare-chatbot/backend/requirements.txt
```

Key packages installed:

| Package               | Purpose                              |
|-----------------------|--------------------------------------|
| `fastapi`             | REST API framework                   |
| `uvicorn`             | ASGI server                          |
| `chromadb==1.5.5`     | Vector database client + HTTP server |
| `sentence-transformers` | Embedding model (`all-MiniLM-L6-v2`) |
| `requests`            | HTTP calls to Ollama                 |
| `pydantic`            | Request/response validation          |
| `PyMuPDF`             | PDF parsing for ingestion scripts    |
| `Pillow`, `pytesseract` | Image/OCR support for ingestion    |

### 3. Pre-download the embedding model

```bash
source .venv/bin/activate
python - <<'EOF'
from sentence_transformers import SentenceTransformer
SentenceTransformer("all-MiniLM-L6-v2")
print("Embedding model cached.")
EOF
```

This downloads ~90 MB from HuggingFace and caches it in `~/.cache/huggingface/`.

### 4. One-Time Frontend Setup

```bash
cd rag-healthcare-chatbot/frontend/chatbot-ui
npm install
```

---

## One-Time Data Ingestion (Build ChromaDB Collections)

This step populates the ChromaDB vector collections from the pre-chunked JSONL files in `backend/data/processed/`. Only needed once (or after adding new documents).

```bash
# Make sure ChromaDB is running first:
source .venv/bin/activate
chroma run --path /tmp/chroma-data --port 8001 &

# Then ingest:
cd rag-healthcare-chatbot/backend
python scripts/build_index.py
```

Expected output:
```
Ingesting kinexushhd/alerts_chunks.jsonl ... done
Ingesting kinexushhd/patient_chunks.jsonl ... done
...
Collections created: kinexushhd, nx2meapp
```

> The `start.sh` script automatically skips re-ingestion if the collections already exist.

---

## Daily Startup (After System Restart)

You have two options:

### Option A — Single Script (Recommended)

```bash
cd rag-healthcare-chatbot
bash start.sh
```

The script:
1. Locates the `.venv` in the parent directory
2. Starts ChromaDB on port 8001 (skips if already running)
3. Ensures Ollama is serving on port 11434 (skips if already running)
4. Starts the FastAPI backend on port 8000
5. Installs frontend dependencies if `node_modules` is missing
6. Starts the React dev server on port 3000
7. Prints all URLs once everything is up

Logs are written to `logs/` inside the project directory.

To start **backend only** (no frontend):

```bash
bash start.sh --backend-only
```

### Option B — Manual Steps

Open four terminal tabs:

**Tab 1 — ChromaDB**
```bash
source .venv/bin/activate
chroma run --path /tmp/chroma-data --port 8001
```

**Tab 2 — Ollama** (only if not a brew service)
```bash
ollama serve
```

**Tab 3 — FastAPI backend**
```bash
source .venv/bin/activate
cd rag-healthcare-chatbot/backend
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

**Tab 4 — React frontend**
```bash
cd rag-healthcare-chatbot/frontend/chatbot-ui
npm start
```

---

## Verifying Everything Is Running

```bash
# ChromaDB heartbeat
curl -s http://localhost:8001/api/v2/heartbeat

# ChromaDB collections (should show kinexushhd and nx2meapp)
curl -s http://localhost:8001/api/v2/collections | python3 -m json.tool

# Ollama
curl -s http://localhost:11434/api/tags | python3 -m json.tool

# FastAPI health
curl -s http://localhost:8000/health

# Test a chat query
curl -s -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"question":"What is a therapy gap?","app":"auto","history":[]}' \
  | python3 -m json.tool
```

---

## Configuration Reference

All backend settings are in `backend/app/config.py`:

| Variable              | Default                          | Description                            |
|-----------------------|----------------------------------|----------------------------------------|
| `MODEL_NAME`          | `all-MiniLM-L6-v2`               | Sentence embedding model               |
| `LLM_MODEL`           | `qwen2.5`                        | Ollama LLM model for answers           |
| `ROUTER_MODEL`        | `qwen2.5`                        | Ollama model used for app routing      |
| `CHROMA_HOST`         | `localhost`                      | ChromaDB hostname                      |
| `CHROMA_PORT`         | `8001`                           | ChromaDB port                          |
| `OLLAMA_URL`          | `http://localhost:11434/api/generate` | Ollama generate endpoint          |
| `TOP_K`               | `2`                              | Number of chunks retrieved per query   |
| `LLM_TIMEOUT_SECONDS` | `90`                             | Timeout for LLM responses              |

---

## Troubleshooting

### `ModuleNotFoundError: No module named 'app'`
Uvicorn is being run from the wrong directory. Always run it from `backend/`:
```bash
cd rag-healthcare-chatbot/backend
uvicorn app.main:app --port 8000
```
Or use the `--app-dir` flag:
```bash
uvicorn app.main:app --app-dir rag-healthcare-chatbot/backend --port 8000
```

### ChromaDB collections missing after restart
ChromaDB uses `/tmp/chroma-data` as storage path. `/tmp` is cleared on macOS reboots. Re-run ingestion:
```bash
bash start.sh  # handles this automatically, or:
cd rag-healthcare-chatbot/backend && python scripts/build_index.py
```

> **Tip:** To persist collections across reboots, change the storage path to something under your home directory, e.g. `~/chroma-data`, in `start.sh`.

### Ollama model not found
```bash
ollama list          # see what is downloaded
ollama pull qwen2.5  # re-download if missing
```

### Port already in use
```bash
lsof -ti :8000 | xargs kill -9   # free backend port
lsof -ti :8001 | xargs kill -9   # free ChromaDB port
lsof -ti :3000 | xargs kill -9   # free frontend port
```

### Frontend shows blank page or API errors
- Confirm the backend is running on port 8000
- Check the browser console for CORS errors
- CORS is pre-configured in `backend/app/main.py` to allow `http://localhost:3000`

---

## Stopping Everything

```bash
bash stop.sh        # gracefully stops all services started by start.sh
```

Or manually:
```bash
# Kill by port
lsof -ti :8000 | xargs kill    # FastAPI
lsof -ti :8001 | xargs kill    # ChromaDB
lsof -ti :3000 | xargs kill    # React frontend
# Ollama (if not a brew service)
pkill ollama
```
