import contextlib
import logging

from playwright.sync_api import Page
from playwright.sync_api import TimeoutError as PWTimeout

from paralisacao import browser
from paralisacao.config import Config
from paralisacao.exceptions import LoginError
from paralisacao.retry import com_retry

logger = logging.getLogger("paralisacao.navegacao")

@com_retry(tentativas=3, backoff_base=2.0, excecoes=(LoginError, Exception))
def login(page: Page, config: Config) -> None:
    """Realiza login no OpenPort CODEBA com as credenciais configuradas."""
    logger.info(f"Acessando {config.url}")
    page.goto(config.url, wait_until="domcontentloaded")
    browser.esperar(page, 3000)
    browser.maximizar_tela_cheia(page)
    browser.bloquear_interacao_usuario(page)

    logger.info("Fazendo login")
    browser.preencher(page, config, config.css["login"], config.login)
    browser.esperar(page, 500)
    browser.preencher(page, config, config.css["senha"], config.senha)
    browser.esperar(page, 500)
    browser.acionar(page, config, config.css["entrar"])

    with contextlib.suppress(Exception):
        page.wait_for_load_state("networkidle")

    browser.esperar(page, 3000)
    browser.bloquear_interacao_usuario(page)

    login_ok = False
    try:
        page.locator("input#User").wait_for(state="hidden", timeout=8000)
        login_ok = True
    except PWTimeout:
        pass

    if login_ok:
        logger.info("Login efetuado.")
        browser.maximizar_tela_cheia(page)
        browser.bloquear_interacao_usuario(page)
    else:
        browser.salvar_screenshot(page, config, "login_falhou")
        raise LoginError("Login nao concluido. Verifique credenciais ou seletores.")

def abrir_tela_7001(page: Page, config: Config) -> None:
    """Abre a tela de cadastro/consulta 7001."""
    logger.info("Abrindo a tela 7001")
    browser.preencher(page, config, config.css["menu_acesso"], "7001")
    browser.esperar(page, 500)
    page.keyboard.press("Enter")

    with contextlib.suppress(Exception):
        page.wait_for_load_state("networkidle")

    browser.esperar(page, 3000)
    browser.bloquear_interacao_usuario(page)
    browser.maximizar_tela_cheia(page)

def voltar_para_lista(page: Page, config: Config) -> None:
    """Retorna para a lista de capas a partir da tela de edição da capa."""
    logger.info("Voltando para lista de capas...")
    try:
        browser.acionar(page, config, "button#BPESQUISAR")
        with contextlib.suppress(Exception):
            page.wait_for_load_state("networkidle")
        browser.esperar(page, 3000)
        browser.bloquear_interacao_usuario(page)
        browser.maximizar_tela_cheia(page)
        logger.info("   Lista de capas exibida.")
    except Exception as e:
        logger.warning(f"   Botao Lista nao funcionou ({e}). Reabrindo 7001 pelo menu.")
        abrir_tela_7001(page, config)
