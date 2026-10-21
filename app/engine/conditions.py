"""Avaliacao de condicoes declarativas.

Formato de condicao (todas as chaves sao combinadas com AND)::

    when:
      lot_area: {lt: 500}
      building_height: {lte: 10}
      use: {in: [comercial, misto]}

Valores escalar equivalem a igualdade: ``use: residencial``.
"""

from __future__ import annotations

from typing import Any

OPS = {
    "eq": lambda a, b: a == b,
    "ne": lambda a, b: a != b,
    "lt": lambda a, b: a < b,
    "lte": lambda a, b: a <= b,
    "gt": lambda a, b: a > b,
    "gte": lambda a, b: a >= b,
    "in": lambda a, b: a in (b or []),
    "not_in": lambda a, b: a not in (b or []),
    "between": lambda a, b: b[0] <= a <= b[1],
}


def match_condition(spec: Any, facts: dict[str, Any]) -> bool:
    """Retorna True se os fatos satisfazem a condicao informada."""
    if spec is None:
        return True
    if not isinstance(spec, dict):
        return bool(spec)

    for fact, cond in spec.items():
        if fact not in facts or facts[fact] is None:
            return False
        value = facts[fact]
        if isinstance(cond, dict):
            for op, expected in cond.items():
                fn = OPS.get(op)
                if fn is None:
                    return False
                try:
                    if not fn(value, expected):
                        return False
                except TypeError:
                    return False
        elif isinstance(cond, (list, tuple)):
            if value not in cond:
                return False
        else:
            if value != cond:
                return False
    return True


def missing_facts(spec: Any, facts: dict[str, Any]) -> list[str]:
    """Lista os fatos ainda nao informados necessarios para avaliar a condicao."""
    if not isinstance(spec, dict):
        return []
    missing = []
    for fact, cond in spec.items():
        if fact not in facts or facts[fact] is None:
            missing.append(fact)
            continue
        if isinstance(cond, dict) and any(op not in OPS for op in cond):
            missing.append(fact)
    return missing
