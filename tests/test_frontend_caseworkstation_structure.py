from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_case_workstation_is_split_into_hooks_and_panels() -> None:
    hooks = [
        ROOT / "frontend" / "src" / "hooks" / "useCaseData.ts",
        ROOT / "frontend" / "src" / "hooks" / "useCaseActions.ts",
    ]
    panels = [
        "CaseHeader.tsx",
        "CaseSourcesPanel.tsx",
        "CaseHistoryPanel.tsx",
        "CaseCustomerPanel.tsx",
        "CaseDraftPanel.tsx",
        "CaseTimelinePanel.tsx",
        "CaseInboundMessage.tsx",
    ]

    for hook in hooks:
        assert hook.exists(), hook
    for panel in panels:
        assert (ROOT / "frontend" / "src" / "components" / "case" / panel).exists(), panel

    workstation = (ROOT / "frontend" / "src" / "screens" / "CaseWorkstation.tsx").read_text(encoding="utf-8")
    assert 'from "../hooks/useCaseData"' in workstation
    assert 'from "../hooks/useCaseActions"' in workstation
    assert workstation.count("<Card") == 0
    assert len(workstation.splitlines()) < 180
