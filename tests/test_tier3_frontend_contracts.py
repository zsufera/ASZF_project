from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_inbox_productivity_contract() -> None:
    inbox = read("frontend/src/screens/Inbox.tsx")
    assert "SavedViewsBar" in inbox
    assert "BulkActionBar" in inbox
    assert "useInboxKeyboard" in inbox
    assert "jogos.inbox.filters" in inbox
    assert "selectedCaseIds" in inbox


def test_command_palette_contract() -> None:
    shell = read("frontend/src/components/AppShell.tsx")
    palette = read("frontend/src/components/CommandPalette.tsx")
    assert "CommandPalette" in shell
    assert "Ctrl+K" in palette
    assert "commandRegistry" in palette
    assert "/knowledge" in palette


def test_draft_power_editing_contract() -> None:
    editor = read("frontend/src/components/DraftEditor.tsx")
    assert "DraftVersionDiff" in editor
    assert "CitationInsertMenu" in editor
    assert "ApprovalChecklist" in editor
    assert "insertCitation" in editor


def test_knowledge_browser_frontend_contract() -> None:
    api = read("frontend/src/lib/api.ts")
    app = read("frontend/src/App.tsx")
    nav = read("frontend/src/components/IconNav.tsx")
    knowledge = read("frontend/src/screens/Knowledge.tsx")
    assert "getAszfTree" in api
    assert "getAszfSection" in api
    assert "searchAszf" in api
    assert "/knowledge" in app
    assert "/knowledge" in nav
    assert "Knowledge" in knowledge
    assert "cross_refs" in knowledge
