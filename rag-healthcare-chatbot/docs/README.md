# RAG Healthcare Chatbot Documentation

This docs folder explains how the repository is structured and how data moves through the system.

## Documents

- [01-architecture-overview.md](./01-architecture-overview.md)
  - Full repo map
  - Frontend, backend, database, and model architecture
  - Component responsibilities
  - Mermaid architecture diagram

- [02-runtime-and-data-flows.md](./02-runtime-and-data-flows.md)
  - Runtime request lifecycle (chat and streaming)
  - Retrieval and routing flow
  - Ingestion/indexing flow from PDFs to ChromaDB
  - Feedback persistence flow
  - Mermaid sequence and flow diagrams

- [03-local-dev-setup.md](./03-local-dev-setup.md)
  - Complete local setup guide (one-time and daily)
  - `start.sh` / `stop.sh` reference
  - Port map and configuration reference
  - Troubleshooting for common startup failures

## Quick Start For New Contributors

1. Read [01-architecture-overview.md](./01-architecture-overview.md) first.
2. Read [02-runtime-and-data-flows.md](./02-runtime-and-data-flows.md) second.
3. Follow [03-local-dev-setup.md](./03-local-dev-setup.md) to set up and start the full stack.
4. Use the Chroma admin endpoints and backend tests to validate assumptions before making major changes.

## Why This Exists

These docs are intended to reduce repeated rediscovery of system behavior and to make onboarding repeatable without needing to ask an AI assistant for the same architecture walkthrough.
