import chromadb
from chromadb.config import Settings

from app.config import CHROMA_HOST, CHROMA_PORT


def get_chroma_client():
    try:
        return chromadb.HttpClient(
            host=CHROMA_HOST,
            port=CHROMA_PORT,
            settings=Settings(anonymized_telemetry=False),
        )
    except Exception as exc:
        raise RuntimeError(
            f"Failed to connect to ChromaDB at {CHROMA_HOST}:{CHROMA_PORT}."
        ) from exc


def persist_client(client):
    persist = getattr(client, "persist", None)
    if callable(persist):
        persist()
