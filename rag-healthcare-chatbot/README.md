# RAG Healthcare Chatbot

Project scaffold for a healthcare-focused RAG chatbot with a FastAPI backend and React frontend.

## Backend

From `backend/`:

```powershell
pip install -r requirements.txt
python scripts/build_index.py
uvicorn app.main:app --reload
```

Open `http://127.0.0.1:8000/docs`.

The backend now connects to a separate ChromaDB HTTP server on `localhost:8001`
and uses the `healthcare` collection for retrieval.

Run ChromaDB separately before starting the backend.

## Frontend

The `frontend/chatbot-ui` folder currently contains the minimal React source files only. Create the React app scaffold there if needed, then add the provided source files.
