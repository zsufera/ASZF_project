from backend.retrieval import auto_merge_siblings


def _chunk(cid, para, text="t"):
    return {"chunk_id": cid, "doc_id": "d", "paragrafus_szam": para, "text": text,
            "szolgaltato": "ONE", "dok_tipus": "ÁSZF", "dok_cim": "X", "oldalszam": 1,
            "cross_refs": [], "source_file": "x.pdf"}


CORPUS = [
    _chunk("l1", "5.5.1"), _chunk("l2", "5.5.2"), _chunk("l3", "5.5.3"),
    _chunk("parent", "5.5", "A teljes 5.5 szakasz."),
    _chunk("other", "2.1"),
]


def test_auto_merge_merges_sibling_leaves():
    results = [
        {"chunk_id": "l1", "score": 0.8, "paragrafus": "5.5.1"},
        {"chunk_id": "l2", "score": 0.7, "paragrafus": "5.5.2"},
        {"chunk_id": "other", "score": 0.6, "paragrafus": "2.1"},
    ]
    out = auto_merge_siblings(results, CORPUS)
    ids = [r["chunk_id"] for r in out]
    assert "parent" in ids          # a testvérek a szülőbe olvadtak
    assert "l1" not in ids and "l2" not in ids
    assert "other" in ids           # a nem-testvér megmarad
    parent_r = next(r for r in out if r["chunk_id"] == "parent")
    assert parent_r["retrieval_source"] == "auto_merged"


def test_auto_merge_keeps_single_leaf():
    results = [{"chunk_id": "l1", "score": 0.8, "paragrafus": "5.5.1"}]
    out = auto_merge_siblings(results, CORPUS)
    assert [r["chunk_id"] for r in out] == ["l1"]  # egyetlen leaf -> nincs merge


def test_auto_merge_no_parent_chunk_keeps_leaves():
    corpus = [_chunk("a", "9.9.1"), _chunk("b", "9.9.2")]  # nincs 9.9 szülő chunk
    results = [{"chunk_id": "a", "score": 0.8, "paragrafus": "9.9.1"},
               {"chunk_id": "b", "score": 0.7, "paragrafus": "9.9.2"}]
    out = auto_merge_siblings(results, corpus)
    assert {r["chunk_id"] for r in out} == {"a", "b"}
