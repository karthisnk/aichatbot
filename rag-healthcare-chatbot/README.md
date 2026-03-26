# RAG Healthcare Chatbot

Project scaffold for a healthcare-focused RAG chatbot with a FastAPI backend and React frontend.

## Documentation

Detailed architecture and flow documentation is available in:

- `docs/README.md`
- `docs/01-architecture-overview.md`
- `docs/02-runtime-and-data-flows.md`

## Backend

From `backend/`:

```powershell
pip install -r requirements.txt
python scripts/build_index.py
uvicorn app.main:app --reload
```

Open `http://127.0.0.1:8000/docs`.

The backend now connects to a separate ChromaDB HTTP server on `localhost:8001`
and uses app-scoped collections (for example `kinexushhd` and `nx2meapp`) for retrieval.

Run ChromaDB separately before starting the backend.

## Frontend

The `frontend/chatbot-ui` folder currently contains the minimal React source files only. Create the React app scaffold there if needed, then add the provided source files.


https://sqlitestudio.pl/
SQLiteStudio
 
https://www.python.org/downloads/windows/
Python Releases for Windows | Python.org
The official home of the Python Programming Language
 
Quickstart - Ollama
Quickstart - Ollama
 
https://sourceforge.net/projects/tesseract-ocr-alt/
  
tesseract.zip
 
https://github.com/ravitejapawan/aichatbot
GitHub - ravitejapawan/aichatbot: chatbot for the project nx2me
chatbot for the project nx2me. Contribute to ravitejapawan/aichatbot development by creating an account on GitHub.
 
requirements.txt
 
rag-healthcare-chatbot.zip
 
ollama pull phi3
 
chroma run --host localhost --port 8001
 
ollama run phi3
 
python backend\scripts\run_chunking.py
python backend\scripts\build_index.py
 
cd  backend
 
uvicorn app.main:app --reload
 
cd chatbot-ui
npm install
npm start
 

brew install tesseract
