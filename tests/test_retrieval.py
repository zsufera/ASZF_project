from backend.retrieval import hybrid_score, resolve_cross_refs, retrieve


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
