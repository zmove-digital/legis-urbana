"""Testes de ponta a ponta da interface, em navegador de verdade.

Estes testes pegam a classe de defeito que os testes de API nao pega:
elemento que aparece quando deveria estar escondido, campo que nao e lido,
botao que nao fecha nada.

Requer Playwright e o Chromium instalado. Sem eles, os testes sao ignorados
(para a suite nao quebrar em maquinas sem navegador).

    pip install playwright
    playwright install chromium
"""

from __future__ import annotations

import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request

import pytest

pytestmark = pytest.mark.e2e


def _porta_livre() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _esperar_saude(url: str, timeout: float = 40.0) -> bool:
    limite = time.time() + timeout
    while time.time() < limite:
        try:
            with urllib.request.urlopen(f"{url}/api/health", timeout=2) as resposta:
                if resposta.status == 200:
                    return True
        except (urllib.error.URLError, OSError):
            time.sleep(0.4)
    return False


@pytest.fixture(scope="module")
def navegador():
    sync_playwright = pytest.importorskip(
        "playwright.sync_api", reason="Playwright nao instalado (pip install playwright)"
    )
    with sync_playwright.sync_playwright() as p:
        try:
            browser = p.chromium.launch()
        except Exception as exc:  # navegador nao instalado
            pytest.skip(f"Chromium indisponivel para Playwright: {exc}")
        yield browser
        browser.close()


@pytest.fixture(scope="module")
def servidor():
    porta = _porta_livre()
    processo = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "uvicorn",
            "app.main:app",
            "--host",
            "127.0.0.1",
            "--port",
            str(porta),
            "--log-level",
            "warning",
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    url = f"http://127.0.0.1:{porta}"
    try:
        if not _esperar_saude(url):
            pytest.skip("servidor nao subiu a tempo")
        yield url
    finally:
        processo.terminate()
        try:
            processo.wait(timeout=10)
        except subprocess.TimeoutExpired:
            processo.kill()


@pytest.fixture
def pagina(navegador, servidor):
    page = navegador.new_page(viewport={"width": 1440, "height": 900})
    erros: list[str] = []
    page.on("pageerror", lambda e: erros.append(str(e)))
    page.goto(servidor, wait_until="networkidle")
    yield page
    assert not erros, f"erros de JS na interface: {erros}"
    page.close()


def test_modal_de_analises_salvas_comeca_fechado(pagina):
    """Regressao: o balao 'Analises salvas' abria sozinho e nao fechava."""
    modal = pagina.locator("#modal")
    assert not modal.is_visible(), "o modal deve iniciar oculto"

    pagina.click("#btn-saved")
    pagina.wait_for_timeout(300)
    assert modal.is_visible(), "o botao 'Analises salvas' deve abrir o modal"

    pagina.click("#btn-close-modal")
    pagina.wait_for_timeout(300)
    assert not modal.is_visible(), "o botao 'Fechar' deve fechar o modal"

    # e o ciclo funciona de novo
    pagina.click("#btn-saved")
    pagina.wait_for_timeout(250)
    pagina.click("#btn-close-modal")
    pagina.wait_for_timeout(250)
    assert not modal.is_visible()


def test_link_do_mapa_de_zoneamento_comeca_oculto(pagina):
    """O link 'Consultar mapa de zoneamento' so aparece quando a cidade tem URL."""
    helper = pagina.locator("#zone-helper")
    assert not helper.is_visible()


def test_sem_campos_de_geolocalizacao_duplicados(pagina):
    """lat/lon nao podem aparecer duas vezes (bloco dedicado + questionario)."""
    assert pagina.locator("#geo-field").count() == 1
    assert not pagina.locator("#geo-field").is_visible()
    assert pagina.locator("#q-lat").count() == 1


def test_consulta_exibe_limites_e_base_legal(pagina):
    pagina.select_option("#city", "sao-paulo")
    pagina.wait_for_timeout(500)
    pagina.select_option("#zone", "ZM")
    pagina.wait_for_timeout(200)

    pagina.fill("#q-lot_area", "900")
    pagina.select_option("#q-use", "residencial")
    pagina.fill("#q-total_built_area", "1200")
    pagina.fill("#q-footprint_area", "500")
    pagina.fill("#q-floors", "3")
    pagina.fill("#q-proposed_setback_front", "3")
    pagina.fill("#q-proposed_setback_side", "2")
    pagina.fill("#q-proposed_setback_back", "2")
    pagina.click("#btn-analyze")
    pagina.wait_for_timeout(1500)

    texto = pagina.locator("#results").inner_text()
    assert "Coeficiente de Aproveitamento" in texto
    assert "Quadro 3" in texto, "a base legal deve aparecer no resultado"
    assert "Não conforme" in texto, "o recuo frontal insuficiente (3 m) deve ser apontado"


def test_geolocalizacao_resolve_a_zona(pagina):
    """O bloco de lat/lon precisa realmente chegar ao motor de analise."""
    pagina.fill("#q-lot_area", "400")
    pagina.select_option("#q-use", "residencial")
    pagina.fill("#q-lat", "-23.555")
    pagina.fill("#q-lon", "-46.635")
    pagina.click("#btn-analyze")
    pagina.wait_for_timeout(1500)

    texto = pagina.locator("#results").inner_text()
    assert "Zona Residencial" in texto, "a zona deveria ser resolvida por geolocalizacao"


def test_zonas_de_porto_alegre_sao_agrupadas_por_sub_setor(pagina):
    """As ZOTs 8.1, 8.2 e 8.3 ficam em grupos, com os sub-setores por letra."""
    pagina.select_option("#city", "porto-alegre")
    pagina.wait_for_timeout(700)

    grupos = pagina.locator("#zone optgroup").all_text_contents()
    assert any("8.1" in g for g in grupos), f"esperado grupo da ZOT 8.1 em {grupos}"
    assert any("8.3" in g for g in grupos), f"esperado grupo da ZOT 8.3 em {grupos}"

    opcoes = pagina.locator("#zone option").all_text_contents()
    assert any("ZOT 8.1A" in o for o in opcoes)
    assert any("ZOT 8.3D" in o for o in opcoes)


def test_consulta_em_porto_alegre_cita_o_anexo_2(pagina):
    pagina.select_option("#city", "porto-alegre")
    pagina.wait_for_timeout(700)
    pagina.select_option("#zone", "ZOT 4")
    pagina.wait_for_timeout(200)

    pagina.fill("#q-lot_area", "1200")
    pagina.select_option("#q-use", "residencial")
    pagina.fill("#q-total_built_area", "1800")
    pagina.fill("#q-footprint_area", "400")
    pagina.fill("#q-floors", "4")
    pagina.fill("#q-permeable_area", "300")
    pagina.fill("#q-proposed_setback_front", "4")
    pagina.fill("#q-proposed_setback_side", "3")
    pagina.fill("#q-proposed_setback_back", "3")
    pagina.click("#btn-analyze")
    pagina.wait_for_timeout(1500)

    texto = pagina.locator("#results").inner_text()
    assert "Coeficiente de Aproveitamento" in texto
    assert "Anexo 2" in texto, "a base legal do Anexo 2 deve aparecer no resultado"
    assert "ZOT 4" in texto
