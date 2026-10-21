"""Resolucao da zona de zoneamento aplicavel ao terreno.

Tres metodos suportados (declarados em `zone_selection.method` da cidade):

* `manual`      - o engenheiro informa a sigla da zona (padrao).
* `questionnaire` - regras declarativas cruzam as respostas do questionario.
* `geo`         - ponto (lat/lon) consultado contra o poligono da zona.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.config import CITIES_DIR
from app.engine.conditions import match_condition
from app.models import City, Zone


def find_zone(city: City, zones: list[Zone], code: str | None) -> Zone | None:
    if not code:
        return None
    target = code.strip().upper()
    for zone in zones:
        if zone.code.upper() == target:
            return zone
    return None


def resolve_by_questionnaire(
    city: City, zones: list[Zone], facts: dict[str, Any]
) -> tuple[Zone | None, list[Zone], list[dict]]:
    """Aplica as regras de zoneamento declaradas pela cidade."""
    candidates: list[Zone] = []
    matched_rules: list[dict] = []
    best_priority = None

    for rule in city.zone_rules or []:
        if not match_condition(rule.get("when"), facts):
            continue
        zone = find_zone(city, zones, rule.get("zone"))
        if zone is None:
            continue
        priority = rule.get("priority", 0)
        matched_rules.append({"rule": rule.get("message", ""), "zone": zone.code})
        if best_priority is None or priority > best_priority:
            best_priority = priority
            candidates = [zone]
        elif priority == best_priority and zone not in candidates:
            candidates.append(zone)

    if len(candidates) == 1:
        return candidates[0], candidates, matched_rules
    return None, candidates, matched_rules


def _point_in_ring(x: float, y: float, ring: list) -> bool:
    inside = False
    n = len(ring)
    for i in range(n):
        x1, y1 = ring[i][0], ring[i][1]
        x2, y2 = ring[(i + 1) % n][0], ring[(i + 1) % n][1]
        if (y1 > y) != (y2 > y):
            xint = (x2 - x1) * (y - y1) / (y2 - y1) + x1
            if x < xint:
                inside = not inside
    return inside


def _point_in_polygon(x: float, y: float, polygon: list) -> bool:
    if not polygon:
        return False
    if not _point_in_ring(x, y, polygon[0]):
        return False
    for hole in polygon[1:]:
        if _point_in_ring(x, y, hole):
            return False
    return True


def resolve_by_geo(city: City, zones: list[Zone], facts: dict[str, Any]) -> Zone | None:
    """Consulta o GeoJSON local de zonas (data/cities/<slug>/zones.geojson)."""
    lat = facts.get("lat")
    lon = facts.get("lon")
    if lat is None or lon is None:
        return None

    path = CITIES_DIR / city.slug / "zones.geojson"
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None

    for feature in data.get("features", []):
        props = feature.get("properties") or {}
        code = props.get("code")
        geometry = feature.get("geometry") or {}
        gtype = geometry.get("type")
        coords = geometry.get("coordinates") or []
        hit = False
        if gtype == "Polygon":
            hit = _point_in_polygon(lon, lat, coords)
        elif gtype == "MultiPolygon":
            for polygon in coords:
                if _point_in_polygon(lon, lat, polygon):
                    hit = True
                    break
        if hit:
            return find_zone(city, zones, code)
    return None


def resolve_zone(
    city: City,
    zones: list[Zone],
    facts: dict[str, Any],
    explicit_code: str | None = None,
) -> dict[str, Any]:
    """Resolve a zona e devolve o metodo usado + candidatos."""
    method = city.zone_selection_method or "manual"

    if explicit_code:
        zone = find_zone(city, zones, explicit_code)
        if zone is None:
            return {
                "zone": None,
                "candidates": [],
                "method": "informada",
                "message": f"Zona '{explicit_code}' nao encontrada em {city.name}.",
                "rules": [],
            }
        return {
            "zone": zone,
            "candidates": [zone],
            "method": "informada",
            "message": f"Zona {zone.code} - {zone.name} (informada manualmente).",
            "rules": [],
        }

    if facts.get("lat") is not None and facts.get("lon") is not None:
        zone = resolve_by_geo(city, zones, facts)
        if zone:
            return {
                "zone": zone,
                "candidates": [zone],
                "method": "geo",
                "message": f"Zona {zone.code} - {zone.name} (localizacao geografica).",
                "rules": [],
            }

    if method == "questionnaire":
        zone, candidates, rules = resolve_by_questionnaire(city, zones, facts)
        if zone:
            return {
                "zone": zone,
                "candidates": candidates,
                "method": "questionario",
                "message": f"Zona {zone.code} - {zone.name} (definida pelo questionario).",
                "rules": rules,
            }
        if candidates:
            return {
                "zone": None,
                "candidates": candidates,
                "method": "questionario",
                "message": "As respostas apontam para mais de uma zona. Selecione a aplicavel.",
                "rules": rules,
            }

    return {
        "zone": None,
        "candidates": [],
        "method": method,
        "message": city.zone_selection_hint or "Selecione a zona de zoneamento do terreno.",
        "rules": [],
    }


def load_zones_geojson(slug: str) -> list[Path]:
    path = CITIES_DIR / slug / "zones.geojson"
    return [path] if path.exists() else []
