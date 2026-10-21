"""Testes da cidade de demonstração (dados fictícios) e da API."""

from __future__ import annotations

from app.engine.analyze import analyze
from app.models import City, Question, Rule, Source, Zone


def _run(db, slug, answers, zone=None):
    city = db.query(City).filter(City.slug == slug).one()
    zones = db.query(Zone).filter(Zone.city_id == city.id).order_by(Zone.ord).all()
    questions = db.query(Question).filter(Question.city_id == city.id).order_by(Question.ord).all()
    rules = db.query(Rule).filter(Rule.city_id == city.id).order_by(Rule.ord).all()
    sources = db.query(Source).filter(Source.city_id == city.id).all()
    return analyze(city, zones, questions, rules, sources, answers, zone)


def _check(result, key):
    return next(c for c in result["checks"] if c["key"] == key)


def test_zona_deduzida_pelo_questionario(db):
    result = _run(db, "cidade-exemplo", {"use": "comercial", "lot_area": 400})
    assert result["zone"]["code"] == "ZC"
    assert result["zone_resolution"]["method"] == "questionario"


def test_zona_industrial_pelo_questionario(db):
    result = _run(db, "cidade-exemplo", {"use": "industrial", "lot_area": 2000})
    assert result["zone"]["code"] == "ZI"


def test_zona_residencial_padrao(db):
    result = _run(db, "cidade-exemplo", {"use": "residencial", "lot_area": 400})
    assert result["zone"]["code"] == "ZR"


def test_zona_por_geolocalizacao(db):
    """Ponto dentro do polígono ZC do GeoJSON da cidade de exemplo."""
    result = _run(db, "cidade-exemplo", {"lat": -23.5550, "lon": -46.6150, "lot_area": 400})
    assert result["zone"]["code"] == "ZC"
    assert result["zone_resolution"]["method"] == "geo"


def test_verificacao_de_permeabilidade(db):
    conforme = _run(
        db,
        "cidade-exemplo",
        {
            "use": "residencial",
            "lot_area": 500,
            "permeable_area": 120,
            "footprint_area": 200,
            "total_built_area": 600,
        },
    )
    assert _check(conforme, "min_permeable_pct")["status"] == "conforme"

    nao_conforme = _run(
        db,
        "cidade-exemplo",
        {
            "use": "residencial",
            "lot_area": 500,
            "permeable_area": 60,
            "footprint_area": 200,
            "total_built_area": 600,
        },
    )
    check = _check(nao_conforme, "min_permeable_pct")
    assert check["status"] == "nao_conforme"
    assert check["allowance"]["value"] == 100  # 20% de 500 m²


def test_zona_nao_definida_sem_respostas(db):
    result = _run(db, "cidade-exemplo", {})
    assert result["zone"] is None
    assert "missing_required" in result


# ------------------------------------------------------------------- API
def test_api_lista_cidades(client):
    data = client.get("/api/cities").json()
    assert {c["slug"] for c in data["items"]} == {"sao-paulo", "cidade-exemplo"}


def test_api_detalhe_da_cidade(client):
    data = client.get("/api/cities/sao-paulo").json()
    assert data["name"] == "São Paulo"
    assert len(data["zones"]) > 30
    assert any(z["code"] == "ZM" for z in data["zones"])
    assert data["sources"][0]["url"].startswith("https://")


def test_api_cidade_inexistente(client):
    assert client.get("/api/cities/nao-existe").status_code == 404


def test_api_analise(client):
    resp = client.post(
        "/api/analyze",
        json={
            "city": "sao-paulo",
            "zone": "ZM",
            "answers": {
                "lot_area": 1000,
                "use": "residencial",
                "footprint_area": 400,
                "total_built_area": 1200,
                "floors": 3,
                "floor_height": 3,
                "proposed_setback_front": 5,
                "proposed_setback_side": 3,
                "proposed_setback_back": 3,
            },
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["zone"]["code"] == "ZM"
    assert data["summary"]["status"] in {"conforme", "pendente"}
    assert data["disclaimer"]


def test_api_ciclo_de_vida_de_analise_salva(client):
    resp = client.post(
        "/api/projects",
        json={
            "city": "cidade-exemplo",
            "answers": {"use": "comercial", "lot_area": 300},
            "name": "Teste",
        },
    )
    assert resp.status_code == 200
    project_id = resp.json()["id"]

    listed = client.get("/api/projects").json()
    assert any(p["id"] == project_id for p in listed["items"])

    fetched = client.get(f"/api/projects/{project_id}").json()
    assert fetched["name"] == "Teste"
    assert fetched["result"]["zone"]["code"] == "ZC"

    assert client.delete(f"/api/projects/{project_id}").status_code == 200
    assert client.get(f"/api/projects/{project_id}").status_code == 404


def test_api_health_e_pagina(client):
    assert client.get("/api/health").json()["status"] == "ok"
    assert "LegisUrb" in client.get("/").text
