import contextlib
import logging

from playwright.sync_api import Page

from paralisacao import browser, mapeamento
from paralisacao.config import Config
from paralisacao.planilha import Capa
from paralisacao.retry import com_retry

logger = logging.getLogger("paralisacao.capa")

@com_retry(tentativas=3, backoff_base=2.0)
def buscar_capa(page: Page, config: Config, capa: Capa, prog_navio: str) -> int | None:
    """Busca uma capa existente no OpenPort e retorna o codRegistro, ou None se não encontrar."""
    turno = mapeamento.turno_do_periodo(capa.periodo, config)
    if not turno:
        logger.warning(f"!! Capa {capa.registro}: turno nao identificado para periodo '{capa.periodo}'")
        return None

    logger.info(f"Buscando capa {capa.registro} | {capa.data} | {capa.periodo}")

    browser.preencher(page, config, config.css["busca_operador"], config.operador)
    browser.preencher(page, config, config.css["busca_prog_navio"], prog_navio)
    browser.preencher(page, config, config.css["busca_data"], capa.data)
    browser.esperar(page, 500)
    page.locator(config.css["busca_turno"]).select_option(label=turno["label"])
    browser.esperar(page, 500)
    browser.aguardar_visualizacao(page, config)

    browser.acionar(page, config, config.css["btn_filtrar"])
    with contextlib.suppress(Exception):
        page.wait_for_load_state("networkidle")
    browser.esperar(page, 3000)

    grid = page.locator(config.css["grid_resultados"])
    rows = grid.locator("tr")
    if rows.count() <= 1:
        logger.info(f"   Capa {capa.registro} nao encontrada. Registros: {rows.count() - 1}")
        return None

    logger.info("   Capa encontrada. Clicando no resultado.")
    rows.nth(1).locator("td").first.click()
    with contextlib.suppress(Exception):
        page.wait_for_load_state("networkidle")
    browser.esperar(page, 3000)
    browser.bloquear_interacao_usuario(page)
    browser.maximizar_tela_cheia(page)

    cod_registro = page.evaluate("document.querySelector('input[name=codRegistro]')?.value || ''")
    cod_registro = int(cod_registro) if cod_registro and str(cod_registro).isdigit() else 0
    logger.info(f"   codRegistro={cod_registro}")
    return cod_registro

@com_retry(tentativas=3, backoff_base=2.0)
def criar_capa(page: Page, config: Config, capa: Capa, prog_navio: str) -> int | None:
    """Cria uma nova capa no OpenPort e retorna o codRegistro, ou None se falhar."""
    turno = mapeamento.turno_do_periodo(capa.periodo, config)
    if not turno:
        logger.warning(f"!! Capa {capa.registro}: turno nao identificado para periodo '{capa.periodo}'")
        return None

    logger.info(f"Criando capa {capa.registro} | {capa.data} | {capa.periodo}")

    # Navegar para URL de nova capa
    url_nova = config.url + "cadastro.aspx?WCI=frmEdtTurmaTrabVeiculos_007&Mv=Novo"
    page.goto(url_nova, wait_until="domcontentloaded")
    browser.esperar(page, 2000)
    browser.maximizar_tela_cheia(page)
    browser.bloquear_interacao_usuario(page)

    # Preencher Operador
    browser.preencher(page, config, "#NUM_EMPRESA_2", config.operador)
    browser.esperar(page, 300)
    page.locator("#NUM_EMPRESA_2").press("Tab")
    browser.esperar(page, 1500)

    # Preencher Progr. Navio
    browser.preencher(page, config, "#NUM_PROGR_NAVIO_2", prog_navio)
    browser.esperar(page, 300)
    page.locator("#NUM_PROGR_NAVIO_2").press("Tab")
    browser.esperar(page, 1500)

    # Preencher Data
    browser.preencher(page, config, "#DAT_INICIO", capa.data)
    browser.esperar(page, 300)
    page.locator("#DAT_INICIO").press("Tab")
    browser.esperar(page, 500)

    # Selecionar Turno (por label, values sao diferentes no form Novo)
    page.locator("#NUM_TURNO").select_option(label=turno["label"])
    browser.esperar(page, 500)

    # Gravar via MySubmit (type="button", onclick="MySubmit(...)")
    logger.info("   Gravando nova capa...")
    page.evaluate("MySubmit('salvar', 'cadastro.aspx?WCI=frmEdtTurmaTrabVeiculos_007&Mv=Salvar')")
    browser.esperar(page, 3000)
    with contextlib.suppress(Exception):
        page.wait_for_load_state("networkidle", timeout=8000)
    browser.esperar(page, 2000)

    # Extrair codRegistro da nova capa (input[name=codRegistro] sem id no DOM)
    cod_registro = page.evaluate("document.querySelector('input[name=codRegistro]')?.value || ''")
    cod_registro = int(cod_registro) if cod_registro and str(cod_registro).isdigit() else 0
    if cod_registro:
        logger.info(f"   Capa criada: codRegistro={cod_registro}")
        browser.maximizar_tela_cheia(page)
        browser.bloquear_interacao_usuario(page)
        return cod_registro

    logger.warning("   !! Nao foi possivel obter codRegistro da nova capa.")
    browser.salvar_screenshot(page, config, f"criar_capa_erro_{capa.registro}")
    return None
