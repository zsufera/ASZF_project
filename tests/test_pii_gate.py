import re

from backend.masking import mask_text


EMAIL_PATTERN = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")


def test_masked_prompt_contains_no_raw_email(tmp_path, monkeypatch) -> None:
    db_path = tmp_path / "pii.db"
    monkeypatch.setattr("backend.masking.settings.sqlite_path", str(db_path))
    raw = "Kapcsolat: kovacs.anna.poc@example.invalid telefonon."
    masked = mask_text("CASE-PII-GATE", raw)["masked_text"]
    assert "kovacs.anna.poc@example.invalid" not in masked
    assert EMAIL_PATTERN.search(masked) is None
    assert "[MASK_EMAIL_" in masked
