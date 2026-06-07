from backend.main import PolicyMapRequest, policy_map


def test_policy_map_endpoint_returns_policy_items() -> None:
    response = policy_map(
        PolicyMapRequest(
            case_id="CASE-1",
            category="szamlazas",
            chunks=[
                {
                    "chunk_id": "one-3-1",
                    "dok_tipus": "ÁSZF",
                    "paragrafus": "3.1",
                    "quote": "A számlázási kifogást az ügyfélszolgálat kivizsgálja.",
                    "score": 1.0,
                    "dok_cim": "ONE ÁSZF",
                    "oldalszam": 12,
                }
            ],
        )
    )

    assert response["request_id"] == "stub"
    assert response["policy_items"][0]["chunk_id"] == "one-3-1"
    assert response["mandatory_refs"] == ["A szamlazasi szabalyok relevans paragrafusai"]
