from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable


@dataclass
class DemoScenario:
    scenario_id: str
    title: str
    description: str
    email_id: str | None
    channel: str
    input_text: str | None
    service_provider: str | None
    output_mode: str
    sla_expired: bool
    assertions: Callable[[dict[str, Any]], list[str]]


def _assert_szamlazas(result: dict[str, Any]) -> list[str]:
    failures: list[str] = []
    if result.get("classification", {}).get("category") != "szamlazas":
        failures.append("várt kategória: szamlazas")
    if not result.get("draft", {}).get("body_masked"):
        failures.append("hiányzó draft")
    if not result.get("retrieval", {}).get("chunks"):
        failures.append("hiányzó forrás")
    return failures


def _assert_eszkalacio(result: dict[str, Any]) -> list[str]:
    failures: list[str] = []
    if not result.get("escalation", {}).get("required"):
        failures.append("várt eszkaláció")
    return failures


def _assert_sla_escalation(result: dict[str, Any]) -> list[str]:
    failures: list[str] = []
    if not result.get("escalation", {}).get("required"):
        failures.append("SLA-lejáratnál eszkaláció várt")
    if "sla_lejart" not in (result.get("escalation", {}).get("reasons") or []):
        failures.append("hiányzó sla_lejart ok")
    return failures


def _assert_copilot(result: dict[str, Any]) -> list[str]:
    failures: list[str] = []
    draft = result.get("draft", {})
    if draft.get("format") != "copilot":
        failures.append("várt copilot formátum")
    if "Beszédpontok" not in draft.get("body_masked", ""):
        failures.append("hiányzó beszédpontok")
    return failures


SCENARIOS: list[DemoScenario] = [
    DemoScenario(
        scenario_id="szamlazas_e2e",
        title="Számlázási panasz végpontig",
        description="Retrieval → policy-map → draft → források",
        email_id="email-001-szamlazas-one",
        channel="email",
        input_text=None,
        service_provider="ONE",
        output_mode="hitl",
        sla_expired=False,
        assertions=_assert_szamlazas,
    ),
    DemoScenario(
        scenario_id="egyedi_szerzodes_eszkalacio",
        title="Egyedi szerződés gyanú → eszkaláció",
        description="Trigger-alapú supervisor átadás",
        email_id="email-edge-001-egyedi-szerzodes",
        channel="email",
        input_text=None,
        service_provider="ONE",
        output_mode="hitl",
        sla_expired=False,
        assertions=_assert_eszkalacio,
    ),
    DemoScenario(
        scenario_id="sla_lejarat_eszkalacio",
        title="SLA-lejárat → eszkaláció",
        description="SLA trigger az eszkalációs döntésben",
        email_id="email-001-szamlazas-one",
        channel="email",
        input_text=None,
        service_provider="ONE",
        output_mode="hitl",
        sla_expired=True,
        assertions=_assert_sla_escalation,
    ),
    DemoScenario(
        scenario_id="phone_copilot",
        title="Telefon copilot beszédpontok",
        description="Copilot csatorna forrással",
        email_id=None,
        channel="phone",
        input_text="A számlázási kifogásommal kapcsolatban szeretnék tájékoztatást.",
        service_provider="ONE",
        output_mode="hitl",
        sla_expired=False,
        assertions=_assert_copilot,
    ),
]
