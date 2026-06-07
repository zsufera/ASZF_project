import json
from pathlib import Path

from preprocessing.index import load_chunks, search_chunks


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
