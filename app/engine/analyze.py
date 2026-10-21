"""Orquestrador da analise: resolve zona, aplica regras e roda as verificacoes."""

from __future__ import annotations

from typing import Any

from app.config import DISCLAIMER
from app.engine import checks as checks_engine
from app.engine.conditions import match_condition, missing_facts
from app.engine.facts import build_facts, missing_required
from app.engine.resolver import resolve_zone
from app.models import City, Parameter, Question, Rule, Source, Zone

PARAM_DISPLAY_KEYS = {
    "ca_max": "Coeficiente de Aproveitamento maximo",
    "ca_base": "Coeficiente de Aproveitamento basico",
    "ca_min": "Coeficiente de Aproveitamento minimo",
    "to_max": "Taxa de Ocupacao maxima",
    "max_height": "Gabarito de altura maxima",
    "setback_front": "Recuo frontal minimo",
    "setback_side_back": "Recuo lateral e de fundo minimo",
    "min_permeable_pct": "Area permeavel minima (% do lote)",
    "max_lot_area_per_unit": "Cota parte maxima de terreno por unidade",
}


def _rule_applies(rule: Rule, zone: Zone | None) -> bool:
    if zone is None:
        return False
    applies_to = rule.applies_to_zones
    if applies_to:
        if "*" not in applies_to and zone.code.upper() not in [z.upper() for z in applies_to]:
            return False
    exclude = rule.exclude_zones or []
    if zone.code.upper() in [z.upper() for z in exclude]:
        return False
    return True


def _resolve_param_value(param: Parameter, facts: dict[str, Any]) -> dict[str, Any]:
    """Resolve o valor do parametro considerando as alternativas condicionais."""
    alternatives = param.alternatives or []
    for alt in alternatives:
        if match_condition(alt.get("when"), facts):
            return {
                "value": alt.get("value"),
                "basis": alt.get("basis") or param.basis,
                "notes": (param.notes or []) + (alt.get("notes") or []),
                "message": alt.get("message"),
                "applied_alternative": alt.get("when"),
                "pending_facts": [],
            }

    if alternatives and param.value_num is None:
        pending: list[str] = []
        for alt in alternatives:
            pending.extend(missing_facts(alt.get("when"), facts))
        return {
            "value": None,
            "basis": param.basis,
            "notes": param.notes or [],
            "message": None,
            "applied_alternative": None,
            "pending_facts": sorted(set(pending)),
        }

    return {
        "value": param.value_num,
        "value_text": param.value_text,
        "basis": param.basis,
        "notes": param.notes or [],
        "message": None,
        "applied_alternative": None,
        "pending_facts": [],
    }


def analyze(
    city: City,
    zones: list[Zone],
    questions: list[Question],
    rules: list[Rule],
    sources: list[Source],
    answers: dict[str, Any],
    explicit_zone: str | None = None,
) -> dict[str, Any]:
    facts = build_facts(questions, answers)
    resolution = resolve_zone(city, zones, facts, explicit_zone)
    zone: Zone | None = resolution["zone"]

    missing_required_fields = [q.key for q in missing_required(questions, answers)]

    parameters: list[dict[str, Any]] = []
    check_results: list[dict[str, Any]] = []
    requirements: list[dict[str, Any]] = []
    applied_rules: list[dict[str, Any]] = []
    overrides: dict[str, dict[str, Any]] = {}

    # 1) Parametros da zona
    resolved: dict[str, dict[str, Any]] = {}
    if zone:
        for param in zone.parameters:
            resolved[param.key] = _resolve_param_value(param, facts)

    # 2) Regras condiconais aplicaveis a zona
    for rule in rules:
        if not _rule_applies(rule, zone):
            continue
        if not match_condition(rule.when, facts):
            continue
        applied_rules.append(
            {
                "code": rule.code,
                "title": rule.title,
                "message": rule.message,
                "severity": rule.severity,
                "basis": rule.basis,
            }
        )
        for effect in rule.effects or []:
            etype = effect.get("type")
            if etype == "override_param":
                overrides[effect["param"]] = {
                    "value": effect.get("value"),
                    "message": effect.get("message"),
                    "basis": effect.get("basis") or rule.basis,
                    "rule": rule.code,
                }
            elif etype in {"add_requirement", "warning"}:
                requirements.append(
                    {
                        "title": effect.get("title") or rule.title,
                        "message": effect.get("message") or rule.message,
                        "severity": effect.get("severity", rule.severity),
                        "basis": effect.get("basis") or rule.basis,
                    }
                )

    # 3) Monta parametros + verificacoes
    if zone:
        for param in zone.parameters:
            info = resolved.get(param.key, {})
            value = info.get("value")
            basis = info.get("basis") or param.basis
            notes = info.get("notes") or []

            override = overrides.get(param.key)
            if override is not None:
                value = override.get("value")
                basis = override.get("basis") or basis
                if override.get("message"):
                    notes = notes + [override["message"]]

            if value is None:
                if info.get("pending_facts"):
                    status = checks_engine.PENDENTE
                    message = (
                        "Informe "
                        + ", ".join(info["pending_facts"])
                        + " para determinar este limite."
                    )
                else:
                    status = checks_engine.NAO_APLICAVEL
                    message = "Não se aplica a esta zona."
                check_results.append(
                    {
                        "key": param.key,
                        "label": param.label,
                        "unit": param.unit,
                        "status": status,
                        "limit": None,
                        "limit_display": "Não se aplica",
                        "computed": None,
                        "computed_display": None,
                        "allowance": None,
                        "message": message,
                        "basis": basis,
                        "notes": notes,
                    }
                )
                parameters.append(
                    {
                        "key": param.key,
                        "label": param.label,
                        "value": None,
                        "value_display": "Não se aplica",
                        "unit": param.unit,
                        "basis": basis,
                        "notes": notes,
                    }
                )
                continue

            result = checks_engine.run_check(
                key=param.key,
                label=param.label,
                value=value,
                unit=param.unit,
                spec=param.check_spec,
                facts=facts,
                basis=basis,
                notes=notes,
            )
            if info.get("message"):
                result["message"] = f"{result['message']} {info['message']}".strip()
            check_results.append(result)

            parameters.append(
                {
                    "key": param.key,
                    "label": param.label,
                    "value": value,
                    "value_display": result["limit_display"],
                    "unit": param.unit,
                    "basis": basis,
                    "notes": notes,
                }
            )

    # 4) Fontes efetivamente utilizadas
    used_source_keys: set[str] = set()
    for item in [*parameters, *check_results, *requirements, *applied_rules]:
        basis = item.get("basis") or {}
        key = basis.get("source")
        if key:
            used_source_keys.add(key)
    source_list = [
        {
            "key": s.key,
            "kind": s.kind,
            "number": s.number,
            "year": s.year,
            "title": s.title,
            "url": s.url,
            "consolidated_as_of": s.consolidated_as_of,
            "retrieved_at": s.retrieved_at,
            "notes": s.notes,
        }
        for s in sources
        if s.key in used_source_keys
    ]

    # 5) Resumo
    counts = {
        checks_engine.CONFORME: 0,
        checks_engine.NAO_CONFORME: 0,
        checks_engine.PENDENTE: 0,
        checks_engine.ATENCAO: 0,
        checks_engine.REFERENCIA: 0,
        checks_engine.NAO_APLICAVEL: 0,
    }
    for item in check_results:
        counts[item["status"]] = counts.get(item["status"], 0) + 1

    if counts[checks_engine.NAO_CONFORME]:
        overall = checks_engine.NAO_CONFORME
    elif counts[checks_engine.PENDENTE]:
        overall = checks_engine.PENDENTE
    elif counts[checks_engine.ATENCAO]:
        overall = checks_engine.ATENCAO
    else:
        overall = checks_engine.CONFORME

    pending_data = sorted(
        {
            fact
            for item in check_results
            if item["status"] == checks_engine.PENDENTE
            for fact in _pending_facts_for(item, questions)
        }
    )

    return {
        "city": {"slug": city.slug, "name": city.name, "uf": city.uf},
        "zone": (
            {"code": zone.code, "name": zone.name, "group": zone.group_name} if zone else None
        ),
        "zone_resolution": {
            "method": resolution["method"],
            "message": resolution["message"],
            "candidates": [z.code for z in resolution["candidates"]],
            "rules": resolution["rules"],
            "helper_url": city.zone_selection_helper_url,
        },
        "inputs": answers,
        "facts": facts,
        "parameters": parameters,
        "checks": check_results,
        "requirements": requirements,
        "applied_rules": applied_rules,
        "sources": source_list,
        "summary": {**counts, "status": overall},
        "pending_data": pending_data,
        "missing_required": missing_required_fields,
        "disclaimer": DISCLAIMER,
    }


def _pending_facts_for(item: dict[str, Any], questions: list[Question]) -> list[str]:
    """Descobre quais dados faltam para uma verificacao pendente."""
    message = item.get("message") or ""
    keys = []
    for q in questions:
        if q.key in message:
            keys.append(q.key)
    return keys
