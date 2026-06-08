from preprocessing.parse import extract_references


def test_extract_local_paragraph_reference():
    refs = extract_references("A 5.6 pont szerint további szabályok érvényesek.")
    assert {"raw": "5.6 pont", "doc_hint": None, "paragraph": "5.6"} in refs


def test_extract_cross_doc_reference_with_paragraph():
    refs = extract_references("Lásd a 2/B. számú melléklet 4.1.4 pont rendelkezéseit.")
    hit = [r for r in refs if r["doc_hint"]]
    assert hit and "melléklet" in hit[0]["doc_hint"].lower()
    assert hit[0]["paragraph"] == "4.1.4"


def test_extract_cross_doc_reference_without_paragraph():
    refs = extract_references("a 3. számú melléklete szerint")
    assert any(r["doc_hint"] and r["paragraph"] is None and "3" in r["doc_hint"] for r in refs)


def test_extract_dedups_and_skips_garbage():
    refs = extract_references("5.6 pont, majd ismét 5.6 pont. li. \nPont")
    paras = [r["paragraph"] for r in refs]
    assert paras.count("5.6") == 1


def test_extract_returns_empty_on_plain_text():
    assert extract_references("Ez egy sima mondat szám nélkül.") == []
