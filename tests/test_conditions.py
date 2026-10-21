"""Testes do motor de condições e fatos."""

from __future__ import annotations

from app.engine.conditions import match_condition, missing_facts
from app.engine.facts import coerce


def test_igualdade_escalar():
    assert match_condition({"use": "residencial"}, {"use": "residencial"})
    assert not match_condition({"use": "residencial"}, {"use": "comercial"})


def test_operadores_numericos():
    facts = {"lot_area": 450.0, "height": 12.0}
    assert match_condition({"lot_area": {"lt": 500}}, facts)
    assert match_condition({"lot_area": {"gte": 500}}, {"lot_area": 500})
    assert not match_condition({"lot_area": {"gte": 500}}, facts)
    assert match_condition({"height": {"between": [10, 20]}}, facts)


def test_operadores_de_conjunto():
    facts = {"use": "comercial"}
    assert match_condition({"use": {"in": ["comercial", "misto"]}}, facts)
    assert match_condition({"use": {"not_in": ["industrial"]}}, facts)


def test_fato_ausente_nao_satisfaz_condicao():
    assert not match_condition({"lot_area": {"lt": 500}}, {})
    assert missing_facts({"lot_area": {"lt": 500}}, {}) == ["lot_area"]


def test_coerce():
    assert coerce("12,5", "number") == 12.5
    assert coerce("sim", "boolean") is True
    assert coerce("nao", "boolean") is False
    assert coerce(3, "text") == "3"
