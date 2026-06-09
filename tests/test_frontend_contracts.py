from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_case_workstation_uses_stable_sender_key_for_history() -> None:
    source = (ROOT / "frontend/src/screens/CaseWorkstation.tsx").read_text(encoding="utf-8")

    assert "getHistory(c.sender_email_masked)" not in source
    assert "getHistory(c.sender_email_masked, c.sender_email_key)" in source


def test_case_type_exposes_sender_email_key() -> None:
    source = (ROOT / "frontend/src/lib/types.ts").read_text(encoding="utf-8")

    assert "sender_email_key: string;" in source
    assert "sender_email_display: string;" in source


def test_api_history_accepts_stable_sender_key() -> None:
    source = (ROOT / "frontend/src/lib/api.ts").read_text(encoding="utf-8")

    assert "getHistory: (address: string, senderEmailKey?: string)" in source
    assert "sender_email_key" in source


def test_draft_editor_defaults_to_latest_version_first() -> None:
    source = (ROOT / "frontend/src/components/DraftEditor.tsx").read_text(encoding="utf-8")

    assert "versions[versions.length - 1]" not in source
    assert "versions[0]?.id" in source


def test_frontend_generation_mode_accepts_template_fallback() -> None:
    types_source = (ROOT / "frontend/src/lib/types.ts").read_text(encoding="utf-8")
    copilot_source = (ROOT / "frontend/src/screens/Copilot.tsx").read_text(encoding="utf-8")

    assert 'GenerationMode = "llm" | "insufficient" | "template"' in types_source
    assert "generation_mode?: GenerationMode" in copilot_source


def test_case_header_uses_stable_sender_display_not_reusable_mask_token() -> None:
    source = (ROOT / "frontend/src/screens/CaseWorkstation.tsx").read_text(encoding="utf-8")

    assert "{caseData.sender_email_masked}" not in source
    assert "{caseData.sender_email_display}" in source
