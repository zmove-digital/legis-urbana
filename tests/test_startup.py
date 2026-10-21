"""Testes de inicialização da aplicação (startup do servidor).

Regressão: o `lifespan` do FastAPI precisa estar ligado ao app. Sem isso o
servidor sobe sem criar o banco e sem carregar as cidades, e toda requisição
responde 500 ("no such table: cities") em uma instalação nova.
"""

from __future__ import annotations

import pytest
from sqlalchemy import inspect

from app.config import SEED_ON_STARTUP
from app.db import Base, engine
from app.main import app
from app.models import City, Source, Zone
from app.seed.loader import seed_all


def test_app_tem_lifespan_ligado():
    """O app precisa executar o lifespan (cria o banco e semeia as cidades)."""
    assert app.router.lifespan_context is not None, (
        "app sem lifespan: o banco nao seria criado no startup"
    )


def test_seed_esta_habilitado_por_padrao():
    assert SEED_ON_STARTUP is True


def test_banco_tem_as_tabelas_do_modelo():
    """As tabelas do ORM existem no banco em uso (create_all no startup)."""
    tabelas = set(inspect(engine).get_table_names())
    esperadas = set(Base.metadata.tables)
    assert esperadas <= tabelas


def test_seed_e_idempotente_e_carrega_todas_as_cidades(db):
    """Rodar o seed de novo nao duplica nem apaga nada."""
    antes = {c.slug for c in db.query(City).all()}
    carregadas = seed_all(db)
    assert set(carregadas) == antes
    assert {c.slug for c in db.query(City).all()} == antes


@pytest.mark.parametrize("slug", ["sao-paulo", "porto-alegre", "cidade-exemplo"])
def test_cada_cidade_tem_zonas_e_fontes(db, slug):
    cidade = db.query(City).filter(City.slug == slug).one()
    assert db.query(Zone).filter(Zone.city_id == cidade.id).count() > 0
    assert db.query(Source).filter(Source.city_id == cidade.id).count() > 0
