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
