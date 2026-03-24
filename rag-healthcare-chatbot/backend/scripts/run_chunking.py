import argparse
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.config import PROCESSED_DATA_DIR, RAW_DATA_DIR
from app.services.chroma_ingestor import ChromaIngestor
from app.services.document_pipeline import DocumentProcessingPipeline


def _print_summary(processed_documents):
    print("\nChunking Summary")
    print("-" * 60)

    total_chunks = 0
    for item in processed_documents:
        chunks_by_domain = item.get("chunks_by_domain") or {}
        app_total = sum(len(chunks) for chunks in chunks_by_domain.values())
        total_chunks += app_total

        print(f"App: {item.get('app_name')}")
        print(f"Source: {item.get('source')}")
        print(f"Output: {item.get('output_dir')}")
        print(f"OCR enabled: {'yes' if item.get('ocr_enabled') else 'no'}")
        print(f"Total chunks: {app_total}")

        for domain, chunks in chunks_by_domain.items():
            file_path = item.get("files", {}).get(domain, "")
            print(f"  - {domain}: {len(chunks)} -> {file_path}")

        print("-" * 60)

    print(f"Grand total chunks: {total_chunks}")


def main():
    parser = argparse.ArgumentParser(
        description="Run the offline PDF chunking pipeline and optionally ingest into ChromaDB."
    )
    parser.add_argument(
        "--ingest-chroma",
        action="store_true",
        help="Also ingest the generated chunks into ChromaDB.",
    )
    args = parser.parse_args()

    print("Running offline document chunking...")
    print(f"Raw data directory: {RAW_DATA_DIR}")

    pipeline = DocumentProcessingPipeline()
    processed_documents = pipeline.process_directory(RAW_DATA_DIR)
    _print_summary(processed_documents)

    if not args.ingest_chroma:
        print("\nChunking completed. Chroma ingestion was skipped.")
        print("To ingest later, run: python backend\\scripts\\run_chunking.py --ingest-chroma")
        return

    print("\nStarting ChromaDB ingestion...")
    ingestor = ChromaIngestor()
    collections = ingestor.ingest_processed_directory(PROCESSED_DATA_DIR)
    print("ChromaDB ingestion completed successfully.")
    print("Collections created:")
    for collection in collections:
        print(f"  - {collection}")


if __name__ == "__main__":
    main()
