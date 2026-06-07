from backend.draft import build_draft


POLICY_MAP = {
    "policy_items": [
        {
            "chunk_id": "one-3-1",
            "dok_tipus": "ÁSZF",
            "paragrafus": "3.1",
            "idezet": "A számlázási kifogást az ügyfélszolgálat kivizsgálja.",
            "kozertheto_magyarazat": "A forrás alapján ez a rész releváns a(z) szamlazas ügyhöz.",
            "dok_cim": "ONE ÁSZF",
            "oldalszam": 12,
            "score": 1.0,
        }
    ],
    "mandatory_refs": ["A szamlazasi szabalyok relevans paragrafusai"],
    "missing_mandatory": [],
}


def test_build_draft_hitl_uses_policy_sources_without_disclaimer() -> None:
    result = build_draft(
        case_id="CASE-1",
        category="szamlazas",
        output_mode="hitl",
        policy_map=POLICY_MAP,
        actions=[],
    )

    assert result["subject"] == "Válaszjavaslat szamlazas ügyben"
    assert "A számlázási kifogást az ügyfélszolgálat kivizsgálja." in result["body_masked"]
    assert result["citations"] == ["one-3-1"]
    assert result["disclaimer_applied"] is False


def test_build_draft_automata_adds_disclaimer() -> None:
    result = build_draft(
        case_id="CASE-1",
        category="szamlazas",
        output_mode="automata",
        policy_map=POLICY_MAP,
        actions=[],
        disclaimer_text="Automata disclaimer.",
    )

    assert result["disclaimer_applied"] is True
    assert "Automata disclaimer." in result["body_masked"]
