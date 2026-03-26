# Runtime and Data Flows

This document explains how data moves through the system at runtime and during ingestion.

---

## 1) Runtime Chat Flow (Streaming)

Primary route: `POST /chat/stream`

```mermaid
sequenceDiagram
  autonumber
  participant U as User
  participant FE as React App
  participant API as FastAPI /chat/stream
  participant RP as RAGPipeline
  participant RT as Retriever
  participant AR as ApplicationRouter
  participant VS as VectorStore
  participant CH as ChromaDB
  participant PJ as Processed JSONL
  participant PB as PromptBuilder
  participant LM as LLM (Ollama)

  U->>FE: Enter question + optional scope
  FE->>API: POST /chat/stream {question, app?, history}
  API->>RP: stream(question, history, where)

  RP->>RP: check answer cache
  alt cache hit
    RP-->>API: meta + token + done
    API-->>FE: NDJSON stream
  else cache miss
    RP->>RT: retrieve(retrieval_query, history, where)
    RT->>AR: resolve_collection(...)
    AR-->>RT: route {app, collection, reason, confidence}

    RT->>VS: search(query, collection, k, metadata filters)
    VS->>CH: semantic query
    VS->>PJ: lexical fallback search
    VS-->>RT: merged/reranked chunks
    RT-->>RP: route + chunks

    RP->>PB: build(query, chunks, history)
    RP-->>API: meta event (routing + sources)

    RP->>LM: stream_generate(prompt)
    loop each generated token
      LM-->>RP: token text
      RP-->>API: token event
      API-->>FE: token event
    end

    RP-->>API: done event
    API-->>FE: done event
    RP->>RP: store answer cache
  end

  FE->>FE: Render answer + routed app + source count
```

Event contracts consumed by frontend:

- `meta`: routing info and retrieved sources
- `token`: incremental answer text
- `done`: generation complete
- `error`: stream-level runtime issue

---

## 2) Runtime Chat Flow (Non-Streaming)

Primary route: `POST /chat`

1. Frontend or client sends `question`, optional `app`, optional `history`.
2. Backend calls `RAGPipeline.run(...)`.
3. Pipeline retrieves route + sources, generates single answer.
4. Returns JSON payload containing:
   - `answer`
   - `sources`
   - `collection`
   - `app`
   - `routing`

---

## 3) Retrieval + Routing Decision Flow

```mermaid
flowchart TD
  Start([Incoming question]) --> Filter{Explicit app/collection filter?}

  Filter -- Yes --> Explicit[Use explicit route]
  Filter -- No --> Heuristic{Heuristic alias/keyword match?}

  Heuristic -- Yes --> RouteHeuristic[Use heuristic route]
  Heuristic -- No --> Cache{Route cache hit?}

  Cache -- Yes --> RouteCache[Use cached route]
  Cache -- No --> Agent{Router model returns valid app_key?}

  Agent -- Yes --> RouteAgent[Use model-selected route]
  Agent -- No --> Fallback[Use fallback default route]

  Explicit --> Search
  RouteHeuristic --> Search
  RouteCache --> Search
  RouteAgent --> Search
  Fallback --> Search

  Search[VectorStore search]
  Search --> Semantic[Chroma semantic query]
  Search --> Lexical[Processed JSONL lexical lookup]
  Semantic --> Merge[Merge + dedupe + rerank]
  Lexical --> Merge
  Merge --> TopK[Top K chunks returned]
  TopK --> Prompt[PromptBuilder]
  Prompt --> Generate[LLM generate/stream]
```

---

## 4) Ingestion and Indexing Flow

Purpose: transform raw PDFs into chunked records and ingest into Chroma collections.

```mermaid
flowchart LR
  Raw[(backend/data/raw/*.pdf)] --> ChunkScript[run_chunking.py]
  ChunkScript --> Pipeline[DocumentProcessingPipeline]

  Pipeline --> Extract[Extract text blocks, sections, tables, images]
  Pipeline --> OCR[Optional OCR for images]
  Pipeline --> Classify[Domain classification\npatient/prescription/alerts/troubleshooting]
  Pipeline --> WriteJSONL[Write *_chunks.jsonl\nper app and domain]

  WriteJSONL --> Processed[(backend/data/processed/<app>/)]

  Processed --> IngestScript[build_index.py or --ingest-chroma]
  IngestScript --> Ingestor[ChromaIngestor]
  Ingestor --> Chroma[(Chroma collections per app)]
```

Ingestion ownership:

- Chunk generation: `services/document_pipeline.py`
- Chroma writes: `services/chroma_ingestor.py`
- Script orchestration: `scripts/run_chunking.py`, `scripts/build_index.py`

---

## 5) Feedback Flow

```mermaid
sequenceDiagram
  autonumber
  participant U as User
  participant FE as React App
  participant API as FastAPI
  participant FS as FeedbackStore
  participant DB as SQLite feedback.sqlite3

  U->>FE: Click like/dislike on assistant message
  FE->>API: POST /feedback/like or /feedback/dislike
  API->>FS: save_like/save_dislike(message_id, question, answer, created_at)
  FS->>DB: Upsert into feedback table by message_id
  DB-->>FS: stored/updated
  FS-->>API: success
  API-->>FE: {status: saved}
```

Design behavior:

- Feedback is idempotent by `message_id` via upsert.
- Changing from like to dislike (or reverse) updates same row.

---

## 6) Caching Behavior

Three LRU-like caches are used to reduce repeated compute and calls:

- Route cache in `ApplicationRouter`
- Retrieval cache in `Retriever`
- Answer cache in `RAGPipeline`

Cache keys include normalized query + recent history + filters to preserve context sensitivity.

---

## 7) Failure Modes and Typical Symptoms

1. Chroma unavailable
   - Symptom: runtime retrieval failures, collection endpoints failing
   - Check: Chroma server status and configured host/port

2. Missing collections
   - Symptom: explicit runtime message instructing ingestion steps
   - Fix: run chunking/ingestion scripts and verify collections

3. Ollama unavailable
   - Symptom: generation failures and 503-style backend behavior
   - Check: Ollama service/model readiness

4. Empty retrieval context
   - Symptom: fallback answer about missing knowledge base context
   - Check: route selected, chunk quality, and ingestion coverage

---

## 8) Test Coverage Map

Current backend tests verify critical architecture contracts:

- `test_main_api.py`
  - API behavior, stream formatting, error handling, feedback delegation
- `test_retriever.py`
  - explicit scope bypass and collection targeting
- `test_vector_store.py`
  - reranking and lexical fallback behavior
- `test_chroma_admin.py`
  - admin record shaping and summary payload contracts

---

## 9) Contributor Checklist Before Major Changes

1. Confirm whether change is runtime-path or ingestion-path.
2. Validate app routing assumptions (`nx2meapp` vs `kinexushhd`).
3. Run backend tests before and after modification.
4. Verify streaming event contract remains unchanged for frontend.
5. If changing retrieval ranking, validate with representative support questions.
6. If changing ingestion, confirm JSONL schema remains compatible with current vector ingestion.

---

## 10) Glossary

- Route: selected app/collection target for retrieval.
- Chunk: indexed text unit (section/table/image-derived) with metadata.
- Semantic retrieval: embedding similarity from Chroma.
- Lexical fallback: keyword/token match against processed JSONL chunks.
- NDJSON stream: newline-delimited JSON events used for token streaming.
