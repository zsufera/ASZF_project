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

    assert response["request_id"]
    assert response["prompt_version"]
    assert response["policy_items"][0]["chunk_id"] == "one-3-1"
    from backend.policy_map import load_mandatory_refs

    assert response["mandatory_refs"] == load_mandatory_refs().get("szamlazas", [])
