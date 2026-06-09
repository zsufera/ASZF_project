from fastapi.testclient import TestClient

from backend.db import init_db
from backend.main import app


def test_knowledge_browser_contract(tmp_path, monkeypatch) -> None:
    db_path = tmp_path / "tier3.db"
    monkeypatch.setattr("config.settings.settings.sqlite_path", str(db_path))
    monkeypatch.setattr("backend.case_service.settings.sqlite_path", str(db_path))
    monkeypatch.setattr("backend.auth.settings.sqlite_path", str(db_path))
    init_db()

    chunks = [
        {
            "chunk_id": "chunk-1",
            "dok_tipus": "ASZF",
            "dok_cim": "Torzsszoveg",
            "paragrafus_szam": "5.5.1",
            "text": "A szamlazasi panasz kivizsgalasanak hatarideje harminc nap.",
            "cross_refs": ["7.2.3"],
            "oldalszam": 12,
        },
        {
            "chunk_id": "chunk-2",
            "dok_tipus": "ASZF",
            "dok_cim": "Torzsszoveg",
            "paragrafus_szam": "7.2.3",
            "text": "A dijemelesrol ertesitest kell kuldeni.",
            "cross_refs": [],
            "oldalszam": 20,
        },
    ]
    monkeypatch.setattr("backend.knowledge_service.load_knowledge_chunks", lambda: chunks)

    with TestClient(app) as client:
        tree = client.get("/aszf/tree")
        assert tree.status_code == 200
        assert tree.json()["items"][0]["section"] == "5"

        section = client.get("/aszf/section/chunk-1")
        assert section.status_code == 200
        assert section.json()["item"]["chunk_id"] == "chunk-1"
        assert section.json()["item"]["cross_refs"] == ["7.2.3"]

        search = client.get("/aszf/search", params={"q": "dijemeles"})
        assert search.status_code == 200
        assert search.json()["items"][0]["chunk_id"] == "chunk-2"
