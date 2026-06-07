import json
from pathlib import Path

from preprocessing.derive_params import derive_all


def _write_chunks(path: Path) -> None:
    rows = [
        {
            "chunk_id": "doc-billing",
            "szolgaltato": "ONE",
            "dok_tipus": "ÁSZF",
            "dok_cim": "ONE ÁSZF",
            "paragrafus_szam": "5.1",
            "oldalszam": 10,
            "text": "A számlázási kifogást az ügyfélszolgálat kivizsgálja és 30 napon belül válaszol.",
        },
        {
            "chunk_id": "doc-escalation",
            "szolgaltato": "ONE",
            "dok_tipus": "ÁSZF",
            "dok_cim": "ONE ÁSZF",
            "paragrafus_szam": "7.2",
            "oldalszam": 20,
            "text": "Vitátott összeg esetén az ügyintéző eszkalálja az ügyet a supervisorhoz.",
        },
        {
            "chunk_id": "doc-disclaimer",
            "szolgaltato": "ONE",
            "dok_tipus": "ÁSZF",
            "dok_cim": "ONE ÁSZF",
            "paragrafus_szam": "1.3",
            "oldalszam": 2,
            "text": "A tájékoztató jellegű közlés nem minősül kötelező érvényű állásfoglalásnak.",
        },
    ]
    path.write_text(
        "\n".join(json.dumps(row, ensure_ascii=False) for row in rows) + "\n",
        encoding="utf-8",
    )


def test_derive_all_writes_provenance_configs(tmp_path: Path) -> None:
    chunks_path = tmp_path / "chunks.jsonl"
    derived_dir = tmp_path / "derived"
    policies_path = tmp_path / "policies.yaml"
    mandatory_refs_path = tmp_path / "mandatory_refs.yaml"
    disclaimer_path = tmp_path / "disclaimer.yaml"
    _write_chunks(chunks_path)

    report = derive_all(
        chunks_path=chunks_path,
        derived_dir=derived_dir,
        policies_path=policies_path,
        mandatory_refs_path=mandatory_refs_path,
        disclaimer_path=disclaimer_path,
    )

    assert report["mandatory_ref_categories"] >= 1
    assert report["escalation_trigger_count"] >= 1
    assert (derived_dir / "derive_report.json").exists()
    assert "szamlazas" in report["mandatory_by_category"]
    assert report["mandatory_by_category"]["szamlazas"][0]["chunk_id"] == "doc-billing"
