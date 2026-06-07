from preprocessing.download import extract_pdf_links, infer_provider_from_page, sanitize_filename


def test_extract_pdf_links_from_href_and_raw_text() -> None:
    html = '''
    <a href="/static/documents/one-aszf.pdf">ÁSZF</a>
    "https://www.one.hu/static/documents/melleklet.pdf"
    '''

    links = extract_pdf_links(html, "https://www.one.hu/aszf#aszf-one")

    assert "https://www.one.hu/static/documents/one-aszf.pdf" in links
    assert "https://www.one.hu/static/documents/melleklet.pdf" in links


def test_sanitize_filename_keeps_pdf_extension() -> None:
    assert sanitize_filename("ONE ÁSZF 2026.pdf") == "ONE_ASZF_2026.pdf"


def test_infer_provider_from_page_fragment() -> None:
    assert infer_provider_from_page("https://www.one.hu/aszf#aszf-invitech") == "Invitech"
