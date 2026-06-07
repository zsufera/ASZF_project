from __future__ import annotations

import argparse
import hashlib
import json
import re
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml


DEFAULT_CONFIG_PATH = Path("config/doc_sources.yaml")
DEFAULT_OUTPUT_PATH = Path("data/ingest_manifest.json")
DEFAULT_DOWNLOAD_METADATA_PATH = Path("data/raw_pdfs/download_metadata.json")


@dataclass
class DocumentManifestItem:
    doc_id: str
    local_path: str
    sha256: str
    file_name: str
    source_url: str | None
    szolgaltato: str
    dok_tipus: str
    dok_cim: str
    version_hint: str | None
    discovered_at: str


def load_doc_sources(config_path: Path = DEFAULT_CONFIG_PATH) -> dict[str, Any]:
    if not config_path.exists():
        raise FileNotFoundError(f"Missing doc sources config: {config_path}")
    with config_path.open("r", encoding="utf-8") as file:
        return yaml.safe_load(file) or {}


def load_download_metadata(path: Path = DEFAULT_DOWNLOAD_METADATA_PATH) -> dict[str, dict[str, Any]]:
    if not path.exists():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    return {item["file_name"]: item for item in payload.get("documents", []) if item.get("file_name")}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for block in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def infer_provider(file_name: str) -> str:
    normalized = file_name.lower()
    if "invitech" in normalized:
        return "Invitech"
    if re.search(r"ah[_\s-]?m[eé]dia|mindigtv|volt_ah", normalized):
        return "AH Media"
    if "helyi" in normalized or "eurocable" in normalized or "i-tv" in normalized:
        return "helyi_kabeles"
    return "ONE"


def infer_doc_type(file_name: str) -> str:
    normalized = file_name.lower()
    if "melleklet" in normalized or "melléklet" in normalized or "fuggelek" in normalized:
        return "melléklet"
    if any(
        token in normalized
        for token in (
            "egyeb",
            "egyéb",
            "felhasznalasi",
            "vasarlasi",
            "online_shop",
            "eszszf",
            "eszmr",
            "eszr",
            "edsz",
            "dpo",
            "tajekoztato",
        )
    ):
        return "Egyéb felhasználási feltételek"
    return "ÁSZF"


def infer_version_hint(file_name: str) -> str | None:
    match = re.search(r"(20\d{6})(?!\d)", file_name)
    if match:
        raw = match.group(1)
        return f"{raw[:4]}-{raw[4:6]}-{raw[6:8]}"
    return None


def build_manifest(config_path: Path = DEFAULT_CONFIG_PATH) -> list[DocumentManifestItem]:
    config = load_doc_sources(config_path)
    local_pdf_dir = Path(config.get("local_pdf_dir", "data/raw_pdfs"))
    metadata_by_file = {
        item.get("file_name"): item for item in config.get("local_pdf_metadata", []) if item.get("file_name")
    }
    metadata_by_file.update(load_download_metadata())
    discovered_at = datetime.now(timezone.utc).isoformat()

    items: list[DocumentManifestItem] = []
    seen_hashes: set[str] = set()

    for pdf_path in sorted(local_pdf_dir.glob("*.pdf")):
        file_hash = sha256_file(pdf_path)
        if file_hash in seen_hashes:
            continue
        seen_hashes.add(file_hash)

        file_meta = metadata_by_file.get(pdf_path.name, {})
        doc_id = f"doc_{file_hash[:16]}"
        items.append(
            DocumentManifestItem(
                doc_id=doc_id,
                local_path=pdf_path.as_posix(),
                sha256=file_hash,
                file_name=pdf_path.name,
                source_url=file_meta.get("source_url"),
                szolgaltato=file_meta.get("szolgaltato") or infer_provider(pdf_path.name),
                dok_tipus=file_meta.get("dok_tipus") or infer_doc_type(pdf_path.name),
                dok_cim=file_meta.get("dok_cim") or pdf_path.stem,
                version_hint=file_meta.get("version_hint") or infer_version_hint(pdf_path.name),
                discovered_at=discovered_at,
            )
        )

    return items


def write_manifest(items: list[DocumentManifestItem], output_path: Path = DEFAULT_OUTPUT_PATH) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "document_count": len(items),
        "documents": [asdict(item) for item in items],
    }
    output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Build ingest manifest from local PDFs.")
    parser.add_argument("--config", default=str(DEFAULT_CONFIG_PATH))
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT_PATH))
    args = parser.parse_args()

    items = build_manifest(Path(args.config))
    write_manifest(items, Path(args.output))
    print(f"Wrote {len(items)} document(s) to {args.output}")


if __name__ == "__main__":
    main()
