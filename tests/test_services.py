from backend.services import approval_service, classification_service, rag_service


def test_classification_service_returns_category_and_mode():
    out = classification_service.classify("Nincs internetem napok ota", history_summary_masked=None)
    assert out["category"] == "hibabejelentes_szolgaltataskieses"
    assert out["mode"] in {"rule", "llm"}


def test_rag_service_retrieve_for_case_packages_chunks_and_policy_map():
    out = rag_service.retrieve_for_case(
        text_masked="Mennyi a felmondasi ido?",
        category="szerzodesfelmondas_modositas",
        service_provider=None,
    )
    assert "chunks" in out
    assert "policy_map" in out
    assert "result_count" in out
    assert "policy_items" in out["policy_map"]


def test_approval_service_prepare_preview_strips_markers():
    preview = approval_service.prepare_preview(
        case_id="CHAT-test",
        subject="Targy [S1]",
        body_masked="A felmondasi ido 30 nap. [S1]",
    )
    assert "[S1]" not in preview["subject_unmasked"]
    assert "[S1]" not in preview["body_unmasked"]
    assert "ready_for_approval" in preview
