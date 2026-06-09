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

# text-embedding-3-large uses cl100k_base; hard limit is 8192 tokens.
# We target 7500 tokens (~8% headroom) so sub-chunks never hit the API limit.
MAX_CHUNK_TOKENS = 7_500

SECTION_PATTERN = re.compile(
    r"(?m)^[ \t]*(?P<section>"
    r"(?:\d+\.\s+[^\r\n]+)"
    r"|(?:\d+\.\d+(?:\.\d+){0,4}\.?\s+[^\r\n]+)"
    r"|(?:[IVXLCDM]+\.\s+[^\r\n]+)"
    r"|(?:(?:\d+\.\s*)?[§]\s*\d+[^\r\n]*)"
    r")[ \t]*$"
)
CROSS_REF_PATTERN = re.compile(
    r"(?i)(?:\d+(?:\.\d+){1,4}\s*(?:pont|bekezdés|bekezdes)|\d+\s*§|[IVXLCDM]+\.\s*(?:fejezet|pont))"
)
DOC_REF_PATTERN = re.compile(
    r"(?i)(?P<doc>\d+\s*[ab]?(?:/[ab])?\.?\s*sz[áa]m[úu]?\s*(?:mell[ée]klet|f[üu]ggel[ée]k))"
    r"(?:e?\s*(?P<para>\d+(?:\.\d+){0,4})\s*(?:pont|bekezd[ée]s))?"
)
LOCAL_REF_PATTERN = re.compile(
    r"(?i)(?P<p1>\d+(?:\.\d+){1,4})\s*(?:pont|bekezd[ée]s)|(?P<p2>\d+)\s*§|"
    r"(?P<rom>[IVXLCDM]+)\.\s*(?:fejezet|pont)"
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
    cross_refs: list[dict]
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
    match = re.match(r"^\s*(?P<num>\d+(?:\.\d+){0,5}|§\s*\d+|\d+\s*§)", section_title)
    return match.group("num") if match else None


def _looks_like_table_page(page_text: str) -> bool:
    lines = [line.strip() for line in page_text.splitlines() if line.strip()]
    if len(lines) < 8:
        return False
    folded_lines = [line.casefold() for line in lines]
    table_terms = (
        "sorszám",
        "sorszam",
        "csatorna",
        "díj",
        "dij",
        "ár",
        "ar",
        "nettó",
        "netto",
        "bruttó",
        "brutto",
        "csomag",
        "program",
        "jelleg",
        "felbontás",
        "felbontas",
    )
    has_table_vocabulary = any(
        term in line for line in folded_lines for term in table_terms
    )
    if not has_table_vocabulary:
        return False

    numeric_only = sum(bool(re.fullmatch(r"\d{1,4}\.?", line)) for line in lines)
    short_lines = sum(len(line) <= 32 for line in lines)
    return numeric_only >= 5 and (
        numeric_only / len(lines) >= 0.18 or short_lines / len(lines) >= 0.75
    )


def split_page_to_sections(page_text: str) -> list[tuple[str | None, str]]:
    if _looks_like_table_page(page_text):
        return [(None, page_text.strip())] if page_text.strip() else []

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


def extract_references(text: str) -> list[dict]:
    """Strukturált hivatkozások a szövegből: lokális §/pont és kereszt-dok melléklet/függelék.

    Visszatérés elemei: {"raw": str, "doc_hint": str|None, "paragraph": str|None}.
    A doc_hint None, ha a hivatkozás a saját dokumentumra mutat.
    """
    refs: list[dict] = []
    seen: set[tuple] = set()

    def _add(doc_hint: str | None, paragraph: str | None, raw: str) -> None:
        key = (doc_hint, paragraph)
        if key in seen or (doc_hint is None and paragraph is None):
            return
        seen.add(key)
        refs.append({"raw": " ".join(raw.split()), "doc_hint": doc_hint, "paragraph": paragraph})

    for match in DOC_REF_PATTERN.finditer(text):
        doc = " ".join(match.group("doc").split())
        _add(doc, match.group("para"), match.group(0))
    for match in LOCAL_REF_PATTERN.finditer(text):
        paragraph = match.group("p1") or match.group("p2")
        if paragraph:
            _add(None, paragraph, match.group(0))
    return refs


# Visszafelé-kompatibilis alias (régi hívók / smoke).
def extract_cross_refs(text: str) -> list[dict]:
    return extract_references(text)


def _tokenize(text: str) -> list[int]:
    import tiktoken
    return tiktoken.get_encoding("cl100k_base").encode(text)


def _decode_tokens(tokens: list[int]) -> str:
    import tiktoken
    return tiktoken.get_encoding("cl100k_base").decode(tokens)


def _split_text(text: str, max_tokens: int) -> list[str]:
    """Split text at paragraph/line boundaries so each part stays under max_tokens tokens."""
    tokens = _tokenize(text)
    if len(tokens) <= max_tokens:
        return [text]

    parts: list[str] = []
    current_tokens: list[int] = []

    def _flush() -> None:
        if current_tokens:
            parts.append(_decode_tokens(current_tokens))

    for para in re.split(r"\n\n+", text):
        para_tokens = _tokenize(para)
        if len(current_tokens) + len(para_tokens) <= max_tokens:
            current_tokens.extend(para_tokens)
            continue
        _flush()
        current_tokens = []
        if len(para_tokens) <= max_tokens:
            current_tokens = para_tokens
            continue
        # Paragraph itself is too long — split at line boundaries
        for line in para.splitlines():
            line_tokens = _tokenize(line)
            if len(current_tokens) + len(line_tokens) <= max_tokens:
                current_tokens.extend(line_tokens)
                continue
            _flush()
            current_tokens = []
            if len(line_tokens) <= max_tokens:
                current_tokens = line_tokens
                continue
            # Single line still too long — hard-split on token boundary
            for i in range(0, len(line_tokens), max_tokens):
                parts.append(_decode_tokens(line_tokens[i : i + max_tokens]))

    _flush()
    return [p for p in parts if p.strip()]


def _maybe_split_chunk(chunk: Chunk, max_tokens: int = MAX_CHUNK_TOKENS) -> list[Chunk]:
    """Return chunk unchanged if within token limit, otherwise sub-split preserving all metadata."""
    if len(_tokenize(chunk.text)) <= max_tokens:
        return [chunk]
    sub_texts = _split_text(chunk.text, max_tokens)
    return [
        Chunk(
            chunk_id=f"{chunk.chunk_id}_sub{idx:03d}",
            doc_id=chunk.doc_id,
            szolgaltato=chunk.szolgaltato,
            dok_tipus=chunk.dok_tipus,
            dok_cim=chunk.dok_cim,
            paragrafus_szam=chunk.paragrafus_szam,
            szulo_szakasz=chunk.szulo_szakasz,
            oldalszam=chunk.oldalszam,
            cross_refs=chunk.cross_refs,
            source_file=chunk.source_file,
            text=part,
        )
        for idx, part in enumerate(sub_texts, start=1)
    ]


def chunk_pages(document: dict[str, Any], pages: list[ParsedPage]) -> list[Chunk]:
    chunks: list[Chunk] = []
    for page in pages:
        for section_index, (section_title, section_text) in enumerate(split_page_to_sections(page.text), start=1):
            if not section_text:
                continue
            resolved_title = section_title or extract_section_title(section_text)
            chunk_id = f"{document['doc_id']}_p{page.page_number:04d}_s{section_index:03d}"
            base_chunk = Chunk(
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
            chunks.extend(_maybe_split_chunk(base_chunk))
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
