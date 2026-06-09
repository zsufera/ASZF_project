from preprocessing.parse import ParsedPage, chunk_pages, split_page_to_sections


DOCUMENT = {
    "doc_id": "doc-test",
    "local_path": "fixture.pdf",
    "szolgaltato": "ONE",
    "dok_tipus": "ASZF",
    "dok_cim": "Fixture ASZF",
}


def test_table_like_numeric_rows_stay_on_one_page_chunk():
    page = ParsedPage(
        doc_id="doc-test",
        page_number=1,
        text=(
            "A helyhez kotott digitalis musorterjesztesi szolgaltatasok - csatornakiosztas\n"
            "Sorszam\n"
            "Csatorna nev\n"
            "Csatorna tematika\n"
            "1\n"
            "M1 HD\n"
            "2\n"
            "M2 HD\n"
            "3\n"
            "Duna HD\n"
            "4\n"
            "M4 Sport HD\n"
            "5\n"
            "Duna World HD\n"
        ),
    )

    chunks = chunk_pages(DOCUMENT, [page])

    assert len(chunks) == 1
    assert chunks[0].paragrafus_szam is None
    assert "M1 HD" in chunks[0].text
    assert "Duna World HD" in chunks[0].text


def test_table_like_dotted_numeric_rows_stay_on_one_page_chunk():
    page = ParsedPage(
        doc_id="doc-test",
        page_number=1,
        text=(
            "Szolgaltatas csomag pontos elnevezese:\n"
            "Program\n"
            "Jelleg, profil\n"
            "Elerheto legnagyobb felbontas\n"
            "1.\n"
            "M1\n"
            "Kozszolgalati csatornak\n"
            "2.\n"
            "M1 HD\n"
            "Kozszolgalati csatornak\n"
            "3.\n"
            "M2\n"
            "Gyerekeknek\n"
            "4.\n"
            "M2 HD\n"
            "Gyerekeknek\n"
            "5.\n"
            "Duna HD\n"
            "Kozszolgalati csatornak\n"
        ),
    )

    chunks = chunk_pages(DOCUMENT, [page])

    assert len(chunks) == 1
    assert chunks[0].paragrafus_szam is None
    assert "M1 HD" in chunks[0].text


def test_decimal_legal_sections_are_split_and_numbered():
    sections = split_page_to_sections(
        "5.5.6. Szamlazasi kifogas\n"
        "A szamlazasi kifogast az ugyfelszolgalat kivizsgalja.\n\n"
        "5.5.7. Ertesites\n"
        "A Szolgaltato irasban ertesiti az elofizetot."
    )

    assert [title for title, _ in sections] == [
        "5.5.6. Szamlazasi kifogas",
        "5.5.7. Ertesites",
    ]


def test_top_level_legal_heading_requires_dot_after_number():
    sections = split_page_to_sections(
        "1. Altalanos rendelkezések\n"
        "A jelen feltetelek a szolgaltatasra vonatkoznak.\n\n"
        "2. Eljarasi szabalyok\n"
        "A Szolgaltato a bejelentest kivizsgalja."
    )

    assert [title for title, _ in sections] == [
        "1. Altalanos rendelkezések",
        "2. Eljarasi szabalyok",
    ]
