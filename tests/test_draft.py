import backend.draft as draft
from backend.draft import build_draft
from config.settings import settings


def _llm_policy_map():
    return {
        "policy_items": [
            {"chunk_id": "one-5-1", "idezet": "A számlázási kifogást az ügyfélszolgálat kivizsgálja."}
        ],
        "missing_mandatory": [],
    }


def test_build_draft_uses_template_without_llm(monkeypatch):
    monkeypatch.setattr(settings, "openai_api_key", "")  # llm unavailable
    result = draft.build_draft(
        case_id="c1", category="szamlazas", output_mode="hitl",
        policy_map=_llm_policy_map(), actions=[],
    )
    assert result["generation_mode"] == "template"
    assert "Tisztelt Ügyfelünk!" in result["body_masked"]


def test_build_draft_uses_llm_and_validates_citations(monkeypatch):
    monkeypatch.setattr(settings, "provider", "cloud")
    monkeypatch.setattr(settings, "llm_enabled", True)
    monkeypatch.setattr(settings, "openai_api_key", "sk-test")
    monkeypatch.setattr(
        draft,
        "chat_json",
        lambda system, user: {
            "targy": "Válasz számlázás ügyben",
            "level_szoveg": "Tisztelt Ügyfelünk! A kifogást kivizsgáljuk.",
            "felhasznalt_forrasok": ["one-5-1", "hamis-id"],
        },
    )
    result = draft.build_draft(
        case_id="c1", category="szamlazas", output_mode="hitl",
        policy_map=_llm_policy_map(), actions=[],
    )
    assert result["generation_mode"] == "llm"
    assert result["subject"] == "Válasz számlázás ügyben"
    assert result["citations"] == ["one-5-1"]  # invalid id filtered out


def test_build_draft_falls_back_on_empty_body(monkeypatch):
    monkeypatch.setattr(settings, "provider", "cloud")
    monkeypatch.setattr(settings, "llm_enabled", True)
    monkeypatch.setattr(settings, "openai_api_key", "sk-test")
    monkeypatch.setattr(draft, "chat_json", lambda system, user: {"level_szoveg": ""})
    result = draft.build_draft(
        case_id="c1", category="szamlazas", output_mode="hitl",
        policy_map=_llm_policy_map(), actions=[],
    )
    assert result["generation_mode"] == "template"


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
    "mandatory_refs": [],
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
