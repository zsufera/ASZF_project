from backend.reference_resolution import (
    normalize_paragraph, build_doc_name_index, build_paragraph_index, resolve_reference,
)

CHUNKS = [
    {"chunk_id": "one_2a_p1", "doc_id": "doc_2a", "szolgaltato": "ONE", "paragrafus_szam": "4.1.4",
     "source_file": "data/raw_pdfs/ASZF_2A_mobil_melleklet_hatalyos_20260605.pdf", "text": "x"},
    {"chunk_id": "one_torzs_p1", "doc_id": "doc_torzs", "szolgaltato": "ONE", "paragrafus_szam": "5.5",
     "source_file": "data/raw_pdfs/ASZF_0_torzs_hatalyos_20260605.pdf", "text": "y"},
    {"chunk_id": "inv_1_p1", "doc_id": "doc_inv1", "szolgaltato": "Invitech", "paragrafus_szam": "1.1",
     "source_file": "data/raw_pdfs/InvitechASZF_1_sz_melleklet20260101.pdf", "text": "z"},
]


def test_normalize_paragraph_extracts_number():
    assert normalize_paragraph("5.5.1 pont") == "5.5.1"
    assert normalize_paragraph(None) == ""


def test_doc_name_index_maps_melleklet_per_provider():
    idx = build_doc_name_index(CHUNKS)
    assert idx[("ONE", "2a melleklet")] == "doc_2a"
    assert idx[("ONE", "2 melleklet")] == "doc_2a"
    assert idx[("Invitech", "1 melleklet")] == "doc_inv1"


def test_resolve_cross_doc_reference():
    src = CHUNKS[1]  # ONE törzs chunk
    ref = {"raw": "2/A. számú melléklet 4.1.4 pont", "doc_hint": "2/A. számú melléklet", "paragraph": "4.1.4"}
    di = build_doc_name_index(CHUNKS); pi = build_paragraph_index(CHUNKS)
    hit = resolve_reference(ref, src, di, pi)
    assert hit is not None and hit["chunk_id"] == "one_2a_p1"


def test_resolve_local_reference_prefix_match():
    src = CHUNKS[0]
    ref = {"raw": "5.5 pont", "doc_hint": None, "paragraph": "5.5"}
    di = build_doc_name_index(CHUNKS); pi = build_paragraph_index(CHUNKS)
    # lokális hivatkozás a forrás dokumentumában (doc_2a) — ott nincs 5.5 → None
    assert resolve_reference(ref, src, di, pi) is None
    # de a törzs chunkból (doc_torzs) feloldódik a saját 5.5-e
    assert resolve_reference(ref, CHUNKS[1], di, pi)["chunk_id"] == "one_torzs_p1"


def test_resolve_returns_none_without_paragraph():
    src = CHUNKS[1]
    ref = {"raw": "3. számú melléklet", "doc_hint": "3. számú melléklet", "paragraph": None}
    di = build_doc_name_index(CHUNKS); pi = build_paragraph_index(CHUNKS)
    assert resolve_reference(ref, src, di, pi) is None


def test_resolve_does_not_cross_provider():
    src = CHUNKS[1]  # ONE
    ref = {"raw": "1. számú melléklet 1.1 pont", "doc_hint": "1. számú melléklet", "paragraph": "1.1"}
    di = build_doc_name_index(CHUNKS); pi = build_paragraph_index(CHUNKS)
    # ONE-nál nincs "1 melleklet" → nem oldja fel az Invitech dokumentumát
    assert resolve_reference(ref, src, di, pi) is None


from backend.reference_resolution import reference_closure


def _corpus():
    return [
        {"chunk_id": "a1", "doc_id": "d", "szolgaltato": "ONE", "paragrafus_szam": "5.1",
         "source_file": "x.pdf", "text": "A 5.2 pont szerint.",
         "cross_refs": [{"raw": "5.2 pont", "doc_hint": None, "paragraph": "5.2"}]},
        {"chunk_id": "a2", "doc_id": "d", "szolgaltato": "ONE", "paragrafus_szam": "5.2",
         "source_file": "x.pdf", "text": "A határidő 30 nap.", "cross_refs": []},
    ]


def test_closure_pulls_linked_chunk():
    corpus = _corpus()
    seed = [dict(corpus[0], score=0.8)]
    added, unresolved = reference_closure(seed, corpus)
    assert len(added) == 1
    chunk, score = added[0]
    assert chunk["chunk_id"] == "a2"
    assert round(score, 2) == 0.75
    assert unresolved == []


def test_closure_collects_unresolved():
    corpus = _corpus()
    corpus[0]["cross_refs"] = [{"raw": "9.9 pont", "doc_hint": None, "paragraph": "9.9"}]
    seed = [dict(corpus[0], score=0.8)]
    added, unresolved = reference_closure(seed, corpus)
    assert added == []
    assert unresolved and unresolved[0]["paragraph"] == "9.9"


def test_closure_respects_max_extra():
    corpus = _corpus()
    extra = [{"chunk_id": f"e{i}", "doc_id": "d", "szolgaltato": "ONE", "paragrafus_szam": f"7.{i}",
              "source_file": "x.pdf", "text": "t", "cross_refs": []} for i in range(6)]
    corpus[0]["cross_refs"] = [{"raw": f"7.{i} pont", "doc_hint": None, "paragraph": f"7.{i}"} for i in range(6)]
    seed = [dict(corpus[0], score=0.8)]
    added, _ = reference_closure(seed, corpus + extra, max_extra=5)
    assert len(added) == 5


def test_closure_skips_chunk_already_in_seed():
    corpus = _corpus()
    seed = [dict(corpus[0], score=0.8), dict(corpus[1], score=0.7)]
    added, _ = reference_closure(seed, corpus)
    assert added == []
