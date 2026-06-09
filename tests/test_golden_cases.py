import pytest

from agent.runner import run_agent


GOLDEN = [
    ("szamla", "Tul magas a havi szamlam, kerem nezzek meg.", "szamlazas"),
    ("hiba", "Napok ota nincs internetem, allandoan szakad.", "hibabejelentes_szolgaltataskieses"),
    (
        "felmondas",
        "Fel szeretnem mondani a szerzodesemet, mennyi a felmondasi ido?",
        "szerzodesfelmondas_modositas",
    ),
]


@pytest.mark.parametrize("name,text,expected_category", GOLDEN)
def test_golden_case_category_and_timeline(name, text, expected_category):
    out = run_agent(case_id=f"GOLD-{name}", channel="email", input_text=text)
    assert out["classification"]["category"] == expected_category
    steps = [t["step"] for t in out["timeline"]]
    assert "classify" in steps and "draft" in steps and "verify" in steps


def test_golden_insufficient_path_sets_insufficient_mode():
    out = run_agent(case_id="GOLD-insuff", channel="email", input_text="zzz qqq xyz")
    assert out["draft"]["generation_mode"] in {"insufficient", "template"}
