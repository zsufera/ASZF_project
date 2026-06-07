from backend import main
from backend.main import RetrieveRequest


def test_retrieve_endpoint_returns_source_grounded_chunks(monkeypatch) -> None:
    monkeypatch.setattr(
        main,
        "retrieve",
        lambda **kwargs: {
            "chunks": [
                {
                    "chunk_id": "one-3-1",
                    "quote": "A számlázási kifogást az ügyfélszolgálat kivizsgálja.",
                    "score": 0.9,
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
        RetrieveRequest(
            case_id="CASE-1",
            query_masked="számlázási kifogás",
            service_provider="ONE",
        )
    )

    assert response["chunks"][0]["chunk_id"] == "one-3-1"
    assert response["chunks"][0]["quote"] == "A számlázási kifogást az ügyfélszolgálat kivizsgálja."
    assert response["chunks"][0]["dok_tipus"] == "ÁSZF"
    assert response["chunks"][0]["paragrafus"] == "3.1"
