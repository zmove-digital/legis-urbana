"""Testes do motor de análise sobre a legislação real de São Paulo.

Os valores esperados são os do Anexo 3 - Quadro 3 da Lei nº 16.402/2016
(texto compilado com as Leis nº 18.081/2024 e nº 18.177/2024). Se um teste
quebrar, provavelmente o dado legal mudou ou o cadastro foi alterado.
"""

from __future__ import annotations

import pytest

from app.engine.analyze import analyze
from app.models import City, Parameter, Question, Rule, Source, Zone


def _city_bundle(db, slug):
    city = db.query(City).filter(City.slug == slug).one()
    zones = db.query(Zone).filter(Zone.city_id == city.id).order_by(Zone.ord).all()
    questions = db.query(Question).filter(Question.city_id == city.id).order_by(Question.ord).all()
    rules = db.query(Rule).filter(Rule.city_id == city.id).order_by(Rule.ord).all()
    sources = db.query(Source).filter(Source.city_id == city.id).all()
    return city, zones, questions, rules, sources


def _run(db, slug, answers, zone=None):
    city, zones, questions, rules, sources = _city_bundle(db, slug)
    return analyze(
        city=city,
        zones=zones,
        questions=questions,
        rules=rules,
        sources=sources,
        answers=answers,
        explicit_zone=zone,
    )


def _check(result, key):
    return next(c for c in result["checks"] if c["key"] == key)


def _param(result, key):
    return next(p for p in result["parameters"] if p["key"] == key)


# --------------------------------------------------------------------- base
def test_seed_carrega_as_cidades_cadastradas(db):
    cities = db.query(City).all()
    assert {c.slug for c in cities} == {"sao-paulo", "porto-alegre", "cidade-exemplo"}


def test_quadro3_zona_mista(db):
    """ZM: CA 2 / CA base 1 / CA min 0,3 / TO 0,85 e 0,70 / altura 28 / recuo 5 / lateral 3."""
    cidade = db.query(City).filter(City.slug == "sao-paulo").one()
    zona = db.query(Zone).filter(Zone.city_id == cidade.id, Zone.code == "ZM").one()
    params = {p.key: p for p in db.query(Parameter).filter(Parameter.zone_id == zona.id).all()}
    assert params["ca_max"].value_num == 2
    assert params["ca_base"].value_num == 1
    assert params["ca_min"].value_num == 0.3
    assert params["max_height"].value_num == 28
    assert params["setback_front"].value_num == 5
    assert params["setback_side_back"].value_num == 3


def test_quadro3_valores_de_outras_zonas(db):
    esperado = {
        "ZEU": {"ca_max": 4, "max_height": None},
        "ZC": {"ca_max": 2, "max_height": 48, "setback_front": 5},
        "ZPR": {"ca_max": 1, "max_height": 10, "ca_min": 0.05},
        "ZPI-2": {"ca_max": 1.5, "max_height": 28},
        "ZEPAM": {"ca_max": 0.1, "ca_base": 0.1},
        "AC-2": {"ca_max": 0.4, "max_height": 10},
    }
    cidade = db.query(City).filter(City.slug == "sao-paulo").one()
    for code, valores in esperado.items():
        zona = db.query(Zone).filter(Zone.city_id == cidade.id, Zone.code == code).one()
        params = {p.key: p for p in db.query(Parameter).filter(Parameter.zone_id == zona.id).all()}
        for chave, valor in valores.items():
            if valor is None:
                continue
            assert params[chave].value_num == valor, f"{code}.{chave}"


def test_to_alternativa_por_area_do_lote(db):
    """TO do Quadro 3: 0,85 para lotes até 500 m² e 0,70 para lotes >= 500 m²."""
    base = {"use": "residencial", "footprint_area": 300, "total_built_area": 900}
    pequeno = _run(db, "sao-paulo", {**base, "lot_area": 400}, zone="ZM")
    grande = _run(db, "sao-paulo", {**base, "lot_area": 800}, zone="ZM")
    assert _param(pequeno, "to_max")["value"] == 0.85
    assert _param(grande, "to_max")["value"] == 0.70


def test_ca_reduzido_na_zeis3_lote_pequeno(db):
    """Nota (g) do Quadro 3: CA máx 2 quando o lote tem menos de 500 m²."""
    pequeno = _run(db, "sao-paulo", {"lot_area": 400, "use": "residencial"}, zone="ZEIS-3")
    grande = _run(db, "sao-paulo", {"lot_area": 1200, "use": "residencial"}, zone="ZEIS-3")
    assert _param(pequeno, "ca_max")["value"] == 2
    assert _param(grande, "ca_max")["value"] == 4


def test_zeis1_nota_f_um_mil_m2(db):
    pequeno = _run(db, "sao-paulo", {"lot_area": 900, "use": "residencial"}, zone="ZEIS-1")
    grande = _run(db, "sao-paulo", {"lot_area": 1500, "use": "residencial"}, zone="ZEIS-1")
    assert _param(pequeno, "ca_max")["value"] == 2
    assert _param(grande, "ca_max")["value"] == 2.5


# --------------------------------------------------------------- verificações
def test_verificacao_de_ca_e_to(db):
    result = _run(
        db,
        "sao-paulo",
        {
            "lot_area": 1000,
            "use": "residencial",
            "footprint_area": 400,
            "total_built_area": 1200,
            "floors": 3,
            "floor_height": 3,
        },
        zone="ZM",
    )
    ca = _check(result, "ca_max")
    assert ca["status"] == "conforme"
    assert ca["allowance"]["value"] == 2000  # CA 2 x 1000 m²

    to = _check(result, "to_max")
    assert to["status"] == "conforme"
    assert to["allowance"]["value"] == 700  # TO 0,70 x 1000 m²

    altura = _check(result, "max_height")
    assert altura["status"] == "conforme"
    assert result["facts"]["building_height"] == 9.0


def test_nao_conformidade_de_ca(db):
    result = _run(
        db,
        "sao-paulo",
        {"lot_area": 1000, "use": "residencial", "total_built_area": 2500, "footprint_area": 500},
        zone="ZM",
    )
    ca = _check(result, "ca_max")
    assert ca["status"] == "nao_conforme"
    assert result["summary"]["status"] == "nao_conforme"


def test_dado_pendente_quando_falta_area(db):
    result = _run(db, "sao-paulo", {"lot_area": 1000, "use": "residencial"}, zone="ZM")
    ca = _check(result, "ca_max")
    assert ca["status"] == "pendente"


def test_dispensa_de_recuos_ate_10m(db):
    """Art. 66, I: recuos laterais e de fundo dispensados até 10 m de altura."""
    baixo = _run(
        db,
        "sao-paulo",
        {"lot_area": 600, "use": "residencial", "floors": 2, "floor_height": 3},
        zone="ZM",
    )
    assert _param(baixo, "setback_side_back")["value"] == 0
    assert any("66" in (r["basis"] or {}).get("ref", "") for r in baixo["applied_rules"])

    alto = _run(
        db,
        "sao-paulo",
        {"lot_area": 600, "use": "residencial", "floors": 4, "floor_height": 3},
        zone="ZM",
    )
    assert _param(alto, "setback_side_back")["value"] == 3


def test_dispensa_nao_se_aplica_em_zpi1(db):
    result = _run(
        db,
        "sao-paulo",
        {"lot_area": 600, "use": "industrial", "floors": 2, "floor_height": 3},
        zone="ZPI-1",
    )
    assert _param(result, "setback_side_back")["value"] == 3


def test_recuo_frontal_dispensado_com_passeio_de_5m(db):
    result = _run(
        db,
        "sao-paulo",
        {"lot_area": 600, "use": "residencial", "sidewalk_width": 5},
        zone="ZM",
    )
    assert _param(result, "setback_front")["value"] == 0


def test_quota_ambiental_obrigatoria_ou_isenta(db):
    grande = _run(db, "sao-paulo", {"lot_area": 900, "use": "residencial"}, zone="ZM")
    pequeno = _run(db, "sao-paulo", {"lot_area": 300, "use": "residencial"}, zone="ZM")
    textos = lambda r: " ".join(x["message"] for x in r["requirements"])  # noqa: E731
    assert "QA" in textos(grande)
    assert "isento" in textos(pequeno).lower()


def test_permeabilidade_do_art_72_apenas_em_terreno_geotecnico(db):
    comum = _run(db, "sao-paulo", {"lot_area": 900, "use": "residencial"}, zone="ZM")
    especial = _run(
        db,
        "sao-paulo",
        {"lot_area": 900, "use": "residencial", "geotechnical_area": True},
        zone="ZM",
    )
    assert not any("art. 72" in r["message"] for r in comum["requirements"])
    assert any("20%" in r["message"] for r in especial["requirements"])


def test_toda_regra_tem_base_legal_valida(db):
    cidade = db.query(City).filter(City.slug == "sao-paulo").one()
    chaves = {s.key for s in db.query(Source).filter(Source.city_id == cidade.id).all()}
    for regra in db.query(Rule).filter(Rule.city_id == cidade.id).all():
        assert regra.basis and regra.basis.get("source") in chaves, regra.code


def test_todo_parametro_tem_base_legal(db):
    cidade = db.query(City).filter(City.slug == "sao-paulo").one()
    chaves = {s.key for s in db.query(Source).filter(Source.city_id == cidade.id).all()}
    for param in db.query(Parameter).filter(Parameter.city_id == cidade.id).all():
        assert param.basis and param.basis.get("source") in chaves, param.key


@pytest.mark.parametrize("slug", ["sao-paulo", "porto-alegre", "cidade-exemplo"])
def test_integridade_da_base_legal(db, slug):
    """Toda cidade cadastrada precisa de base legal referenciavel."""
    cidade = db.query(City).filter(City.slug == slug).one()
    chaves = {s.key for s in db.query(Source).filter(Source.city_id == cidade.id).all()}

    for param in db.query(Parameter).filter(Parameter.city_id == cidade.id).all():
        assert param.basis, f"{slug}: parametro {param.key} sem base legal"
        assert param.basis.get("source") in chaves, f"{slug}: {param.key} -> fonte inexistente"
        assert param.basis.get("ref"), f"{slug}: {param.key} sem referencia localizavel"

    for regra in db.query(Rule).filter(Rule.city_id == cidade.id).all():
        assert regra.basis, f"{slug}: regra {regra.code} sem base legal"
        assert regra.basis.get("source") in chaves, f"{slug}: {regra.code} -> fonte inexistente"

    # Nenhuma regra pode apontar para zona inexistente
    zonas = {z.code for z in db.query(Zone).filter(Zone.city_id == cidade.id).all()}
    for regra in db.query(Rule).filter(Rule.city_id == cidade.id).all():
        for zona in regra.applies_to_zones or []:
            assert zona in zonas, f"{slug}: regra {regra.code} -> zona inexistente {zona}"
        for zona in regra.exclude_zones or []:
            assert zona in zonas, f"{slug}: regra {regra.code} -> zona inexistente {zona}"


@pytest.mark.parametrize("slug", ["sao-paulo", "porto-alegre", "cidade-exemplo"])
def test_nenhuma_fonte_sem_url_e_titulo(db, slug):
    cidade = db.query(City).filter(City.slug == slug).one()
    for fonte in db.query(Source).filter(Source.city_id == cidade.id).all():
        assert fonte.title
        assert fonte.notes
        if not cidade.is_demo:
            # Cidades reais exigem link oficial e data de consolidacao
            assert fonte.url and fonte.url.startswith("https://"), fonte.key
        else:
            # Cidades ficticias sao marcadas como demonstracao
            assert not fonte.url, "cidade de demonstracao nao deve ter link oficial"


@pytest.mark.parametrize("slug", ["sao-paulo", "porto-alegre", "cidade-exemplo"])
def test_fonte_usada_como_base_tem_vigencia(db, slug):
    """Toda fonte que fundamenta um numero precisa de data de consolidacao.

    Fontes apenas de referencia (citadas em notas, sem fundamentar parametro)
    podem existir sem data, mas precisam dizer isso.
    """
    cidade = db.query(City).filter(City.slug == slug).one()
    usadas = set()
    for param in db.query(Parameter).filter(Parameter.city_id == cidade.id).all():
        if param.basis:
            usadas.add(param.basis.get("source"))
    for regra in db.query(Rule).filter(Rule.city_id == cidade.id).all():
        if regra.basis:
            usadas.add(regra.basis.get("source"))

    for fonte in db.query(Source).filter(Source.city_id == cidade.id).all():
        if fonte.key in usadas:
            assert fonte.consolidated_as_of, f"{slug}: fonte {fonte.key} sem consolidacao"
        else:
            assert "refer" in (fonte.notes or "").lower(), (
                f"{slug}: fonte {fonte.key} sem data de consolidacao e sem nota de referencia"
            )
