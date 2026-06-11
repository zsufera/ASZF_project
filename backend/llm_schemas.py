"""Pydantic sémák a chat_json() LLM-válaszok validálásához.

Minden LLM-hívó modul a saját try-blokkjában validálja a nyers dict-et;
pydantic.ValidationError esetén a meglévő except-ág determinisztikus
fallbackre terel (ld. .claude/skills/add-llm-call).
"""
from __future__ import annotations

from pydantic import BaseModel, Field


class ClassifyCandidate(BaseModel):
    kategoria: str = ""
    konfidencia: float = 0.5


class ClassifyResponse(BaseModel):
    fo_kategoria: str = ""
    altipus: str | None = None
    tobb_jelolt: list[ClassifyCandidate] = Field(default_factory=list)
    konfidencia: float = 0.6


class SynthesizeResponse(BaseModel):
    targy: str | None = None
    valasz: str = ""
    felhasznalt_forrasok: list[str] = Field(default_factory=list)
    elegtelen_fedezet: bool = False


class VerifyResponse(BaseModel):
    nem_megalapozott: list[str] = Field(default_factory=list)
    nem_megalapozott_chunk_idk: list[str] = Field(default_factory=list)


class EscalationResponse(BaseModel):
    eszkalacio: bool = False
    okok: list[str] = Field(default_factory=list)


class QueryRewriteResponse(BaseModel):
    query: str = ""


class JudgeResponse(BaseModel):
    pontszam: float = 3.0
    forrashuseg: float = 3.0
    teljesseg: float = 3.0
    hangnem: float = 3.0
    kozerthetoseg: float = 3.0
    indoklas: str = ""
