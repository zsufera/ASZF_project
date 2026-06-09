import json

from preprocessing.enrich_cross_refs import enrich_chunks_file


def test_enrich_rewrites_cross_refs_from_text(tmp_path):
    rows = [
        {"chunk_id": "c1", "text": "A 5.6 pont és a 2/B. számú melléklet 4.1.4 pont szerint.", "cross_refs": []},
        {"chunk_id": "c2", "text": "Sima mondat.", "cross_refs": ["régi string"]},
    ]
    path = tmp_path / "chunks.jsonl"
    path.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n", encoding="utf-8")

    count = enrich_chunks_file(path)

    out = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    assert count == 2
    assert isinstance(out[0]["cross_refs"], list) and isinstance(out[0]["cross_refs"][0], dict)
    assert any(r["paragraph"] == "5.6" for r in out[0]["cross_refs"])
    assert out[1]["cross_refs"] == []  # a régi string lecserélve üresre (nincs hivatkozás a szövegben)
