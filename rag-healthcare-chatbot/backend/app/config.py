MODEL_NAME = "all-MiniLM-L6-v2"
LLM_MODEL = "mistral"

from pathlib import Path
import os


BACKEND_DIR = Path(__file__).resolve().parents[1]
RAW_DATA_DIR = BACKEND_DIR / "data" / "raw"
PROCESSED_DATA_DIR = BACKEND_DIR / "data" / "processed"
CHROMA_HOST = "localhost"
CHROMA_PORT = 8001
SUPPORTED_DOMAINS = (
    "patient",
    "prescription",
    "alerts",
    "troubleshooting",
)

OLLAMA_URL = "http://localhost:11434/api/generate"
LLM_TIMEOUT_SECONDS = 90
LLM_MAX_TOKENS = 220
ROUTER_MODEL = "mistral"
ROUTER_TIMEOUT_SECONDS = 10
OLLAMA_KEEP_ALIVE = "45m"
ROUTER_CACHE_SIZE = 256
ANSWER_CACHE_SIZE = 256
RETRIEVAL_CACHE_SIZE = 512
TOP_K = 5
PROMPT_MAX_CHUNKS = 4
PROMPT_CHUNK_CHAR_LIMIT = 650
TESSERACT_CMD = os.getenv("TESSERACT_CMD", "")
