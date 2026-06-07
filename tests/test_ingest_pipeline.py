import json
from pathlib import Path

import fitz

from preprocessing.parse import parse_and_chunk
from preprocessing.index import load_chunks, search_chunks


def create_fixture_pdf(path: Path) -> None:
    document = fitz.open()
    page = document.new_page()
    page.insert_text(
        (72, 72),
        "1. Szamlazasi kifogas\n"
        "A szamlazasi kifogast az ugyfelszolgalat kivizsgalja.\n"
        "A 2.1 pont szerint az ugyfel tajekoztatast kap.",
    )
    document.save(path)
    document.close()


def test_pdf_to_chunks_to_retrieve_smoke(tmp_path: Path) -> None:
    pdf_path = tmp_path / "one_aszf_fixture.pdf"
    manifest_path = tmp_path / "ingest_manifest.json"
    pages_output = tmp_path / "parsed_pages.jsonl"
    chunks_output = tmp_path / "chunks.jsonl"
    create_fixture_pdf(pdf_path)

    manifest_path.write_text(
        json.dumps(
            {
                "generated_at": "2026-01-01T00:00:00Z",
                "document_count": 1,
                "documents": [
                    {
                        "doc_id": "doc-fixture",
                        "local_path": pdf_path.as_posix(),
                        "sha256": "fixture",
                        "file_name": pdf_path.name,
                        "source_url": None,
                        "szolgaltato": "ONE",
                        "dok_tipus": "ÁSZF",
                        "dok_cim": "Fixture ÁSZF",
                        "version_hint": None,
                        "discovered_at": "2026-01-01T00:00:00Z",
                    }
                ],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    page_count, chunk_count = parse_and_chunk(
        manifest_path=manifest_path,
        pages_output=pages_output,
        chunks_output=chunks_output,
    )
    results = search_chunks(
        query="szamlazasi kifogas",
        chunks=load_chunks(chunks_output),
        service_provider="ONE",
    )

    assert page_count == 1
    assert chunk_count >= 1
    assert results
    assert results[0]["chunk_id"].startswith("doc-fixture")
    assert results[0]["dok_tipus"] == "ÁSZF"
    assert results[0]["szolgaltato"] == "ONE"
