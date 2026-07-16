import contextlib
import logging
from datetime import datetime

from playwright.sync_api import BrowserContext, Page

from paralisacao.config import Config

logger = logging.getLogger("paralisacao.browser")

_SCRIPT_BLOQUEIO_MOUSE = """
() => {
    if (window.__rpaBloqueioMouse) return;
    window.__rpaBloqueioMouse = true;
    const eventos = [
        "mousedown", "mouseup", "click", "dblclick",
        "mousemove", "mouseover", "mouseout", "mouseenter", "mouseleave",
        "contextmenu", "wheel", "pointerdown", "pointerup", "pointermove",
    ];
    const bloquear = (evento) => {
        if (evento.isTrusted) {
            evento.stopImmediatePropagation();
            evento.preventDefault();
        }
    };
    eventos.forEach((nome) => document.addEventListener(nome, bloquear, true));
}
"""

def esperar(page: Page, ms: int = 1500) -> None:
    """Wrapper simples para aguardar milissegundos."""
    page.wait_for_timeout(ms)

def trazer_para_primeiro_plano(page: Page) -> None:
    """Traz a página ativa para o primeiro plano e maximiza a janela."""
    with contextlib.suppress(Exception):
        page.bring_to_front()
    try:
        cdp = page.context.new_cdp_session(page)
        window_id = cdp.send("Browser.getWindowForTarget")["windowId"]
        cdp.send("Browser.setWindowBounds", {
            "windowId": window_id,
            "bounds": {"windowState": "maximized"}
        })
        cdp.send("Page.bringToFront")
    except Exception:
        pass

def aguardar_visualizacao(page: Page, config: Config) -> None:
    """Pausa a execução condicionalmente para fins de acompanhamento visual."""
    if not config.primeiro_plano or config.pausa_visual_ms <= 0:
        return
    trazer_para_primeiro_plano(page)
    page.wait_for_timeout(config.pausa_visual_ms)

def maximizar_tela_cheia(page: Page) -> None:
    """Tenta maximizar a tela usando múltiplos métodos (CDP, JS, F11)."""
    trazer_para_primeiro_plano(page)
    tentativas = []
    # 1 - CDP fullscreen
    try:
        cdp = page.context.new_cdp_session(page)
        window_id = cdp.send("Browser.getWindowForTarget")["windowId"]
        cdp.send("Browser.setWindowBounds", {
            "windowId": window_id,
            "bounds": {"windowState": "fullscreen"}
        })
        tentativas.append("CDP")
    except Exception:
        pass
    # 2 - JavaScript resize
    if not tentativas:
        try:
            page.evaluate("window.moveTo(0,0); window.resizeTo(screen.availWidth, screen.availHeight)")
            tentativas.append("JS")
        except Exception:
            pass
    # 3 - F11 fallback
    if not tentativas:
        try:
            page.keyboard.press("F11")
            page.wait_for_timeout(500)
            tentativas.append("F11")
        except Exception:
            pass
    if tentativas:
        logger.info(f"   Tela maximizada ({', '.join(tentativas)}).")
    else:
        logger.warning("   (aviso: nao foi possivel maximizar a tela)")

def bloquear_interacao_usuario(page: Page) -> None:
    """Injeta script JS para bloquear cliques físicos e movimentação de mouse do usuário."""
    try:
        page.evaluate(_SCRIPT_BLOQUEIO_MOUSE)
    except Exception as e:
        logger.debug(f"   (aviso: bloqueio de mouse: {e})")

def registrar_tela_cheia_em_novas_paginas(context: BrowserContext, config: Config) -> None:
    """Configura handlers de novas páginas para bloquear interação e maximizar automaticamente."""
    def _ao_abrir_pagina(nova_pagina: Page) -> None:
        with contextlib.suppress(Exception):
            nova_pagina.wait_for_load_state("domcontentloaded")
        with contextlib.suppress(Exception):
            bloquear_interacao_usuario(nova_pagina)
        with contextlib.suppress(Exception):
            maximizar_tela_cheia(nova_pagina)
    context.on("page", _ao_abrir_pagina)

def preencher(page: Page, config: Config, css: str, valor: str) -> None:
    """Foca e preenche um campo input por seletor CSS, aguardando visualização."""
    campo = page.locator(css)
    campo.scroll_into_view_if_needed()
    campo.focus()
    campo.fill(str(valor))
    esperar(page, 300)
    aguardar_visualizacao(page, config)

def acionar(page: Page, config: Config, css: str) -> None:
    """Clica em um elemento via JS evaluate para maior robustez, aguardando visualização."""
    locator = page.locator(css)
    locator.scroll_into_view_if_needed()
    locator.evaluate("el => el.click()")
    esperar(page, 500)
    aguardar_visualizacao(page, config)

def salvar_screenshot(page: Page, config: Config, nome: str) -> None:
    """Salva um screenshot no diretório de screenshots do projeto."""
    try:
        screenshots_dir = config.project_root / "screenshots"
        screenshots_dir.mkdir(exist_ok=True)
        caminho = screenshots_dir / f"{nome}_{datetime.now():%Y%m%d_%H%M%S}.png"
        page.screenshot(path=str(caminho))
        logger.info(f"   Screenshot salvo: {caminho}")
    except Exception as e:
        logger.error(f"   (nao foi possivel salvar screenshot: {e})")
