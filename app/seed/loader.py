"""Leitor de cidades em YAML -> banco de dados.

O YAML e a fonte da verdade. Formato (resumo):

    slug, name, uf, ibge, description
    zone_selection: {method, hint, helper_url, rules[]}
    sources: [{key, kind, number, year, title, url, consolidated_as_of, retrieved_at, notes}]
    questions: [{key, label, type, required, unit, help, options, default, default_text, derivations}]
    zones: [{code, name, group, description, params: {chave: {label, unit, value, basis,
             check, notes, alternatives}}}]
    rules: [{code, title, message, severity, when, applies_to_zones, exclude_zones,
             effects[], basis}]
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

import yaml
from sqlalchemy.orm import Session

from app.config import CITIES_DIR
from app.models import City, Parameter, Project, Question, Rule, Source, Zone


def _hash_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()[:32]


def _clear_city(db: Session, city: City) -> None:
    db.query(Project).filter(Project.city_id == city.id).delete()
    db.query(Parameter).filter(Parameter.city_id == city.id).delete()
    db.query(Question).filter(Question.city_id == city.id).delete()
    db.query(Rule).filter(Rule.city_id == city.id).delete()
    db.query(Source).filter(Source.city_id == city.id).delete()
    db.query(Zone).filter(Zone.city_id == city.id).delete()
    db.delete(city)
    db.flush()


def _load_sources(db: Session, city: City, data: dict[str, Any]) -> None:
    for item in data.get("sources", []) or []:
        db.add(
            Source(
                city_id=city.id,
                key=item["key"],
                kind=item.get("kind", "lei"),
                number=str(item.get("number")) if item.get("number") is not None else None,
                year=item.get("year"),
                title=item.get("title", item["key"]),
                url=item.get("url"),
                consolidated_as_of=item.get("consolidated_as_of"),
                retrieved_at=item.get("retrieved_at"),
                notes=item.get("notes"),
            )
        )


def _load_questions(db: Session, city: City, data: dict[str, Any]) -> None:
    for order, item in enumerate(data.get("questions", []) or []):
        default = item.get("default")
        db.add(
            Question(
                city_id=city.id,
                key=item["key"],
                label=item.get("label", item["key"]),
                type=item.get("type", "number"),
                required=bool(item.get("required", False)),
                options=item.get("options"),
                help_text=item.get("help"),
                unit=item.get("unit"),
                default_value=float(default) if isinstance(default, (int, float)) else None,
                default_text=str(default) if isinstance(default, str) else None,
                is_fact=item.get("is_fact", True),
                derivations=item.get("derivations"),
                ord=order,
            )
        )


def _load_zones(db: Session, city: City, data: dict[str, Any]) -> None:
    for order, item in enumerate(data.get("zones", []) or []):
        zone = Zone(
            city_id=city.id,
            code=item["code"],
            name=item.get("name", item["code"]),
            group_name=item.get("group"),
            description=item.get("description"),
            ord=order,
        )
        db.add(zone)
        db.flush()
        for p_order, (key, spec) in enumerate((item.get("params") or {}).items()):
            value = spec.get("value")
            value_num = float(value) if isinstance(value, (int, float)) else None
            value_text = None if value is None else str(value)
            db.add(
                Parameter(
                    city_id=city.id,
                    zone_id=zone.id,
                    key=key,
                    label=spec.get("label", key),
                    unit=spec.get("unit"),
                    value_num=value_num,
                    value_text=value_text,
                    check_spec=spec.get("check"),
                    alternatives=spec.get("alternatives"),
                    basis=spec.get("basis"),
                    notes=spec.get("notes"),
                    ord=p_order,
                )
            )


def _load_rules(db: Session, city: City, data: dict[str[str, Any]]) -> None:
    for order, item in enumerate(data.get("rules", []) or []):
        db.add(
            Rule(
                city_id=city.id,
                code=item["code"],
                title=item.get("title", item["code"]),
                message=item.get("message"),
                severity=item.get("severity", "info"),
                when=item.get("when"),
                applies_to_zones=item.get("applies_to_zones"),
                exclude_zones=item.get("exclude_zones"),
                effects=item.get("effects"),
                basis=item.get("basis"),
                ord=order,
            )
        )


def load_city_file(db: Session, path: Path) -> City:
    raw = path.read_text(encoding="utf-8")
    data = yaml.safe_load(raw) or {}
    slug = data["slug"]

    city = db.query(City).filter(City.slug == slug).one_or_none()
    if city is not None:
        _clear_city(db, city)

    zone_selection = data.get("zone_selection") or {}
    city = City(
        slug=slug,
        name=data["name"],
        uf=data.get("uf", ""),
        ibge=str(data.get("ibge")) if data.get("ibge") is not None else None,
        description=data.get("description"),
        zone_selection_method=zone_selection.get("method", "manual"),
        zone_selection_hint=zone_selection.get("hint"),
        zone_selection_helper_url=zone_selection.get("helper_url"),
        zone_rules=zone_selection.get("rules"),
        content_hash=_hash_file(path),
        is_demo=bool(data.get("is_demo", False)),
    )
    db.add(city)
    db.flush()

    _load_sources(db, city, data)
    _load_questions(db, city, data)
    _load_zones(db, city, data)
    _load_rules(db, city, data)
    db.commit()
    return city


def seed_all(db: Session, cities_dir: Path | None = None) -> list[str]:
    """Carrega todas as cidades. Reaplica apenas as que mudaram (hash do arquivo)."""
    root = cities_dir or CITIES_DIR
    loaded: list[str] = []
    if not root.exists():
        return loaded

    for path in sorted(root.glob("*/city.yaml")):
        content_hash = _hash_file(path)
        slug = path.parent.name
        existing = db.query(City).filter(City.slug == slug).one_or_none()
        if existing is not None and existing.content_hash == content_hash:
            loaded.append(slug)
            continue
        city = load_city_file(db, path)
        loaded.append(city.slug)
    return loaded
