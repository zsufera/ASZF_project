from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_tier1_types_expose_provenance_verify_and_audit_contracts() -> None:
    source = read("frontend/src/lib/types.ts")

    assert "export interface VerifyClaim" in source
    assert "retrieval_source?: RetrievalSource" in source
    assert "export type UnresolvedReference" in source
    assert "unresolved_refs: UnresolvedReference[]" in source
    assert "verify: VerifyState" in source
    assert "export interface AuditEvent" in source
    assert "export interface AuditCompleteness" in source
    assert "export interface AcceptanceResult" in source


def test_tier1_api_exposes_audit_trace_acceptance_endpoints() -> None:
    source = read("frontend/src/lib/api.ts")

    assert "getAuditEvents" in source
    assert "/audit/events" in source
    assert "getAuditCompleteness" in source
    assert "/audit/completeness/" in source
    assert "getTraces" in source
    assert "/observability/traces" in source
    assert "runAcceptance" in source
    assert "/acceptance/run" in source


def test_tier1_case_workstation_renders_provenance_and_audit_panels() -> None:
    case_source = read("frontend/src/screens/CaseWorkstation.tsx")
    sources_panel = read("frontend/src/components/case/CaseSourcesPanel.tsx")
    draft_panel = read("frontend/src/components/case/CaseDraftPanel.tsx")

    assert "AuditPanel" in case_source
    assert "verify={caseData.agent_state?.verify}" in case_source
    assert "unresolvedRefs={caseData.agent_state?.retrieval?.unresolved_refs" in case_source
    assert "ProvenanceBadge" in sources_panel
    assert "UnresolvedReferencesPanel" in sources_panel
    assert "GroundingClaimsPanel" in draft_panel
    assert "MandatoryReferencesPanel" in draft_panel


def test_unresolved_references_are_formatted_before_rendering() -> None:
    sources_panel = read("frontend/src/components/case/CaseSourcesPanel.tsx")

    assert "formatUnresolvedRef" in sources_panel
    assert "JSON.stringify(ref)" in sources_panel


def test_tier1_supervisor_and_evaluation_use_structured_dashboards() -> None:
    supervisor = read("frontend/src/screens/Supervisor.tsx")
    evaluation = read("frontend/src/screens/Evaluation.tsx")

    assert "AuditEventSearch" in supervisor
    assert "AuditCompletenessCard" in supervisor
    assert "TraceViewer" in supervisor
    assert "PurgePreview" in supervisor
    assert "AcceptanceGatePanel" in evaluation
    assert "EvalRegressionDiff" in evaluation
    assert "EvalCaseDrilldown" in evaluation
    assert "HumanScoreSummary" in evaluation
