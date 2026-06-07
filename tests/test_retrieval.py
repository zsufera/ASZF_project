import json

import preprocessing.embedding as emb
import preprocessing.index as index
import backend.retrieval as retrieval
from backend.retrieval import hybrid_score, resolve_cross_refs, retrieve
from config.settings import settings


def _write_two_chunks(tmp_path):
    rows = [
        {"chunk_id": "one-bill", "szolgaltato": "ONE", "dok_tipus": "ÁSZF",
         "paragrafus_szam": "3.1", "doc_id": "d1", "cross_refs": [],
         "text": "A számlázási kifogás bejelentése és kivizsgálása."},
        {"chunk_id": "one-term", "szolgaltato": "ONE", "dok_tipus": "ÁSZF",
         "paragrafus_szam": "5.2", "doc_id": "d1", "cross_refs": [],
         "text": "A szerződés felmondásának feltételei."},
    ]
    path = tmp_path / "chunks.jsonl"
    path.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n",
                    encoding="utf-8")
    return path


def test_retrieve_falls_back_to_hybrid_local_without_key(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "provider", "cloud")
    monkeypatch.setattr(settings, "openai_api_key", "")  # deterministic -> skip qdrant
    chunks_path = _write_two_chunks(tmp_path)

    result = retrieve("számlázási kifogás", service_provider="ONE",
                      chunks_path=chunks_path)

    assert result["retrieval_mode"] == "hybrid_local"
    assert result["result_count"] >= 1


def test_retrieve_uses_semantic_when_openai(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "provider", "cloud")
    monkeypatch.setattr(settings, "openai_api_key", "sk-test")
    monkeypatch.setattr(settings, "openai_embed_dim", 8)
    monkeypatch.setattr(settings, "qdrant_mode", "local")
    monkeypatch.setattr(settings, "qdrant_path", str(tmp_path / "qd"))
    monkeypatch.setattr(emb, "EMBED_CACHE_PATH", tmp_path / "cache.db")

    def fake_embed(texts):
        # "kifogás"-bearing text gets a distinct vector so it ranks first.
        out = []
        for text in texts:
            if "kifogás" in text:
                out.append([1.0, 0, 0, 0, 0, 0, 0, 0])
            else:
                out.append([0, 1.0, 0, 0, 0, 0, 0, 0])
        return out

    monkeypatch.setattr(emb, "_openai_embed", fake_embed)

    chunks_path = _write_two_chunks(tmp_path)
    rows = index.load_chunks(chunks_path)
    index.index_chunks(rows)  # builds local collection at qdrant_path

    result = retrieval.retrieve("kifogás", service_provider="ONE",
                                chunks_path=chunks_path)

    assert result["retrieval_mode"] == "qdrant_semantic"
    assert result["chunks"][0]["chunk_id"] == "one-bill"


def test_hybrid_score_prefers_matching_tokens() -> None:
    high = hybrid_score("szamlazasi kifogas", "A szamlazasi kifogast az ugyfelszolgálat kivizsgálja.", "5.1")
    low = hybrid_score("szamlazasi kifogas", "Mobil internet csomagok leírása.", "2.1")
    assert high > low


def test_resolve_cross_refs_adds_linked_chunk() -> None:
    chunks = [
        {
            "chunk_id": "doc_a_p0001_s001",
            "doc_id": "doc_a",
            "paragrafus_szam": "5.1",
            "text": "A 5.2 pont szerint további szabályok érvényesek.",
            "cross_refs": ["5.2 pont"],
            "dok_tipus": "ÁSZF",
            "dok_cim": "Teszt",
            "oldalszam": 1,
            "szolgaltato": "ONE",
            "source_file": "a.pdf",
        },
        {
            "chunk_id": "doc_a_p0002_s001",
            "doc_id": "doc_a",
            "paragrafus_szam": "5.2",
            "text": "Az eljárás határideje 30 nap.",
            "cross_refs": [],
            "dok_tipus": "ÁSZF",
            "dok_cim": "Teszt",
            "oldalszam": 2,
            "szolgaltato": "ONE",
            "source_file": "a.pdf",
        },
    ]
    primary = [
        {
            "chunk_id": "doc_a_p0001_s001",
            "quote": "A 5.2 pont szerint",
            "score": 0.8,
            "dok_tipus": "ÁSZF",
            "paragrafus": "5.1",
            "szolgaltato": "ONE",
            "dok_cim": "Teszt",
            "oldalszam": 1,
            "cross_refs": ["5.2 pont"],
            "source_file": "a.pdf",
            "retrieval_source": "hybrid_local",
        }
    ]

    expanded = resolve_cross_refs(primary, chunks)

    assert len(expanded) == 2
    assert expanded[1]["chunk_id"] == "doc_a_p0002_s001"
    assert expanded[1]["retrieval_source"] == "cross_ref"


def test_retrieve_filters_service_provider(tmp_path, monkeypatch) -> None:
    chunks_path = tmp_path / "chunks.jsonl"
    rows = [
        {
            "chunk_id": "one-billing",
            "doc_id": "doc_one",
            "szolgaltato": "ONE",
            "dok_tipus": "ÁSZF",
            "dok_cim": "ONE ÁSZF",
            "paragrafus_szam": "5.1",
            "oldalszam": 1,
            "cross_refs": [],
            "source_file": "one.pdf",
            "text": "A szamlazasi kifogast az ugyfelszolgalat kivizsgalja.",
        },
        {
            "chunk_id": "invitech-billing",
            "doc_id": "doc_inv",
            "szolgaltato": "Invitech",
            "dok_tipus": "ÁSZF",
            "dok_cim": "Invitech ÁSZF",
            "paragrafus_szam": "5.1",
            "oldalszam": 1,
            "cross_refs": [],
            "source_file": "inv.pdf",
            "text": "A szamlazasi kifogas masik szolgaltatonal.",
        },
    ]
    chunks_path.write_text(
        "\n".join(__import__("json").dumps(row, ensure_ascii=False) for row in rows) + "\n",
        encoding="utf-8",
    )
    monkeypatch.setattr("backend.retrieval.search_qdrant", lambda *args, **kwargs: [])

    result = retrieve(
        query="szamlazasi kifogas",
        service_provider="ONE",
        chunks_path=chunks_path,
        prefer_qdrant=False,
    )

    assert result["chunks"]
    assert all(chunk["szolgaltato"] == "ONE" for chunk in result["chunks"])
