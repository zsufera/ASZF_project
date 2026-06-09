from fastapi.testclient import TestClient

import backend.serve as serve


def test_serve_spa_and_api(tmp_path, monkeypatch):
    dist = tmp_path / "dist"
    (dist / "assets").mkdir(parents=True)
    (dist / "index.html").write_text("<html>APP</html>", encoding="utf-8")
    (dist / "assets" / "app.js").write_text("console.log(1)", encoding="utf-8")

    monkeypatch.setattr(serve, "DIST", dist)
    monkeypatch.setattr(serve, "_api_startup", lambda: None)  # DB-init kihagyása a tesztben

    with TestClient(serve.app) as client:
        # SPA kliens-oldali útvonal -> index.html
        spa = client.get("/case/123")
        assert spa.status_code == 200
        assert "APP" in spa.text

        # statikus asset kiszolgálva
        asset = client.get("/assets/app.js")
        assert asset.status_code == 200
        assert "console.log" in asset.text

        # API elérhető /api alatt (a mount levágja a prefixet -> /health)
        api = client.get("/api/health")
        assert api.status_code == 200
        assert api.json()["status"] == "ok"


def test_serve_404_when_no_build(tmp_path, monkeypatch):
    monkeypatch.setattr(serve, "DIST", tmp_path / "missing_dist")
    monkeypatch.setattr(serve, "_api_startup", lambda: None)
    with TestClient(serve.app) as client:
        r = client.get("/anything")
        assert r.status_code == 404
        assert "npm run build" in r.json()["detail"]
