from backend.classify import classify_message


def test_classify_message_detects_billing_complaint() -> None:
    result = classify_message(
        message_text_masked="Hibás számla miatt szeretnék panaszt tenni.",
        history_summary_masked=None,
    )

    assert result["category"] == "szamlazas"
    assert result["confidence"] >= 0.7
    assert result["is_repeated"] is False


def test_classify_message_distinguishes_price_increase_from_escalation() -> None:
    result = classify_message(
        message_text_masked="A díjemelés mértékét vitatom, kérem a tájékoztatást.",
        history_summary_masked=None,
    )

    assert result["category"] == "dijemeles"
    assert result["subtype"] == "dijmodositas"


def test_classify_message_marks_repeated_from_history() -> None:
    result = classify_message(
        message_text_masked="Megint ugyanaz a szolgáltatáskiesés van.",
        history_summary_masked="Korábban ismétlődő panasz volt ugyanebben az ügyben.",
    )

    assert result["category"] == "hibabejelentes_szolgaltataskieses"
    assert result["is_repeated"] is True
