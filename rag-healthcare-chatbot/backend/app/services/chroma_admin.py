from app.services.chroma_client import get_chroma_client


def _to_json_safe(value):
    if hasattr(value, "tolist"):
        return value.tolist()

    if isinstance(value, dict):
        return {key: _to_json_safe(item) for key, item in value.items()}

    if isinstance(value, list):
        return [_to_json_safe(item) for item in value]

    return value


def _coerce_metadata(metadata):
    if metadata is None:
        return {}

    if isinstance(metadata, dict):
        return _to_json_safe(metadata)

    return {"value": _to_json_safe(metadata)}


def _coerce_sequence(value):
    if value is None:
        return []

    safe_value = _to_json_safe(value)
    if isinstance(safe_value, list):
        return safe_value

    return [safe_value]


def _collection_to_payload(collection):
    try:
        count = collection.count()
    except Exception:
        count = None

    metadata = getattr(collection, "metadata", None)

    return {
        "name": collection.name,
        "count": count,
        "metadata": _coerce_metadata(metadata),
    }


def _get_collection(name: str):
    client = get_chroma_client()
    return client.get_collection(name=name)


def _build_records(items):
    ids = _coerce_sequence(items.get("ids"))
    documents = _coerce_sequence(items.get("documents"))
    metadatas = _coerce_sequence(items.get("metadatas"))
    embeddings = _coerce_sequence(items.get("embeddings"))

    records = []
    for index, item_id in enumerate(ids):
        document = documents[index] if index < len(documents) else None
        metadata = metadatas[index] if index < len(metadatas) else None
        embedding = embeddings[index] if index < len(embeddings) else None

        record = {
            "id": item_id,
            "document": document,
            "document_length": len(document) if isinstance(document, str) else 0,
            "metadata": _coerce_metadata(metadata),
            "metadata_keys": sorted(metadata.keys()) if isinstance(metadata, dict) else [],
        }

        if embedding is not None:
            safe_embedding = _to_json_safe(embedding)
            record["embedding_size"] = (
                len(safe_embedding) if isinstance(safe_embedding, list) else None
            )
            record["embedding_preview"] = (
                safe_embedding[:8] if isinstance(safe_embedding, list) else safe_embedding
            )

        records.append(record)

    return records


def list_collections():
    client = get_chroma_client()
    collections = client.list_collections()
    results = []

    for collection in collections:
        if isinstance(collection, str):
            collection = client.get_collection(name=collection)

        results.append(_collection_to_payload(collection))

    return results


def get_collection_preview(name: str, limit: int = 5):
    collection = _get_collection(name)
    preview = _to_json_safe(collection.peek(limit=limit))

    return {
        "name": name,
        "count": collection.count(),
        "preview": preview,
    }


def get_collection_overview(name: str, sample_size: int = 25):
    collection = _get_collection(name)
    total_count = collection.count()
    sample_size = max(1, min(sample_size, 100))
    items = collection.get(
        limit=sample_size,
        offset=0,
        include=["documents", "metadatas", "embeddings"],
    )
    records = _build_records(items)

    metadata_keys = sorted(
        {
            key
            for record in records
            for key in (record.get("metadata_keys") or [])
        }
    )
    docs_with_metadata = sum(1 for record in records if record["metadata"])
    avg_document_length = 0
    if records:
        avg_document_length = round(
            sum(record["document_length"] for record in records) / len(records)
        )

    embedding_size = None
    for record in records:
        if record.get("embedding_size") is not None:
            embedding_size = record["embedding_size"]
            break

    return {
        "collection": _collection_to_payload(collection),
        "summary": {
            "sample_size": len(records),
            "documents_with_metadata": docs_with_metadata,
            "average_document_length": avg_document_length,
            "metadata_keys": metadata_keys,
            "embedding_size": embedding_size,
        },
        "sample_records": records[:5],
    }


def get_collection_records(name: str, offset: int = 0, limit: int = 25):
    collection = _get_collection(name)
    total_count = collection.count()
    offset = max(offset, 0)
    limit = max(1, min(limit, 100))
    items = collection.get(
        limit=limit,
        offset=offset,
        include=["documents", "metadatas", "embeddings"],
    )
    records = _build_records(items)

    return {
        "name": name,
        "count": total_count,
        "offset": offset,
        "limit": limit,
        "returned": len(records),
        "has_next_page": offset + len(records) < total_count,
        "records": records,
    }
