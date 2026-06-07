from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

from preprocessing.index import load_chunks, quote_text, search_chunks


DEFAULT_CHUNKS_PATH = Path("data/processed/chunks.jsonl")
DEFAULT_DERIVED_DIR = Path("data/derived")
DEFAULT_POLICIES_PATH = Path("config/policies.yaml")
DEFAULT_MANDATORY_REFS_PATH = Path("config/mandatory_refs.yaml")
DEFAULT_DISCLAIMER_PATH = Path("config/disclaimer.yaml")

CATEGORY_QUERIES: dict[str, tuple[str, ...]] = {
    "szamlazas": ("számlázás", "szamlazas", "számla", "fizetési határidő", "számlázási kifogás"),
    "dijemeles": ("díjemelés", "dijemeles", "díjmódosítás", "áremelés", "díjkorrekció"),
    "hibabejelentes_szolgaltataskieses": (
        "hibabejelentés",
        "szolgáltatáskiesés",
        "kiesés",
        "helyreállítás",
        "SLA",
    ),
    "szerzodesfelmondas_modositas": ("felmondás", "szerződésmódosítás", "előfizetői szerződés", "megszűnés"),
    "lefedettseg": ("lefedettség", "szolgáltatási terület", "elérhetőség", "földrajzi"),
    "eszkoz_keszulek": ("médiaeszköz", "berendezés", "modem", "visszaszolgáltatás", "készülék"),
    "adatvedelem": ("adatvédelem", "személyes adat", "adatkezelés", "GDPR", "érintett"),
}

ESCALATION_QUERIES: dict[str, tuple[str, ...]] = {
    "egyedi_szerzodes_gyanu": ("egyedi előfizetői szerződés", "egyedi szerződés", "eltérő feltétel"),
    "vitatott_osszeg": ("vitatott összeg", "jogvit", "követelés", "visszatérítés"),
    "ismetlodo_panasz": ("ismétlődő panasz", "ismételt panasz", "újbóli bejelentés"),
    "jogi_hatosagi_media": ("hatóság", "bíróság", "NMHH", "fogyasztóvédelem", "média"),
    "sla_kozel_lejarat": ("határidő", "30 nap", "válaszadási kötelezettség", "SLA"),
}

DISCLAIMER_QUERIES: tuple[str, ...] = (
    "tájékoztató jelleg",
    "nem minősül",
    "állásfoglalás",
    "egyoldalú módosítás",
    "tájékoztatás",
)


def pick_best_chunk(chunks: list[dict[str, Any]], query_terms: tuple[str, ...]) -> dict[str, Any] | None:
    query = " ".join(query_terms)
    results = search_chunks(query=query, chunks=chunks, limit=5)
    if results:
        return results[0]
    lowered_terms = [term.lower() for term in query_terms]
    for chunk in chunks:
        text = chunk.get("text", "").lower()
        if any(term in text for term in lowered_terms):
            return {
                "chunk_id": chunk.get("chunk_id"),
                "paragrafus": chunk.get("paragrafus_szam"),
                "quote": quote_text(chunk.get("text", "")),
                "dok_cim": chunk.get("dok_cim"),
                "oldalszam": chunk.get("oldalszam"),
                "szolgaltato": chunk.get("szolgaltato"),
            }
    return None


def build_mandatory_label(chunk: dict[str, Any], category: str) -> str:
    paragraph = chunk.get("paragrafus") or chunk.get("paragrafus_szam")
    dok_cim = chunk.get("dok_cim") or "forrás"
    if paragraph:
        return f"{paragraph} — {dok_cim} ({category})"
    return f"{dok_cim} ({category})"


def derive_mandatory_refs(chunks: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    mandatory_by_category: dict[str, list[dict[str, Any]]] = {}
    for category, terms in CATEGORY_QUERIES.items():
        chunk = pick_best_chunk(chunks, terms)
        if not chunk:
            continue
        mandatory_by_category[category] = [
            {
                "label": build_mandatory_label(chunk, category),
                "chunk_id": chunk.get("chunk_id"),
                "paragrafus": chunk.get("paragrafus"),
                "idezet": chunk.get("quote", ""),
                "dok_cim": chunk.get("dok_cim"),
                "oldalszam": chunk.get("oldalszam"),
                "szolgaltato": chunk.get("szolgaltato"),
            }
        ]
    return mandatory_by_category


def derive_escalation_triggers(chunks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    triggers: list[dict[str, Any]] = []
    for trigger_name, terms in ESCALATION_QUERIES.items():
        chunk = pick_best_chunk(chunks, terms)
        if not chunk:
            continue
        triggers.append(
            {
                "nev": trigger_name,
                "leiras": f"A forrás alapján eszkalációt indokolhat: {trigger_name.replace('_', ' ')}",
                "chunk_id": chunk.get("chunk_id"),
                "idezet": chunk.get("quote", ""),
                "paragrafus": chunk.get("paragrafus"),
                "dok_cim": chunk.get("dok_cim"),
            }
        )
    return triggers


def derive_disclaimer_draft(chunks: list[dict[str, Any]], existing_text: str) -> dict[str, Any]:
    chunk = pick_best_chunk(chunks, DISCLAIMER_QUERIES)
    draft = (
        "Ez a válasz AI-támogatással készült tájékoztató jellegű draft. "
        "A végleges ügyintézői állásfoglalást és az egyedi ügyre vonatkozó döntést "
        "emberi felülvizsgálat után lehet érvényesnek tekinteni."
    )
    if existing_text.strip():
        draft = existing_text.strip()
    provenance = None
    if chunk:
        provenance = {
            "chunk_id": chunk.get("chunk_id"),
            "idezet": chunk.get("quote", ""),
            "paragrafus": chunk.get("paragrafus"),
            "dok_cim": chunk.get("dok_cim"),
        }
    return {"disclaimer_draft": draft, "provenance": provenance}


def load_existing_disclaimer(path: Path) -> str:
    if not path.exists():
        return ""
    payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return str(payload.get("text_hu", "")).strip()


def write_yaml(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(payload, allow_unicode=True, sort_keys=False), encoding="utf-8")


def derive_all(
    chunks_path: Path = DEFAULT_CHUNKS_PATH,
    derived_dir: Path = DEFAULT_DERIVED_DIR,
    policies_path: Path = DEFAULT_POLICIES_PATH,
    mandatory_refs_path: Path = DEFAULT_MANDATORY_REFS_PATH,
    disclaimer_path: Path = DEFAULT_DISCLAIMER_PATH,
) -> dict[str, Any]:
    chunks = load_chunks(chunks_path)
    if not chunks:
        raise FileNotFoundError(f"No chunks found at {chunks_path}. Run preprocessing.parse first.")

    mandatory_by_category = derive_mandatory_refs(chunks)
    escalation_details = derive_escalation_triggers(chunks)
    disclaimer = derive_disclaimer_draft(chunks, load_existing_disclaimer(disclaimer_path))

    existing_policies = yaml.safe_load(policies_path.read_text(encoding="utf-8")) if policies_path.exists() else {}
    policies_payload = {
        "confidence_threshold": existing_policies.get("confidence_threshold", 0.75),
        "sla_fallback_days": existing_policies.get("sla_fallback_days", 30),
        "escalation_triggers": [item["nev"] for item in escalation_details]
        or existing_policies.get("escalation_triggers", []),
        "escalation_trigger_details": escalation_details,
        "derived_at": datetime.now(timezone.utc).isoformat(),
        "source_chunks": chunks_path.as_posix(),
    }

    mandatory_payload = {
        "mandatory_by_category": mandatory_by_category,
        "derived_at": datetime.now(timezone.utc).isoformat(),
        "source_chunks": chunks_path.as_posix(),
    }

    disclaimer_payload = {
        "automata_required": True,
        "text_hu": disclaimer["disclaimer_draft"],
        "provenance": disclaimer.get("provenance"),
        "derived_at": datetime.now(timezone.utc).isoformat(),
        "source_chunks": chunks_path.as_posix(),
    }

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "chunk_count": len(chunks),
        "mandatory_ref_categories": len(mandatory_by_category),
        "escalation_trigger_count": len(escalation_details),
        "mandatory_by_category": mandatory_by_category,
        "escalation_trigger_details": escalation_details,
        "disclaimer": disclaimer,
    }

    derived_dir.mkdir(parents=True, exist_ok=True)
    report_path = derived_dir / "derive_report.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    write_yaml(policies_path, policies_payload)
    write_yaml(mandatory_refs_path, mandatory_payload)
    write_yaml(disclaimer_path, disclaimer_payload)
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description="Derive policy YAMLs from indexed ASZF chunks.")
    parser.add_argument("--chunks", default=str(DEFAULT_CHUNKS_PATH))
    parser.add_argument("--derived-dir", default=str(DEFAULT_DERIVED_DIR))
    parser.add_argument("--policies", default=str(DEFAULT_POLICIES_PATH))
    parser.add_argument("--mandatory-refs", default=str(DEFAULT_MANDATORY_REFS_PATH))
    parser.add_argument("--disclaimer", default=str(DEFAULT_DISCLAIMER_PATH))
    args = parser.parse_args()

    report = derive_all(
        chunks_path=Path(args.chunks),
        derived_dir=Path(args.derived_dir),
        policies_path=Path(args.policies),
        mandatory_refs_path=Path(args.mandatory_refs),
        disclaimer_path=Path(args.disclaimer),
    )
    print(
        "Derived params: "
        f"{report['mandatory_ref_categories']} mandatory categories, "
        f"{report['escalation_trigger_count']} escalation triggers. "
        f"Report: data/derived/derive_report.json"
    )


if __name__ == "__main__":
    main()
