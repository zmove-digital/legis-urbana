"""Modelo de dados (ORM).

A estrutura foi desenhada para ser generica: qualquer cidade pode ser cadastrada
descrevendo suas zonas, parametros, condicoes e fontes em um arquivo YAML,
sem necessidade de alterar codigo.
"""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


def _now() -> datetime:
    return datetime.now(UTC)


class City(Base):
    __tablename__ = "cities"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    slug: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(120))
    uf: Mapped[str] = mapped_column(String(2))
    ibge: Mapped[str | None] = mapped_column(String(16), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    zone_selection_method: Mapped[str] = mapped_column(String(32), default="manual")
    zone_selection_hint: Mapped[str | None] = mapped_column(Text, nullable=True)
    zone_selection_helper_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    zone_rules: Mapped[list | None] = mapped_column(JSON, nullable=True)
    content_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_now, onupdate=_now)

    sources: Mapped[list[Source]] = relationship(
        back_populates="city", cascade="all, delete-orphan"
    )
    zones: Mapped[list[Zone]] = relationship(
        back_populates="city", cascade="all, delete-orphan", order_by="Zone.ord"
    )
    questions: Mapped[list[Question]] = relationship(
        back_populates="city", cascade="all, delete-orphan", order_by="Question.ord"
    )
    rules: Mapped[list[Rule]] = relationship(
        back_populates="city", cascade="all, delete-orphan", order_by="Rule.ord"
    )


class Source(Base):
    """Fonte legal (lei, decreto, anexo, norma tecnica)."""

    __tablename__ = "sources"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    city_id: Mapped[int] = mapped_column(ForeignKey("cities.id", ondelete="CASCADE"), index=True)
    key: Mapped[str] = mapped_column(String(64))
    kind: Mapped[str] = mapped_column(String(32), default="lei")
    number: Mapped[str | None] = mapped_column(String(64), nullable=True)
    year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    title: Mapped[str] = mapped_column(Text)
    url: Mapped[str | None] = mapped_column(Text, nullable=True)
    consolidated_as_of: Mapped[str | None] = mapped_column(String(32), nullable=True)
    retrieved_at: Mapped[str | None] = mapped_column(String(32), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    city: Mapped[City] = relationship(back_populates="sources")


class Zone(Base):
    """Zona de uso (zoneamento) com seus parametros."""

    __tablename__ = "zones"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    city_id: Mapped[int] = mapped_column(ForeignKey("cities.id", ondelete="CASCADE"), index=True)
    code: Mapped[str] = mapped_column(String(32))
    name: Mapped[str] = mapped_column(String(160))
    group_name: Mapped[str | None] = mapped_column(String(64), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    ord: Mapped[int] = mapped_column(Integer, default=0)

    city: Mapped[City] = relationship(back_populates="zones")
    parameters: Mapped[list[Parameter]] = relationship(
        back_populates="zone", cascade="all, delete-orphan", order_by="Parameter.ord"
    )


class Parameter(Base):
    """Parametro de ocupacao (CA, TO, recuo, gabarito...) com sua base legal."""

    __tablename__ = "parameters"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    city_id: Mapped[int] = mapped_column(ForeignKey("cities.id", ondelete="CASCADE"), index=True)
    zone_id: Mapped[int] = mapped_column(ForeignKey("zones.id", ondelete="CASCADE"), index=True)
    key: Mapped[str] = mapped_column(String(64))
    label: Mapped[str] = mapped_column(Text)
    unit: Mapped[str | None] = mapped_column(String(32), nullable=True)
    value_num: Mapped[float | None] = mapped_column(Float, nullable=True)
    value_text: Mapped[str | None] = mapped_column(String(120), nullable=True)
    check_spec: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    alternatives: Mapped[list | None] = mapped_column(JSON, nullable=True)
    basis: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    notes: Mapped[list | None] = mapped_column(JSON, nullable=True)
    ord: Mapped[int] = mapped_column(Integer, default=0)

    zone: Mapped[Zone] = relationship(back_populates="parameters")


class Rule(Base):
    """Regra condicional (dispensas, faculdades, exigencia adicional)."""

    __tablename__ = "rules"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    city_id: Mapped[int] = mapped_column(ForeignKey("cities.id", ondelete="CASCADE"), index=True)
    code: Mapped[str] = mapped_column(String(64))
    title: Mapped[str] = mapped_column(Text)
    message: Mapped[str | None] = mapped_column(Text, nullable=True)
    severity: Mapped[str] = mapped_column(String(16), default="info")
    when: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    applies_to_zones: Mapped[list | None] = mapped_column(JSON, nullable=True)
    exclude_zones: Mapped[list | None] = mapped_column(JSON, nullable=True)
    effects: Mapped[list | None] = mapped_column(JSON, nullable=True)
    basis: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    ord: Mapped[int] = mapped_column(Integer, default=0)

    city: Mapped[City] = relationship(back_populates="rules")


class Question(Base):
    """Campo do questionario que o engenheiro preenche."""

    __tablename__ = "questions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    city_id: Mapped[int] = mapped_column(ForeignKey("cities.id", ondelete="CASCADE"), index=True)
    key: Mapped[str] = mapped_column(String(64))
    label: Mapped[str] = mapped_column(Text)
    type: Mapped[str] = mapped_column(String(24), default="number")
    required: Mapped[bool] = mapped_column(Boolean, default=False)
    options: Mapped[list | None] = mapped_column(JSON, nullable=True)
    help_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    unit: Mapped[str | None] = mapped_column(String(24), nullable=True)
    default_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    default_text: Mapped[str | None] = mapped_column(String(120), nullable=True)
    is_fact: Mapped[bool] = mapped_column(Boolean, default=True)
    derivations: Mapped[list | None] = mapped_column(JSON, nullable=True)
    ord: Mapped[int] = mapped_column(Integer, default=0)

    city: Mapped[City] = relationship(back_populates="questions")


class Project(Base):
    """Analise salva pelo engenheiro."""

    __tablename__ = "projects"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    city_id: Mapped[int] = mapped_column(ForeignKey("cities.id", ondelete="CASCADE"), index=True)
    zone_id: Mapped[int | None] = mapped_column(
        ForeignKey("zones.id", ondelete="SET NULL"), nullable=True
    )
    name: Mapped[str] = mapped_column(String(160), default="Analise sem nome")
    input_payload: Mapped[dict] = mapped_column(JSON, default=dict)
    result_payload: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)
