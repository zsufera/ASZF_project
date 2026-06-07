from backend.masking import mask_text, unmask_text


def test_mask_and_unmask_roundtrip(tmp_path, monkeypatch) -> None:
    db_path = tmp_path / "app.db"
    monkeypatch.setattr("backend.masking.settings.sqlite_path", str(db_path))
    monkeypatch.setattr("config.settings.settings.sqlite_path", str(db_path))

    original = "Ügyfél: Kovacs Anna, email: kovacs.anna.poc@example.invalid, tel: +36 20 123 4567"
    masked = mask_text("CASE-1", original)

    assert "[MASK_EMAIL_1]" in masked["masked_text"]
    assert "kovacs.anna.poc@example.invalid" not in masked["masked_text"]
    assert unmask_text("CASE-1", masked["masked_text"]) == original
