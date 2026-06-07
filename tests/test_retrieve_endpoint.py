from backend import main
from backend.main import RetrieveRequest


def test_retrieve_endpoint_returns_source_grounded_chunks(monkeypatch) -> None:
    monkeypatch.setattr(
        main,
        "load_chunks",
        lambda: [
            {
                "chunk_id": "one-3-1",
                "szolgaltato": "ONE",
                "dok_tipus": "ÁSZF",
                "dok_cim": "ONE ÁSZF",
                "paragrafus_szam": "3.1",
                "oldalszam": 12,
                "cross_refs": [],
                "text": "A számlázási kifogást az ügyfélszolgálat kivizsgálja.",
            },
            {
                "chunk_id": "invitech-3-1",
                "szolgaltato": "Invitech",
                "dok_tipus": "ÁSZF",
                "dok_cim": "Invitech ÁSZF",
                "paragrafus_szam": "3.1",
                "oldalszam": 9,
                "cross_refs": [],
                "text": "A számlázási kifogás másik szolgáltatóhoz tartozik.",
            },
        ],
    )

    response = main.retrieve(
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
