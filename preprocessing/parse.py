from __future__ import annotations

import argparse
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import fitz

from preprocessing.manifest import DEFAULT_OUTPUT_PATH, build_manifest, write_manifest


DEFAULT_PAGES_OUTPUT = Path("data/processed/parsed_pages.jsonl")
DEFAULT_CHUNKS_OUTPUT = Path("data/processed/chunks.jsonl")

SECTION_PATTERN = re.compile(
    r"(?m)^\s*(?P<section>(?:\d+(?:\.\d+){0,4}|[IVXLCDM]+)\.?\s+.+|(?:\d+\.\s*)?[§]\s*\d+.*)$"
)
CROSS_REF_PATTERN = re.compile(
    r"(?i)(?:\d+(?:\.\d+){1,4}\s*(?:pont|bekezdés|bekezdes)|\d+\s*§|[IVXLCDM]+\.\s*(?:fejezet|pont))"
)


@dataclass
class ParsedPage:
    doc_id: str
    page_number: int
    text: str


@dataclass
class Chunk:
    chunk_id: str
    doc_id: str
    szolgaltato: str
    dok_tipus: str
    dok_cim: str
    paragrafus_szam: str | None
    szulo_szakasz: str | None
    oldalszam: int
    cross_refs: list[str]
    source_file: str
    text: str


def load_manifest(path: Path) -> dict[str, Any]:
    if not path.exists():
        items = build_manifest()
        write_manifest(items, path)
    return json.loads(path.read_text(encoding="utf-8"))


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as file:
        for row in rows:
            file.write(json.dumps(row, ensure_ascii=False) + "\n")


def parse_pdf_text(document: dict[str, Any]) -> list[ParsedPage]:
    pdf_path = Path(document["local_path"])
    pages: list[ParsedPage] = []
    with fitz.open(pdf_path) as pdf:
        for index, page in enumerate(pdf, start=1):
            pages.append(
                ParsedPage(
                    doc_id=document["doc_id"],
                    page_number=index,
                    text=page.get_text("text").strip(),
                )
            )
    return pages


def extract_section_title(text: str) -> str | None:
    for line in text.splitlines():
        stripped = line.strip()
        if stripped:
            return stripped[:200]
    return None


def extract_paragraph_number(section_title: str | None) -> str | None:
    if not section_title:
        return None
    match = re.match(r"^\s*(?P<num>\d+(?:\.\d+){0,4}|§\s*\d+|\d+\s*§)", section_title)
    return match.group("num") if match else None


def split_page_to_sections(page_text: str) -> list[tuple[str | None, str]]:
    matches = list(SECTION_PATTERN.finditer(page_text))
    if not matches:
        return [(None, page_text.strip())] if page_text.strip() else []

    sections: list[tuple[str | None, str]] = []
    if matches[0].start() > 0:
        preamble = page_text[: matches[0].start()].strip()
        if preamble:
            sections.append((None, preamble))

    for idx, match in enumerate(matches):
        start = match.start()
        end = matches[idx + 1].start() if idx + 1 < len(matches) else len(page_text)
        section_text = page_text[start:end].strip()
        sections.append((match.group("section").strip(), section_text))
    return sections


def extract_cross_refs(text: str) -> list[str]:
    refs = {match.group(0).strip() for match in CROSS_REF_PATTERN.finditer(text)}
    return sorted(refs)


def chunk_pages(document: dict[str, Any], pages: list[ParsedPage]) -> list[Chunk]:
    chunks: list[Chunk] = []
    for page in pages:
        for section_index, (section_title, section_text) in enumerate(split_page_to_sections(page.text), start=1):
            if not section_text:
                continue
            resolved_title = section_title or extract_section_title(section_text)
            chunk_id = f"{document['doc_id']}_p{page.page_number:04d}_s{section_index:03d}"
            chunks.append(
                Chunk(
                    chunk_id=chunk_id,
                    doc_id=document["doc_id"],
                    szolgaltato=document["szolgaltato"],
                    dok_tipus=document["dok_tipus"],
                    dok_cim=document["dok_cim"],
                    paragrafus_szam=extract_paragraph_number(resolved_title),
                    szulo_szakasz=resolved_title,
                    oldalszam=page.page_number,
                    cross_refs=extract_cross_refs(section_text),
                    source_file=document["local_path"],
                    text=section_text,
                )
            )
    return chunks


def parse_and_chunk(
    manifest_path: Path = DEFAULT_OUTPUT_PATH,
    pages_output: Path = DEFAULT_PAGES_OUTPUT,
    chunks_output: Path = DEFAULT_CHUNKS_OUTPUT,
) -> tuple[int, int]:
    manifest = load_manifest(manifest_path)
    all_pages: list[ParsedPage] = []
    all_chunks: list[Chunk] = []

    for document in manifest.get("documents", []):
        pages = parse_pdf_text(document)
        all_pages.extend(pages)
        all_chunks.extend(chunk_pages(document, pages))

    write_jsonl(pages_output, [asdict(page) for page in all_pages])
    write_jsonl(chunks_output, [asdict(chunk) for chunk in all_chunks])
    return len(all_pages), len(all_chunks)


def main() -> None:
    parser = argparse.ArgumentParser(description="Parse local ASZF PDFs and create hierarchical chunks.")
    parser.add_argument("--manifest", default=str(DEFAULT_OUTPUT_PATH))
    parser.add_argument("--pages-output", default=str(DEFAULT_PAGES_OUTPUT))
    parser.add_argument("--chunks-output", default=str(DEFAULT_CHUNKS_OUTPUT))
    args = parser.parse_args()

    page_count, chunk_count = parse_and_chunk(
        manifest_path=Path(args.manifest),
        pages_output=Path(args.pages_output),
        chunks_output=Path(args.chunks_output),
    )
    print(f"Parsed {page_count} page(s), wrote {chunk_count} chunk(s).")


if __name__ == "__main__":
    main()
