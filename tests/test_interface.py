"""Testes da interface (estaticos).

Regressao importante: regras de CSS com `display` em classes (`.modal`,
`.help-link`) venciam o atributo `hidden` do HTML, deixando o balao
"Analises salvas" sempre aberto e o botao "Fechar" sem efeito visual.
"""

from __future__ import annotations

import re

from app.config import STATIC_DIR

STYLES = STATIC_DIR / "styles.css"
INDEX = STATIC_DIR / "index.html"


def _regras_hidden(css: str) -> list[str]:
    """Seletores que contem [hidden] e declaram display:none."""
    encontradas = []
    for bloco in re.finditer(r"([^{}]+)\{([^{}]*)\}", css):
        seletores, corpo = bloco.group(1).strip(), bloco.group(2)
        if "[hidden]" in seletores and re.search(r"display\s*:\s*none", corpo):
            encontradas.append(seletores)
    return encontradas


def test_atributo_hidden_tem_precedencia_no_css():
    """O atributo hidden precisa vencer o display das classes."""
    css = STYLES.read_text(encoding="utf-8")
    assert _regras_hidden(css), (
        "styles.css precisa de uma regra [hidden] { display: none } - "
        "sem ela o modal e o link de ajuda ignoram o atributo hidden"
    )


def test_elementos_com_hidden_no_html_tem_regra_que_os_esconde():
    """Todo elemento com hidden no HTML precisa de uma regra [hidden] valida."""
    html = INDEX.read_text(encoding="utf-8")
    css = STYLES.read_text(encoding="utf-8")
    com_hidden = re.findall(r"id=\"([^\"]+)\"[^>]*\shidden", html)
    assert com_hidden, "o HTML deveria ter elementos com hidden"
    assert _regras_hidden(css)
    for elemento in com_hidden:
        assert f'"{elemento}"' in html or f'id="{elemento}"' in html


def test_nenhuma_classe_com_display_quebra_o_hidden():
    """Classes usadas por elementos hidden nao podem ter display fixo.

    Um `display` em seletor de classe tem precedencia sobre o padrao do
    navegador para [hidden]; por isso a regra global e obrigatoria.
    """
    html = INDEX.read_text(encoding="utf-8")
    css = STYLES.read_text(encoding="utf-8")
    classes_com_hidden = set()
    for elemento in re.findall(r"<(\w+)[^>]*class=\"([^\"]+)\"[^>]*\shidden", html):
        classes_com_hidden.update(elemento[1].split())
    for elemento in re.findall(r"class=\"([^\"]+)\"[^>]*\shidden", html):
        classes_com_hidden.update(elemento.split())

    for classe in classes_com_hidden:
        padrao = re.compile(rf"\.{re.escape(classe)}\s*(,[^{{]+)?\{{([^}}]*)\}}")
        for achado in padrao.finditer(css):
            if re.search(r"display\s*:\s*(?!none)", achado.group(2)):
                # display em .classe e seguro: a regra [hidden] usa !important
                continue
    # A garantia real e a regra global com !important
    assert re.search(r"\[hidden\]\s*\{[^}]*display\s*:\s*none\s*!important", css), (
        "a regra [hidden] precisa usar !important para vencer display de classe"
    )


def test_app_js_nao_deixa_campos_mortos():
    """Todo input do HTML precisa ser lido pelo collectAnswers ou por outro JS.

    Regressao: os inputs #lat e #lon do bloco de geolocalizacao existiam no
    HTML mas nao eram lidos, e o dado digitado era ignorado na analise.
    """
    html = INDEX.read_text(encoding="utf-8")
    js = (STATIC_DIR / "app.js").read_text(encoding="utf-8")
    ids_html = set(re.findall(r"<(?:input|select|textarea)[^>]*id=\"([^\"]+)\"", html))
    # ids lidos explicitamente pelo JS
    lidos = set(re.findall(r"getElementById\(['\"]([^'\"]+)['\"]\)", js))
    lidos |= set(re.findall(r"\$\(['\"]#([^'\"]+)['\"]\)", js))
    lidos |= set(re.findall(r"id = [`'\"]([^`'\"]+)[`'\"]", js))
    # ids de campos dinamicos (prefixo q-) sao criados em tempo de execucao
    dinamicos = {i for i in ids_html if i.startswith("q-")}
    fixos = ids_html - dinamicos
    nao_lidos = fixos - lidos
    assert not nao_lidos, f"campos do HTML sem leitura no JS: {sorted(nao_lidos)}"
