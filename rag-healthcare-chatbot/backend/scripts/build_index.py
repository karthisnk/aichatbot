import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.config import PROCESSED_DATA_DIR
from app.services.chroma_ingestor import ChromaIngestor

ingestor = ChromaIngestor()
collections = ingestor.ingest_processed_directory(PROCESSED_DATA_DIR)

print("ChromaDB ingestion completed successfully")
print("Collections created:")
for collection in collections:
    print(f"- {collection}")
