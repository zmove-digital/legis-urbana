"""Testes do motor de análise sobre a legislação real de Porto Alegre.

Base legal: Lei Complementar nº 1.076/2026 (LUOS) e o Anexo 2 (quadros de
regime urbanístico por ZOT). Se um teste quebrar, provavelmente o dado legal
mudou ou o cadastro foi alterado.
"""

from __future__ import annotations

import pytest

from app.engine.analyze import analyze
from app.models import City, Parameter, Question, Rule, Source, Zone

BASE = {
    "lot_area": 1200,
    "footprint_area": 400,
    "total_built_area": 1800,
    "use": "residencial",
    "floors": 4,
    "floor_height": 3.0,
    "proposed_setback_front": 4,
    "proposed_setback_side": 3,
    "proposed_setback_back": 3,
    "permeable_area": 300,
    "via_arterial": False,
    "terreno_origem_parcelamento": True,
    "parcelamento_equipamentos": False,
}


def _city_bundle(db, slug):
    city = db.query(City).filter(City.slug == slug).one()
    zones = db.query(Zone).filter(Zone.city_id == city.id).order_by(Zone.ord).all()
    questions = db.query(Question).filter(Question.city_id == city.id).order_by(Question.ord).all()
    rules = db.query(Rule).filter(Rule.city_id == city.id).order_by(Rule.ord).all()
    sources = db.query(Source).filter(Source.city_id == city.id).all()
    return city, zones, questions, rules, sources


def _run(db, answers=None, zone=None):
    city, zones, questions, rules, sources = _city_bundle(db, "porto-alegre")
    return analyze(
        city=city,
        zones=zones,
        questions=questions,
        rules=rules,
        sources=sources,
        answers={**BASE, **(answers or {})},
        explicit_zone=zone,
    )


def _check(result, key):
    return next(c for c in result["checks"] if c["key"] == key)


def _param(result, key):
    return next(p for p in result["parameters"] if p["key"] == key)


# --------------------------------------------------------------------- cadastro
def test_zonas_e_sub_setores_cadastrados(db):
    cidade = db.query(City).filter(City.slug == "porto-alegre").one()
    zonas = db.query(Zone).filter(Zone.city_id == cidade.id).order_by(Zone.ord).all()
    codigos = [z.code for z in zonas]
    assert len(codigos) == 29
    for base in ("ZOT 1", "ZOT 2", "ZOT 3", "ZOT 4", "ZOT 5", "ZOT 6", "ZOT 7", "ZOT 8"):
        assert base in codigos
    for sub in ("A", "B", "C", "D", "E", "F", "G"):
        assert f"ZOT 8.1{sub}" in codigos
    assert "ZOT 8.2A" in codigos and "ZOT 8.2B" in codigos
    for sub in ("A", "B", "C", "D"):
        assert f"ZOT 8.3{sub}" in codigos
    for zot in range(9, 17):
        assert f"ZOT {zot}" in codigos


def test_zonas_com_sub_setores_sao_agrupadas(db):
    cidade = db.query(City).filter(City.slug == "porto-alegre").one()
    zonas = {z.code: z.group_name for z in db.query(Zone).filter(Zone.city_id == cidade.id).all()}
    assert zonas["ZOT 8.1A"] == zonas["ZOT 8.1G"] != ""
    assert zonas["ZOT 8.2A"] == zonas["ZOT 8.2B"] != ""
    assert zonas["ZOT 8.3A"] == zonas["ZOT 8.3D"] != ""
    assert not zonas["ZOT 4"]


# ------------------------------------------------------- quadro do Anexo 2
@pytest.mark.parametrize(
    ("code", "esperado"),
    [
        (
            "ZOT 1",
            {
                "max_height": 9,
                "setback_front": 4,
                "min_permeable_pct": 30,
                "tp_factor_conversion": 30,
                "lot_min_area": 150,
                "lot_min_frontage": 5,
            },
        ),
        (
            "ZOT 2",
            {
                "max_height": 9,
                "min_permeable_pct": 30,
                "tp_factor_conversion": 50,
                "lot_min_area": 150,
            },
        ),
        (
            "ZOT 3",
            {"ca_base": 2, "ca_max": 3, "max_height": 12.5, "min_permeable_pct": 20},
        ),
        (
            "ZOT 4",
            {
                "ca_base": 2,
                "ca_max": 4,
                "max_height": 18,
                "setback_front": 4,
                "setback_side_pct": 18,
                "setback_back_pct": 18,
                "min_permeable_pct": 20,
                "tp_factor_conversion": 50,
                "lot_min_area": 125,
            },
        ),
        ("ZOT 5", {"ca_base": 2.4, "ca_max": 4, "max_height": 33}),
        ("ZOT 6", {"ca_base": 2.4, "ca_max": 5, "max_height": 42}),
        ("ZOT 7", {"ca_base": 2.4, "ca_max": 6.5, "max_height": 60}),
        ("ZOT 8", {"ca_base": 2.4, "ca_max": 7.5, "max_height": 90}),
        ("ZOT 9", {"ca_base": 2, "ca_max": 4, "max_height": 18}),
        ("ZOT 10", {"ca_base": 2.4, "ca_max": 4, "max_height": 33}),
        ("ZOT 11", {"ca_base": 2.4, "ca_max": 5, "max_height": 42}),
        ("ZOT 12", {"ca_base": 3.0, "ca_max": 6.5, "max_height": 60}),
        ("ZOT 13", {"ca_base": 3.0, "ca_max": 6.5, "max_height": 60}),
        ("ZOT 14", {"ca_base": 0.5, "max_height": 9, "tp_factor_conversion": 20}),
        ("ZOT 15", {"ca_base": 0.3, "max_height": 9, "tp_factor_conversion": 20}),
        ("ZOT 16", {"ca_base": 0.3, "max_height": 9, "tp_factor_conversion": 20}),
        ("ZOT 8.1A", {"ca_base": 3.6, "ca_max": 6.5, "max_height": 60}),
        ("ZOT 8.1B", {"ca_base": 3.6, "ca_max": 7, "max_height": 75}),
        ("ZOT 8.1C", {"ca_base": 3.6, "ca_max": 7.5, "max_height": 90}),
        ("ZOT 8.1D", {"ca_base": 3.6, "ca_max": 11.5, "max_height": 100}),
        ("ZOT 8.1E", {"ca_base": 3.6, "ca_max": 11.5, "max_height": 130}),
        ("ZOT 8.1F", {"ca_base": 1.15, "max_height": 6.7}),
        ("ZOT 8.1G", {"ca_base": 3.6, "ca_max": 6}),
        ("ZOT 8.2A", {"ca_base": 3.6, "ca_max": 7.5, "max_height": 130}),
        ("ZOT 8.2B", {"ca_base": 3.6, "ca_max": 6.5, "max_height": 60}),
        ("ZOT 8.3A", {"ca_base": 3.0, "ca_max": 7.5, "max_height": 130}),
        ("ZOT 8.3B", {"ca_base": 3.0, "ca_max": 7.5, "max_height": 90}),
        ("ZOT 8.3C", {"ca_base": 3.0, "ca_max": 7.5, "max_height": 90}),
        ("ZOT 8.3D", {"ca_base": 3.6, "ca_max": 6.5, "max_height": 60}),
    ],
)
def test_quadro_do_anexo_2(db, code, esperado):
    """Valores do Anexo 2 da LC 1076/2026 (quadros de edificacoes por ZOT)."""
    cidade = db.query(City).filter(City.slug == "porto-alegre").one()
    zona = db.query(Zone).filter(Zone.city_id == cidade.id, Zone.code == code).one()
    params = {p.key: p for p in db.query(Parameter).filter(Parameter.zone_id == zona.id).all()}
    for chave, valor in esperado.items():
        assert params[chave].value_num == valor, f"{code}.{chave}"


def test_ca_das_zots_1_e_2_e_condicional(db):
    """Art. 24, paragrafo 4: o CA das ZOTs 1 e 2 depende da origem do lote."""
    cidade = db.query(City).filter(City.slug == "porto-alegre").one()
    zona = db.query(Zone).filter(Zone.city_id == cidade.id, Zone.code == "ZOT 1").one()
    params = {p.key: p for p in db.query(Parameter).filter(Parameter.zone_id == zona.id).all()}
    for chave, valores in (("ca_base", {0.75, 1.5}), ("ca_max", {1.25, 2.5})):
        assert params[chave].value_num is None
        alternativas = params[chave].alternatives
        assert len(alternativas) == 4
        assert {a["value"] for a in alternativas} == valores


def test_zot_1_tem_afastamento_lateral_isento(db):
    cidade = db.query(City).filter(City.slug == "porto-alegre").one()
    zona = db.query(Zone).filter(Zone.city_id == cidade.id, Zone.code == "ZOT 1").one()
    params = {p.key: p for p in db.query(Parameter).filter(Parameter.zone_id == zona.id).all()}
    assert params["setback_side_pct"].value_num is None
    assert params["setback_back_pct"].value_num is None
    assert params["setback_side_pct"].notes


# --------------------------------------------------------------- volumetria
def test_afastamento_de_18_por_cento_da_altura_acima_de_12_5m(db):
    """Anexo 2, nota 6: 18% da altura a partir da RN, aplicavel acima de 12,5 m."""
    baixo = _run(db, {"floors": 4}, zone="ZOT 4")
    assert _check(baixo, "setback_side_pct")["status"] == "nao_aplicavel"

    alto = _run(db, {"floors": 7, "proposed_setback_side": 3}, zone="ZOT 4")
    check = _check(alto, "setback_side_pct")
    assert check["status"] == "nao_conforme"
    assert check["allowance"]["value"] == pytest.approx(0.18 * 21)

    conforme = _run(db, {"floors": 7, "proposed_setback_side": 4}, zone="ZOT 4")
    assert _check(conforme, "setback_side_pct")["status"] == "conforme"


def test_altura_informada_tem_precedencia_do_calculo(db):
    result = _run(db, {"floors": 4, "building_height": 30}, zone="ZOT 4")
    assert result["facts"]["building_height"] == 30


# --------------------------------------------------------- permeabilidade
def test_taxa_de_permeabilidade_em_degraus(db):
    """Acima de 1.500 m2: 20% sobre os primeiros 1.500 m2 e 30% sobre o excedente."""
    pequeno = _run(db, {"lot_area": 1200, "permeable_area": 240}, zone="ZOT 4")
    assert _check(pequeno, "min_permeable_pct")["allowance"]["value"] == pytest.approx(240)

    medio = _run(db, {"lot_area": 3000, "permeable_area": 750}, zone="ZOT 4")
    assert _check(medio, "min_permeable_pct")["allowance"]["value"] == pytest.approx(750)

    grande = _run(db, {"lot_area": 5000, "permeable_area": 1350}, zone="ZOT 4")
    assert _check(grande, "min_permeable_pct")["allowance"]["value"] == pytest.approx(1350)

    insuficiente = _run(db, {"lot_area": 5000, "permeable_area": 1000}, zone="ZOT 4")
    assert _check(insuficiente, "min_permeable_pct")["status"] == "nao_conforme"


def test_dispensa_de_tp_em_lote_de_ate_150m2(db):
    """Art. 79, III: dispensa da TP em terreno com area de ate 150 m2."""
    result = _run(db, {"lot_area": 120, "permeable_area": 0}, zone="ZOT 4")
    assert _param(result, "min_permeable_pct")["value"] == 0
    assert any("79" in (r["basis"] or {}).get("ref", "") for r in result["applied_rules"])


def test_dispensa_de_tp_no_centro_historico(db):
    result = _run(db, {"centro_historico": True}, zone="ZOT 4")
    assert _param(result, "min_permeable_pct")["value"] == 0


# ------------------------------------------- coeficiente de aproveitamento
def test_ca_reduzido_em_50_por_cento_sem_parcelamento(db):
    """Art. 24, paragrafo 4, III: reducacao de 50% nas ZOTs 1 e 2."""
    reduzido = _run(
        db,
        {"lot_area": 1000, "terreno_origem_parcelamento": False},
        zone="ZOT 1",
    )
    assert _param(reduzido, "ca_max")["value"] == pytest.approx(1.25)
    assert _param(reduzido, "ca_base")["value"] == pytest.approx(0.75)

    integral = _run(
        db,
        {"lot_area": 1000, "terreno_origem_parcelamento": True},
        zone="ZOT 1",
    )
    assert _param(integral, "ca_max")["value"] == pytest.approx(2.5)
    assert _param(integral, "ca_base")["value"] == pytest.approx(1.5)

    grande = _run(
        db,
        {"lot_area": 30000, "terreno_origem_parcelamento": False},
        zone="ZOT 1",
    )
    assert _param(grande, "ca_max")["value"] == pytest.approx(2.5)

    outra_zona = _run(
        db,
        {"lot_area": 1000, "terreno_origem_parcelamento": False},
        zone="ZOT 4",
    )
    assert _param(outra_zona, "ca_max")["value"] == pytest.approx(4)


def test_ca_pendente_quando_falta_a_origem_do_lote(db):
    """Sem a informacao sobre parcelamento o valor nao e escolhido em silencio."""
    result = _run(db, {"terreno_origem_parcelamento": None}, zone="ZOT 1")
    assert _check(result, "ca_max")["status"] == "pendente"


def test_base_de_calculo_limitada_ao_modulo_de_fracionamento(db):
    """Art. 24, II: base de calculo limitada ao Modulo de Fracionamento (3.000 m2)."""
    result = _run(
        db,
        {"lot_area": 20000, "total_built_area": 6000},
        zone="ZOT 1",
    )
    ca = _check(result, "ca_max")
    assert ca["allowance"]["value"] == pytest.approx(2.5 * 3000)

    com_equipamentos = _run(
        db,
        {"lot_area": 20000, "total_built_area": 6000, "parcelamento_equipamentos": True},
        zone="ZOT 1",
    )
    ca = _check(com_equipamentos, "ca_max")
    assert ca["allowance"]["value"] == pytest.approx(2.5 * 20000)


def test_base_de_calculo_integral_fora_das_zots_1_e_2(db):
    result = _run(
        db,
        {"lot_area": 20000, "total_built_area": 6000},
        zone="ZOT 4",
    )
    ca = _check(result, "ca_max")
    assert ca["allowance"]["value"] == pytest.approx(4 * 20000)


def test_area_isenta_e_descontada_do_calculo_do_ca(db):
    """Art. 73: areas isentas nao integrao o calculo do potencial construtivo."""
    result = _run(
        db,
        {"lot_area": 1000, "total_built_area": 2000, "area_isenta_ca": 200},
        zone="ZOT 4",
    )
    ca = _check(result, "ca_max")
    assert ca["computed"] == pytest.approx(1.8)


# ------------------------------------------------------------ recuo de jardim
def test_recuo_de_jardim_de_4m_e_12m_segundo_a_via(db):
    """Anexo 2.14 a 2.16: 4 m, ou 12 m em vias estruturantes ou arteriais."""
    comum = _run(db, {"via_arterial": False}, zone="ZOT 14")
    assert _param(comum, "setback_front")["value"] == 4

    arterial = _run(db, {"via_arterial": True}, zone="ZOT 14")
    assert _param(arterial, "setback_front")["value"] == 12


def test_recuo_de_jardim_pendente_sem_a_informacao_da_via(db):
    result = _run(db, {"via_arterial": None}, zone="ZOT 14")
    assert _check(result, "setback_front")["status"] == "pendente"


# -------------------------------------------------------------- casos especiais
def test_regime_de_his_na_zot_14(db):
    """Art. 19, paragrafo 2: regime urbanistico da ZOT 1 para HIS na ZOT 14."""
    result = _run(db, {"his": True}, zone="ZOT 14")
    assert _param(result, "ca_base")["value"] == pytest.approx(1.5)
    assert _param(result, "ca_max")["value"] == pytest.approx(2.5)
    assert any("19" in (r["basis"] or {}).get("ref", "") for r in result["applied_rules"])


def test_regime_especial_4d_na_zot_82(db):
    """Anexo 2.8.2, notas 3 e 4: CA basico 7,5 e maximo 13 no Regime +4D."""
    result = _run(db, {"regime_4d": True}, zone="ZOT 8.2A")
    assert _param(result, "ca_base")["value"] == pytest.approx(7.5)
    assert _param(result, "ca_max")["value"] == pytest.approx(13)
    assert any("4D" in r["message"] or "4D" in r["title"] for r in result["applied_rules"])


def test_ca_maximo_sem_valor_numerico_fica_pendente(db):
    """Anexo 2.14: 'Ajuste / TDC' nao e um limite numerico."""
    result = _run(db, zone="ZOT 14")
    check = _check(result, "ca_max")
    assert check["status"] == "pendente"
    assert "Anexo 2.14" in check["message"]


def test_altura_do_sitio_historico_fica_pendente(db):
    """Anexo 2.8.1: altura 'ORGANO COMPETENTE' (IPHAN/IPHAE)."""
    result = _run(db, zone="ZOT 8.1G")
    check = _check(result, "max_height")
    assert check["status"] == "pendente"
    assert "ORGANO COMPETENTE" in check["message"]


def test_zonas_com_taxa_de_permeabilidade_isenta(db):
    """Centro Historico (Anexo 2.8.1): taxa de permeabilidade isenta."""
    result = _run(db, {"permeable_area": 0}, zone="ZOT 8.1A")
    check = _check(result, "min_permeable_pct")
    assert check["status"] == "nao_aplicavel"
    assert "ISENT" in check["message"].upper()


# ------------------------------------------------------------- base legal
def test_fontes_da_luos_e_do_anexo(db):
    cidade = db.query(City).filter(City.slug == "porto-alegre").one()
    fontes = {s.key: s for s in db.query(Source).filter(Source.city_id == cidade.id).all()}
    assert fontes["luos"].url.endswith("/norma/51486")
    assert fontes["luos"].consolidated_as_of
    assert fontes["luos_anexo2"].url.endswith(".pdf")
    assert fontes["luos_anexo2"].consolidated_as_of
    assert fontes["pdus"].url.endswith("/norma/51485")
    assert "refer" in (fontes["pdus"].notes or "").lower()


def test_toda_regra_tem_base_legal_valida(db):
    cidade = db.query(City).filter(City.slug == "porto-alegre").one()
    chaves = {s.key for s in db.query(Source).filter(Source.city_id == cidade.id).all()}
    for regra in db.query(Rule).filter(Rule.city_id == cidade.id).all():
        assert regra.basis and regra.basis.get("source") in chaves, regra.code
        assert regra.basis.get("ref"), regra.code


def test_todo_parametro_tem_base_legal(db):
    cidade = db.query(City).filter(City.slug == "porto-alegre").one()
    chaves = {s.key for s in db.query(Source).filter(Source.city_id == cidade.id).all()}
    for param in db.query(Parameter).filter(Parameter.city_id == cidade.id).all():
        assert param.basis and param.basis.get("source") in chaves, param.key
        assert param.basis.get("ref"), param.key


# ------------------------------------------------------------------- API
def test_api_detalhe_da_cidade(client):
    data = client.get("/api/cities/porto-alegre").json()
    assert data["name"] == "Porto Alegre"
    assert data["uf"] == "RS"
    assert len(data["zones"]) == 29
    assert data["zone_selection"]["method"] == "manual"
    assert data["sources"][0]["url"].startswith("https://")


def test_api_analise_de_porto_alegre(client):
    resp = client.post(
        "/api/analyze",
        json={
            "city": "porto-alegre",
            "zone": "ZOT 4",
            "answers": {
                "lot_area": 1200,
                "use": "residencial",
                "footprint_area": 400,
                "total_built_area": 1800,
                "floors": 4,
                "floor_height": 3,
                "proposed_setback_front": 4,
                "proposed_setback_side": 3,
                "proposed_setback_back": 3,
                "permeable_area": 300,
                "via_arterial": False,
                "terreno_origem_parcelamento": True,
                "parcelamento_equipamentos": False,
            },
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["zone"]["code"] == "ZOT 4"
    assert next(c for c in data["checks"] if c["key"] == "ca_max")["status"] == "conforme"
    assert any(s["key"] == "luos_anexo2" for s in data["sources"])
