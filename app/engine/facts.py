"""Construcao dos fatos do projeto a partir das respostas do questionario.

Fato = dado conhecido sobre o terreno/projeto usado para avaliar condicoes
legais (area do lote, altura da edificacao, uso, largura da testada...).
"""

from __future__ import annotations

from typing import Any

from app.models import Question

DERIV_OPS = {
    "mul": lambda a, b: a * b,
    "div": lambda a, b: (a / b) if b else None,
    "add": lambda a, b: a + b,
    "sub": lambda a, b: a - b,
    "min": lambda a, b: min(a, b),
    "max": lambda a, b: max(a, b),
}


def coerce(value: Any, qtype: str) -> Any:
    if value is None:
        return None
    if qtype == "number":
        try:
            return float(str(value).replace(",", "."))
        except (TypeError, ValueError):
            return None
    if qtype == "boolean":
        if isinstance(value, bool):
            return value
        return str(value).strip().lower() in {"1", "true", "sim", "yes", "on"}
    return str(value)


def _apply_derivation(derivation: dict, facts: dict[str, Any]) -> Any:
    op = derivation.get("op", "mul")
    args = derivation.get("args", [])
    values = [facts.get(a) for a in args]
    if any(v is None for v in values):
        return None
    fn = DERIV_OPS.get(op)
    if fn is None:
        return None
    try:
        result = fn(*values)
    except TypeError:
        return None
    if isinstance(result, float):
        return round(result, 4)
    return result


def build_facts(questions: list[Question], answers: dict[str, Any]) -> dict[str, Any]:
    """Respostas -> fatos (inclui valores default e derivacoes)."""
    facts: dict[str, Any] = {}

    for q in questions:
        if not q.is_fact or q.type == "derived":
            continue
        raw = answers.get(q.key)
        if raw is None:
            raw = q.default_value if q.default_value is not None else q.default_text
        value = coerce(raw, q.type)
        if value is not None:
            facts[q.key] = value

    # Derivacoes: perguntas do tipo "derived" calculam fatos a partir de outros.
    # Valor informado pelo responsavel tecnico tem precedencia sobre o calculado.
    for q in questions:
        if q.type == "derived":
            raw = answers.get(q.key)
            if raw is not None and str(raw).strip() != "":
                try:
                    facts[q.key] = float(str(raw).replace(",", "."))
                except (TypeError, ValueError):
                    pass
        for derivation in q.derivations or []:
            if derivation.get("fact") in facts:
                continue
            derived = _apply_derivation(derivation, facts)
            if derived is not None:
                facts[derivation["fact"]] = derived

    return facts


def missing_required(questions: list[Question], answers: dict[str, Any]) -> list[Question]:
    """Campos obrigatorios ainda nao respondidos."""
    missing = []
    for q in questions:
        if not q.required or q.type == "derived" or not q.is_fact:
            continue
        value = answers.get(q.key)
        if value is None or (isinstance(value, str) and not value.strip()):
            missing.append(q)
    return missing
