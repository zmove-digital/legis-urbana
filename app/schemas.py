"""Schemas de entrada/saida da API."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class AnalyzeRequest(BaseModel):
    city: str = Field(..., description="Slug da cidade (ex.: sao-paulo)")
    zone: str | None = Field(None, description="Sigla da zona, quando conhecida")
    answers: dict[str, Any] = Field(default_factory=dict, description="Respostas do questionario")
    name: str | None = None


class ProjectCreate(BaseModel):
    city: str
    zone: str | None = None
    answers: dict[str, Any] = Field(default_factory=dict)
    name: str = "Analise sem nome"
