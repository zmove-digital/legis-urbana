"""Configuracoes da aplicacao (via variaveis de ambiente)."""

from __future__ import annotations

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = Path(os.getenv("LEGIS_DATA_DIR", BASE_DIR / "data"))
CITIES_DIR = DATA_DIR / "cities"
STATIC_DIR = Path(__file__).resolve().parent / "static"
SEED_ON_STARTUP = os.getenv("LEGIS_SEED_ON_STARTUP", "1") == "1"
APP_TITLE = "LegisUrb - Parametros urbanisticos por legislacao municipal"
APP_VERSION = "0.1.0"


def _resolve_db_url() -> str:
    """Normaliza a URL do banco.

    Caminhos SQLite relativos sao resolvidos a partir da raiz do projeto (e
    nao do diretorio de trabalho do processo), para que a aplicacao funcione
    independente de onde o uvicorn foi iniciado.
    """
    raw = os.getenv("LEGIS_DB_URL", f"sqlite:///{(DATA_DIR / 'legis.db').as_posix()}")
    prefix = "sqlite:///"
    if raw.startswith(prefix):
        caminho = raw[len(prefix) :]
        if caminho and not caminho.startswith("/") and not Path(caminho).is_absolute():
            caminho = (BASE_DIR / caminho).as_posix()
        return prefix + caminho
    return raw


DB_URL = _resolve_db_url()

DISCLAIMER = (
    "Ferramenta de apoio tecnico. Os parametros apresentados sao extraidos de texto "
    "legislativo e dependem de interpretacao, de verificaciones especificas e de "
    "parecer do responsavel tecnico (ART/RRT). Nao substitui a leitura da lei vigente, "
    "a analise do orgao municipal nem a responsabilidade profissional."
)
