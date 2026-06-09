from backend.policy_map import category_section_prefixes, category_mandatory_paragraphs


_ENTRIES = {
    "szamlazas": [{"label": "x", "chunk_id": "c1", "paragrafus": "5.5.1"}],
    "szerzodesfelmondas_modositas": [{"label": "y", "chunk_id": "c2", "paragrafus": "7.3.1"}],
    "lefedettseg": [{"label": "z", "chunk_id": "c3", "paragrafus": "8"}],
}


def test_category_section_prefixes_top_level():
    assert category_section_prefixes("szamlazas", _ENTRIES) == {"5"}
    assert category_section_prefixes("szerzodesfelmondas_modositas", _ENTRIES) == {"7"}
    assert category_section_prefixes("lefedettseg", _ENTRIES) == {"8"}


def test_category_section_prefixes_unknown_category_empty():
    assert category_section_prefixes("nincs_ilyen", _ENTRIES) == set()


def test_category_mandatory_paragraphs():
    assert category_mandatory_paragraphs("szamlazas", _ENTRIES) == {"5.5.1"}
    assert category_mandatory_paragraphs("nincs_ilyen", _ENTRIES) == set()


from backend.retrieval import apply_category_boost, retrieve
from config.settings import settings
import json as _json


def test_apply_category_boost_promotes_section_chunk():
    results = [
        {"chunk_id": "x", "paragrafus": "2.1", "score": 0.5},
        {"chunk_id": "y", "paragrafus": "5.5", "score": 0.45},
    ]
    out = apply_category_boost(results, section_prefixes={"5"}, mandatory_paras=set())
    assert out[0]["chunk_id"] == "y"  # 0.45 + 0.1 = 0.55 > 0.5


def test_apply_category_boost_exact_mandatory_stronger():
    # Azonos alap-score: a kötelező § (+0.2) erősebb, mint a puszta szekció-egyezés (+0.1).
    results = [
        {"chunk_id": "x", "paragrafus": "5.9", "score": 0.5},    # szekció -> 0.6
        {"chunk_id": "y", "paragrafus": "5.5.1", "score": 0.5},  # kötelező § -> 0.7
    ]
    out = apply_category_boost(results, section_prefixes={"5"}, mandatory_paras={"5.5.1"})
    assert out[0]["chunk_id"] == "y"


def test_apply_category_boost_noop_without_prefixes():
    results = [{"chunk_id": "x", "paragrafus": "2.1", "score": 0.5}]
    assert apply_category_boost(results, set(), set()) == results


def test_retrieve_accepts_category(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "openai_api_key", "")  # deterministic, skip qdrant
    rows = [
        {"chunk_id": "off", "szolgaltato": "ONE", "dok_tipus": "ÁSZF", "doc_id": "d",
         "paragrafus_szam": "2.1", "cross_refs": [], "source_file": "o.pdf",
         "text": "számlázási kifogás általános információ"},
        {"chunk_id": "bill", "szolgaltato": "ONE", "dok_tipus": "ÁSZF", "doc_id": "d",
         "paragrafus_szam": "5.5.1", "cross_refs": [], "source_file": "o.pdf",
         "text": "számlázási kifogás kivizsgálás"},
    ]
    path = tmp_path / "chunks.jsonl"
    path.write_text("\n".join(_json.dumps(r, ensure_ascii=False) for r in rows) + "\n", encoding="utf-8")
    result = retrieve("számlázási kifogás", service_provider="ONE", chunks_path=path, category="szamlazas")
    assert result["chunks"]
