import json
from pathlib import Path

import preprocessing.index as index
from config.settings import settings
from preprocessing.index import load_chunks, search_chunks


def test_index_chunks_local_mode_deterministic(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "qdrant_mode", "local")
    monkeypatch.setattr(settings, "qdrant_path", str(tmp_path / "qd"))
    monkeypatch.setattr(settings, "provider", "cloud")
    monkeypatch.setattr(settings, "openai_api_key", "")  # deterministic -> size 64

    chunks = [
        {"chunk_id": "c1", "szolgaltato": "ONE", "text": "számlázási kifogás kezelése"},
        {"chunk_id": "c2", "szolgaltato": "ONE", "text": "felmondás feltételei"},
    ]

    client = index.make_client()
    count = index.index_chunks(chunks, client=client)

    assert count == 2
    info = client.get_collection(index.DEFAULT_COLLECTION)
    assert info.config.params.vectors.size == 64
    # content_hash is attached to payloads
    points, _ = client.scroll(index.DEFAULT_COLLECTION, with_payload=True, limit=10)
    assert all("content_hash" in point.payload for point in points)
    client.close()


def test_index_chunks_removes_stale_points_on_reindex(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "qdrant_mode", "local")
    monkeypatch.setattr(settings, "qdrant_path", str(tmp_path / "qd"))
    monkeypatch.setattr(settings, "provider", "cloud")
    monkeypatch.setattr(settings, "openai_api_key", "")

    client = index.make_client()
    index.index_chunks(
        [
            {"chunk_id": "old", "szolgaltato": "ONE", "text": "regi chunk"},
            {"chunk_id": "keep", "szolgaltato": "ONE", "text": "marado chunk"},
        ],
        client=client,
    )

    index.index_chunks(
        [{"chunk_id": "keep", "szolgaltato": "ONE", "text": "marado chunk"}],
        client=client,
    )

    points, _ = client.scroll(index.DEFAULT_COLLECTION, with_payload=True, limit=10)
    assert [point.payload["chunk_id"] for point in points] == ["keep"]
    client.close()


def test_point_id_is_stable_for_chunk_id():
    assert index.point_id("c1") == index.point_id("c1")
    assert index.point_id("c1") != index.point_id("c2")


def test_load_chunks_reads_jsonl(tmp_path: Path) -> None:
    chunks_path = tmp_path / "chunks.jsonl"
    chunks_path.write_text(
        json.dumps(
            {
                "chunk_id": "chunk-1",
                "szolgaltato": "ONE",
                "dok_tipus": "ÁSZF",
                "paragrafus_szam": "1.2",
                "text": "Számlázási panasz kezelése.",
            },
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )

    chunks = load_chunks(chunks_path)

    assert len(chunks) == 1
    assert chunks[0]["chunk_id"] == "chunk-1"
    assert chunks[0]["text"] == "Számlázási panasz kezelése."


def test_search_chunks_filters_provider_and_returns_source_fields(tmp_path: Path) -> None:
    chunks_path = tmp_path / "chunks.jsonl"
    rows = [
        {
            "chunk_id": "one-billing",
            "szolgaltato": "ONE",
            "dok_tipus": "ÁSZF",
            "paragrafus_szam": "3.1",
            "text": "A számlázási kifogás bejelentése és kivizsgálása.",
        },
        {
            "chunk_id": "invitech-billing",
            "szolgaltato": "Invitech",
            "dok_tipus": "ÁSZF",
            "paragrafus_szam": "3.1",
            "text": "A számlázási kifogás másik szolgáltatóra.",
        },
    ]
    chunks_path.write_text(
        "\n".join(json.dumps(row, ensure_ascii=False) for row in rows) + "\n",
        encoding="utf-8",
    )

    results = search_chunks(
        query="számlázási kifogás",
        chunks=load_chunks(chunks_path),
        service_provider="ONE",
        limit=3,
    )

    assert [result["chunk_id"] for result in results] == ["one-billing"]
    assert results[0]["quote"] == "A számlázási kifogás bejelentése és kivizsgálása."
    assert results[0]["dok_tipus"] == "ÁSZF"
    assert results[0]["paragrafus"] == "3.1"
