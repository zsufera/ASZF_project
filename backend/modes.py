from __future__ import annotations

from enum import Enum


class ClassifyMode(str, Enum):
    LLM = "llm"
    RULE = "rule"


class GenerationMode(str, Enum):
    LLM = "llm"
    TEMPLATE = "template"
    INSUFFICIENT = "insufficient"


class VerifyMode(str, Enum):
    LLM = "llm"
    HEURISTIC = "heuristic"


class EscalationMode(str, Enum):
    RULE = "rule"
    RULE_LLM = "rule+llm"


class OrchestratorMode(str, Enum):
    LLM = "llm"
    FALLBACK = "fallback"
