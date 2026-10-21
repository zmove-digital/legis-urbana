"""Verificacao determinista dos parametros contra o projeto informado.

Cada parametro pode declarar um `check`:

    check:
      type: ratio_max          # (num / den) <= valor
      numerator: total_built_area
      denominator: lot_area
    # ou
    check:
      type: gte               # campo >= valor (recuos minimos)
      field: setback_front
    # ou
    check:
      type: lte               # campo <= valor (altura maxima)
      field: building_height
    # ou
    check:
      type: max_area_per_unit
      field: lot_area
      divisor: units
"""

from __future__ import annotations

from typing import Any

from app.engine.conditions import match_condition

EPS = 1e-9

CONFORME = "conforme"
NAO_CONFORME = "nao_conforme"
PENDENTE = "pendente"
NAO_APLICAVEL = "nao_aplicavel"
ATENCAO = "atencao"
REFERENCIA = "referencia"

STATUS_LABEL = {
    CONFORME: "Conforme",
    NAO_CONFORME: "Nao conforme",
    PENDENTE: "Dado pendente",
    NAO_APLICAVEL: "Nao se aplica",
    ATENCAO: "Atencao",
    REFERENCIA: "Referencia",
}


def _round(value: float | None, digits: int = 2) -> float | None:
    if value is None:
        return None
    return round(value + 0.0, digits)


def _fmt(value: float | None) -> str:
    if value is None:
        return "-"
    if abs(value - round(value)) < 1e-9:
        return str(int(round(value)))
    return f"{value:.2f}".rstrip("0").rstrip(".")


def _cap_applies(spec: dict, facts: dict[str, Any]) -> bool:
    """Decide se a base de calculo do limite deve ser reduzida."""
    cond = spec.get("denominator_cap_when")
    if cond is not None and not match_condition(cond, facts):
        return False
    exempt = spec.get("denominator_cap_exempt_when")
    if exempt is not None and match_condition(exempt, facts):
        return False
    return True


def run_check(
    key: str,
    label: str,
    value: Any,
    unit: str | None,
    spec: dict | None,
    facts: dict[str, Any],
    basis: dict | None,
    notes: list | None,
) -> dict:
    """Executa a verificacao de um parametro e devolve o resultado formatado."""
    result: dict[str, Any] = {
        "key": key,
        "label": label,
        "unit": unit,
        "status": NAO_APLICAVEL,
        "limit": None,
        "limit_display": None,
        "computed": None,
        "computed_display": None,
        "allowance": None,
        "message": "",
        "basis": basis,
        "notes": notes or [],
    }

    if value is None:
        result["message"] = "Valor nao definido para esta zona."
        return result

    if not isinstance(value, (int, float)) or isinstance(value, bool):
        result["status"] = PENDENTE
        result["limit_display"] = str(value)
        result["message"] = (
            f"Limite nao determinavel de forma automatica ({value}). "
            "Verificar com o orgao competente."
        )
        return result

    result["limit"] = value
    result["limit_display"] = _fmt(value) + (f" {unit}" if unit else "")

    if not spec:
        result["status"] = REFERENCIA
        result["message"] = "Valor de referencia (sem verificacao automatica disponivel)."
        return result

    ctype = spec.get("type")

    if ctype == "ratio_max":
        num_field = spec.get("numerator", "")
        den_field = spec.get("denominator", "")
        num = facts.get(num_field)
        den = facts.get(den_field)
        if num is None or den in (None, 0):
            result["status"] = PENDENTE
            result["message"] = f"Informe {num_field} e {den_field} para verificar o limite."
            return result
        # Areas isentas de contabilizacao (art. 73 da LC 1076/2026, por exemplo).
        offset_field = spec.get("numerator_offset")
        offset = (facts.get(offset_field) or 0) if offset_field else 0
        num -= offset
        # Base de calculo limitada (modulo de fracionamento, por exemplo).
        cap = spec.get("denominator_cap")
        if cap is not None and _cap_applies(spec, facts):
            den = min(den, float(cap))
        ratio = num / den
        max_area = value * den
        result["computed"] = _round(ratio, 4)
        computed_display = f"{_fmt(ratio)} ({_fmt(num)} m² / {_fmt(den)} m²)"
        if offset:
            computed_display += f" [isento: {_fmt(offset)} m²]"
        result["computed_display"] = computed_display
        result["allowance"] = {
            "label": f"Area maxima admissivel ({num_field})",
            "value": _round(max_area),
            "unit": "m²",
            "display": f"{_fmt(max_area)} m²",
        }
        if ratio <= value + EPS:
            result["status"] = CONFORME
            result["message"] = f"Proporcao {_fmt(ratio)} dentro do limite {_fmt(value)}."
        else:
            result["status"] = NAO_CONFORME
            result["message"] = (
                f"Proporcao {_fmt(ratio)} excede o limite {_fmt(value)} "
                f"(excedente de {_fmt(num - max_area)} m²)."
            )
        return result

    if ctype in {"gte", "lte"}:
        fields = spec.get("fields") or ([spec["field"]] if spec.get("field") else [])
        values = [facts.get(f) for f in fields]
        known = [v for v in values if v is not None]
        if not known:
            result["status"] = PENDENTE
            result["message"] = f"Informe '{', '.join(fields)}' para verificar o limite."
            return result
        actual = min(known) if ctype == "gte" else max(known)
        result["computed"] = _round(actual)
        result["computed_display"] = f"{_fmt(actual)} {unit}".strip()
        if ctype == "gte":
            ok = all(v >= value - EPS for v in known)
            result["message"] = f"Valor minimo exigido {_fmt(value)} {unit or ''}".strip() + (
                " - atendido." if ok else f" - insuficiente (faltam {_fmt(value - actual)})."
            )
        else:
            ok = all(v <= value + EPS for v in known)
            result["message"] = f"Valor maximo permitido {_fmt(value)} {unit or ''}".strip() + (
                " - atendido." if ok else f" - excede em {_fmt(actual - value)}."
            )
        result["status"] = CONFORME if ok else NAO_CONFORME
        return result

    if ctype == "min_area_from_pct":
        field = spec.get("field", "permeable_area")
        base_field = spec.get("base", "lot_area")
        actual = facts.get(field)
        base = facts.get(base_field)
        if actual is None or base is None:
            result["status"] = PENDENTE
            result["message"] = f"Informe '{field}' e '{base_field}' para verificar o limite."
            return result
        limit = base * value / 100.0
        result["computed"] = _round(actual)
        result["computed_display"] = f"{_fmt(actual)} m²"
        result["allowance"] = {
            "label": f"Área permeável mínima ({value:g}% da área do lote)",
            "value": _round(limit),
            "unit": "m²",
            "display": f"{_fmt(limit)} m²",
        }
        if actual >= limit - EPS:
            result["status"] = CONFORME
            result["message"] = (
                f"Área permeável de {_fmt(actual)} m² atende o mínimo de {_fmt(limit)} m²."
            )
        else:
            result["status"] = NAO_CONFORME
            result["message"] = (
                f"Área permeável de {_fmt(actual)} m² é inferior ao mínimo de {_fmt(limit)} m² "
                f"({value:g}% de {_fmt(base)} m²)."
            )
        return result

    if ctype == "min_area_piecewise":
        """Area minima em degraus (taxa de permeabilidade sobre faixas de lote)."""
        field = spec.get("field", "permeable_area")
        base_field = spec.get("base", "lot_area")
        actual = facts.get(field)
        base = facts.get(base_field)
        if actual is None or base is None:
            result["status"] = PENDENTE
            result["message"] = f"Informe '{field}' e '{base_field}' para verificar o limite."
            return result

        segments = spec.get("segments") or []
        limit = 0.0
        remaining = float(base)
        description = []
        for seg in segments:
            if remaining <= 0:
                break
            pct = float(seg.get("pct", 0))
            upto = seg.get("up_to")
            if upto is None:
                limit += remaining * pct / 100.0
                description.append(f"{_fmt(pct)}% sobre o excedente")
                remaining = 0
                break
            upto = float(upto)
            if base <= upto:
                limit += remaining * pct / 100.0
                description.append(f"{_fmt(pct)}% sobre a area do lote (ate {upto:g} m²)")
                remaining = 0
                break
            limit += upto * pct / 100.0
            description.append(f"{_fmt(pct)}% sobre os primeiros {upto:g} m²")
            remaining = base - upto

        result["computed"] = _round(actual)
        result["computed_display"] = f"{_fmt(actual)} m²"
        result["limit_display"] = "; ".join(description)
        result["allowance"] = {
            "label": "Area permeavel minima (" + "; ".join(description) + ")",
            "value": _round(limit),
            "unit": "m²",
            "display": f"{_fmt(limit)} m²",
        }
        if actual >= limit - EPS:
            result["status"] = CONFORME
            result["message"] = (
                f"Area permeavel de {_fmt(actual)} m² atende o minimo de {_fmt(limit)} m²."
            )
        else:
            result["status"] = NAO_CONFORME
            result["message"] = (
                f"Area permeavel de {_fmt(actual)} m² e inferior ao minimo de {_fmt(limit)} m² "
                f"(faltam {_fmt(limit - actual)} m²)."
            )
        return result

    if ctype == "setback_from_height":
        """Afastamento proporcional a altura da edificacao."""
        field = spec.get("field", "proposed_setback_side")
        height_field = spec.get("height_field", "building_height")
        height = facts.get(height_field)
        ratio = spec.get("ratio")
        ratio = float(ratio) if ratio is not None else float(value) / 100.0
        applies_above = spec.get("applies_above")

        if height is None:
            result["status"] = PENDENTE
            result["message"] = f"Informe '{height_field}' para verificar o afastamento."
            return result

        if applies_above is not None and height <= float(applies_above):
            result["status"] = NAO_APLICAVEL
            result["message"] = (
                f"Afastamento de {_fmt(ratio * 100)}% da altura aplicavel acima de "
                f"{_fmt(applies_above)} m; edificacao com {_fmt(height)} m nao atinge o limite."
            )
            return result

        proposed = facts.get(field)
        if proposed is None:
            result["status"] = PENDENTE
            result["message"] = f"Informe '{field}' para verificar o afastamento."
            return result

        required = height * ratio
        result["computed"] = _round(proposed)
        result["computed_display"] = f"{_fmt(proposed)} m"
        result["allowance"] = {
            "label": f"Afastamento minimo ({_fmt(ratio * 100)}% da altura de {_fmt(height)} m)",
            "value": _round(required),
            "unit": "m",
            "display": f"{_fmt(required)} m",
        }
        if proposed >= required - EPS:
            result["status"] = CONFORME
            result["message"] = (
                f"Afastamento de {_fmt(proposed)} m atende o minimo de {_fmt(required)} m "
                f"({_fmt(ratio * 100)}% da altura)."
            )
        else:
            result["status"] = NAO_CONFORME
            result["message"] = (
                f"Afastamento de {_fmt(proposed)} m e inferior ao minimo de {_fmt(required)} m "
                f"({_fmt(ratio * 100)}% da altura de {_fmt(height)} m)."
            )
        return result

    if ctype == "max_area_per_unit":
        field = spec.get("field", "lot_area")
        divisor_field = spec.get("divisor", "units")
        actual = facts.get(field)
        divisor = facts.get(divisor_field)
        if actual is None or divisor in (None, 0):
            result["status"] = PENDENTE
            result["message"] = f"Informe '{field}' e '{divisor_field}' para verificar o limite."
            return result
        limit = value * divisor
        result["computed"] = _round(actual)
        result["computed_display"] = f"{_fmt(actual)} m²"
        result["allowance"] = {
            "label": "Área máxima de terreno para o número de unidades informado",
            "value": _round(limit),
            "unit": "m²",
            "display": f"{_fmt(limit)} m²",
        }
        if actual <= limit + EPS:
            result["status"] = CONFORME
            result["message"] = f"Área de {_fmt(actual)} m² dentro do limite de {_fmt(limit)} m²."
        else:
            result["status"] = NAO_CONFORME
            result["message"] = (
                f"Área de {_fmt(actual)} m² excede o limite de {_fmt(limit)} m² "
                f"para {_fmt(divisor)} unidade(s)."
            )
        return result

    result["status"] = ATENCAO
    result["message"] = f"Tipo de verificacao nao suportado: {ctype}."
    return result
