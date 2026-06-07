from backend import main
from backend.main import EvalRequest, MaskRequest, ReindexRequest, RetrieveRequest, UnmaskRequest


def test_retrieve_endpoint_returns_metadata(monkeypatch) -> None:
    monkeypatch.setattr(
        main,
        "retrieve",
        lambda **kwargs: {
            "chunks": [
                {
                    "chunk_id": "one-3-1",
                    "quote": "A szamlazasi kifogast az ugyfelszolgálat kivizsgálja.",
                    "score": 0.8,
                    "dok_tipus": "ÁSZF",
                    "paragrafus": "3.1",
                    "szolgaltato": "ONE",
                    "dok_cim": "ONE ÁSZF",
                    "oldalszam": 12,
                    "cross_refs": [],
                    "source_file": "one.pdf",
                    "retrieval_source": "hybrid_local",
                }
            ],
            "retrieval_mode": "hybrid_local",
            "result_count": 1,
        },
    )

    response = main.retrieve_endpoint(
        RetrieveRequest(case_id="CASE-1", query_masked="szamlazasi kifogas", service_provider="ONE")
    )

    assert response["chunks"][0]["chunk_id"] == "one-3-1"
    assert response["request_id"]
    assert response["model_profile"]
    assert response["prompt_version"]


def test_mask_endpoint_masks_pii(tmp_path, monkeypatch) -> None:
    db_path = tmp_path / "app.db"
    monkeypatch.setattr("backend.masking.settings.sqlite_path", str(db_path))
    monkeypatch.setattr("config.settings.settings.sqlite_path", str(db_path))

    response = main.mask(
        MaskRequest(case_id="CASE-2", text="Írj a ugyfelszolgalat@one.hu címre.")
    )

    assert "[MASK_EMAIL_1]" in response["masked_text"]
    assert response["token_count"] >= 1


def test_unmask_endpoint_restores_masked_text(tmp_path, monkeypatch) -> None:
    db_path = tmp_path / "app.db"
    monkeypatch.setattr("backend.masking.settings.sqlite_path", str(db_path))
    monkeypatch.setattr("config.settings.settings.sqlite_path", str(db_path))
    main.mask(MaskRequest(case_id="CASE-3", text="Email: test.poc@example.invalid"))

    response = main.unmask(
        UnmaskRequest(case_id="CASE-3", body_masked="Email: [MASK_EMAIL_1]", role="ui")
    )

    assert response["body_unmasked"] == "Email: test.poc@example.invalid"


def test_eval_run_endpoint_returns_metrics(monkeypatch) -> None:
    monkeypatch.setattr(
        main,
        "run_eval",
        lambda limit=10: {"evaluated": 2, "category_accuracy": 1.0, "retrieval_support": 0.5, "results": []},
    )

    response = main.eval_run(EvalRequest(limit=2))

    assert response["evaluated"] == 2
    assert response["category_accuracy"] == 1.0


def test_reindex_endpoint_delegates(monkeypatch) -> None:
    monkeypatch.setattr(
        main,
        "run_reindex",
        lambda force=False: {
            "aszf_version": "2026-06-05",
            "indexed_docs": 32,
            "indexed_chunks": 100,
            "indexed_qdrant_chunks": 0,
            "parsed_pages": 10,
            "qdrant_status": "skipped",
            "derive_report": {},
            "force": force,
            "started_at": "t0",
            "finished_at": "t1",
        },
    )

    response = main.reindex(ReindexRequest(force=True))

    assert response["indexed_docs"] == 32
    assert response["force"] is True
