from preprocessing.gen_emails import SAMPLE_EMAILS, write_catalog


def test_write_catalog_creates_versioned_emails(tmp_path) -> None:
    manifest = write_catalog(tmp_path)

    assert manifest["email_count"] == len(SAMPLE_EMAILS)
    assert manifest["catalog_version"]
    assert (tmp_path / "catalog.json").exists()
    assert (tmp_path / "email-001-szamlazas-one.json").exists()


def test_sample_emails_cover_main_and_edge_cases() -> None:
    categories = {email.varht_kategoria for email in SAMPLE_EMAILS}
    edge_cases = {email.edge_case for email in SAMPLE_EMAILS if email.edge_case}

    assert "szamlazas" in categories
    assert "dijemeles" in categories
    assert "prompt_injection" in edge_cases
    assert "nem_panasz" in edge_cases
    assert len(SAMPLE_EMAILS) >= 14
