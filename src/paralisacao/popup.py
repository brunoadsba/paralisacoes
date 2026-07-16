import contextlib
import logging
from datetime import datetime, timedelta

from playwright.sync_api import Page

from paralisacao import browser, mapeamento
from paralisacao.config import Config
from paralisacao.exceptions import GravacaoError
from paralisacao.planilha import Paralisacao
from paralisacao.relatorio import Relatorio
from paralisacao.retry import com_retry

logger = logging.getLogger("paralisacao.popup")

def abrir_popup_paralisacao(page: Page, config: Config, cod_registro: int) -> Page | None:
    """Abre o popup dlgEdtInformParalisManual via botao ⊕ e retorna a pagina do popup."""
    logger.info("   Abrindo popup de paralisacao (botao [+])...")
    try:
        with page.expect_popup(timeout=15000) as popup_info:
            page.locator(config.css["btn_adicionar_paralisacao"]).evaluate("el => el.click()")
        popup = popup_info.value
    except Exception:
        # fallback: verificar se ja abriu
        popup = None
        for p in page.context.pages:
            if "dlgEdtInformParalisManual" in p.url:
                popup = p
                break
    if not popup:
        logger.warning("   !! Nao foi possivel abrir o popup de paralisacao.")
        return None
    popup.wait_for_load_state("domcontentloaded")
    browser.esperar(popup, 3000)
    browser.maximizar_tela_cheia(popup)
    browser.bloquear_interacao_usuario(popup)
    logger.info("   Popup aberto.")
    return popup

def selecionar_lookup_motivo(popup: Page, nome_motivo: str, config: Config) -> bool:
    """Abre o lookup de motivo e seleciona o texto exato."""
    logger.info(f"     Selecionando motivo '{nome_motivo}' no lookup...")
    try:
        popup.locator(config.css["popup_btn_motivo"]).evaluate("el => el.click()")
        browser.esperar(popup, 2000)
    except Exception as e:
        logger.error(f"     !! Nao foi possivel clicar no botao lookup: {e}")
        return False

    # Capturar janela do lookup (modal)
    lookup = None
    for p in popup.context.pages:
        if "dlgPsqTipoParalisacao" in p.url and p != popup:
            lookup = p
            break
    if not lookup:
        logger.warning("     !! Janela de lookup nao encontrada.")
        return False

    try:
        lookup.wait_for_load_state("domcontentloaded")
        browser.esperar(lookup, 3000)
        browser.maximizar_tela_cheia(lookup)
        browser.bloquear_interacao_usuario(lookup)

        # Tenta multiplas estrategias de busca
        linha = None
        for seletor in [
            f"text={nome_motivo}",
            f"text='{nome_motivo}'",
            f"tr:has-text('{nome_motivo}')",
            f"td:has-text('{nome_motivo}')",
        ]:
            candidato = lookup.locator(seletor).first
            if candidato.count() > 0:
                linha = candidato
                logger.info(f"     Encontrado com seletor: {seletor}")
                break

        if linha is None:
            logger.warning(f"     !! Motivo '{nome_motivo}' nao encontrado no lookup.")
            try:
                textos = lookup.locator("tr td:last-child, tr td:nth-child(2)").all_inner_texts()
                logger.info(f"     Opcoes disponiveis: {textos[:10]}")
            except Exception:
                pass
            lookup.close()
            return False

        logger.info(f"     Clicando no motivo '{nome_motivo}'...")
        linha.evaluate("el => el.click()")
        browser.esperar(lookup, 1500)
        lookup.close()
        browser.esperar(popup, 1000)
        logger.info("     Motivo selecionado.")
        return True
    except Exception as e:
        logger.error(f"     !! Erro no lookup: {e}")
        with contextlib.suppress(Exception):
            lookup.close()
        return False

def selecionar_estadia(popup: Page, nome_navio: str, config: Config) -> bool:
    """Seleciona a estadia que contem o nome do navio no dropdown."""
    try:
        select = popup.locator(config.css["popup_estadia"])
        options = select.evaluate("""
            el => Array.from(el.options).map(o => ({value: o.value, text: o.text}))
        """)
        for opt in options:
            if nome_navio.upper() in opt["text"].upper() and opt["value"] != "0":
                logger.info(f"     Selecionando estadia: '{opt['text']}'")
                select.select_option(value=opt["value"])
                browser.esperar(popup, 500)
                return True
        logger.warning(f"     !! Estadia com navio '{nome_navio}' nao encontrada.")
        return False
    except Exception as e:
        logger.error(f"     !! Erro ao selecionar estadia: {e}")
        return False

def _calcular_data_hora(capa_data: str, periodo: str, hora_str: str) -> str:
    """Retorna 'DD/MM/YYYY HH:MM' ajustando a data se o horário passou da meia-noite."""
    if not hora_str:
        return capa_data

    hora_str = hora_str.strip()
    hora_str = hora_str.replace("-", "/")
    partes_t = hora_str.split(":")
    if len(partes_t) < 2:
        return f"{capa_data} {hora_str}"
    hora = int(partes_t[0])
    minuto = partes_t[1]

    try:
        ref_hora = int(periodo.split("/")[0].split(":")[0])
    except (ValueError, IndexError):
        return f"{capa_data} {hora_str}"

    try:
        dt = datetime.strptime(capa_data, "%d/%m/%Y")
    except ValueError:
        return f"{capa_data} {hora_str}"

    if hora < ref_hora:
        dt = dt + timedelta(days=1)

    return dt.strftime(f"%d/%m/%Y {hora:02d}:{minuto}")

def preencher_data_hora(popup: Page, config: Config, seletor_data: str, seletor_hora: str, valor: str) -> None:
    """Preenche data e hora a partir de um valor tipo '13:00' ou '09/07/2026 13:00'."""
    if not valor:
        return
    partes = valor.strip().split()
    if len(partes) >= 2:
        browser.preencher(popup, config, seletor_data, partes[0])
        browser.preencher(popup, config, seletor_hora, partes[1])
    elif "/" in partes[0]:
        browser.preencher(popup, config, seletor_data, partes[0])
    else:
        browser.preencher(popup, config, seletor_hora, partes[0])

def _verificar_gravacao(popup: Page) -> bool:
    """Verifica se a gravação foi confirmada pelo OpenPort, levantando exceções em caso de falha."""
    if popup.is_closed():
        return True  # Popup fechou = salvou com sucesso

    try:
        # Aguarda um curto timeout para ler o corpo caso o sistema demore a renderizar o erro/sucesso
        body = popup.locator("body").inner_text(timeout=3000)
    except Exception:
        return False

    body_lower = body.lower()

    # 1. Detectar erros óbvios
    padroes_erro = ["erro", "falha", "inválid", "obrigatório", "não permitid", "ocorreu um problema"]
    for padrao in padroes_erro:
        if padrao in body_lower:
            raise GravacaoError(f"Sistema retornou erro no popup: {body[:300].strip()}")

    # 2. Detectar mensagens explícitas de sucesso
    padroes_sucesso = ["sucesso", "realizada com sucesso", "salvo", "incluíd", "gravad"]
    for padrao in padroes_sucesso:
        if padrao in body_lower:
            return True

    # 3. Sem indicativo de sucesso ou erro (ex: modal continuou aberto e inalterado)
    raise GravacaoError(f"Confirmação não detectada. Conteúdo da tela: {body[:300].strip()}")

@com_retry(tentativas=3, backoff_base=2.0, excecoes=(GravacaoError, Exception))
def adicionar_paralisacao(page: Page, config: Config, relatorio: Relatorio,
                          capa_registro: str, cod_registro: int,
                          p: Paralisacao, nome_navio: str = "",
                          capa_data: str = "", capa_periodo: str = "") -> bool:
    """Insere e grava uma paralisação no popup do OpenPort."""
    if not cod_registro or cod_registro <= 0:
        msg = f"codRegistro invalido ({cod_registro})"
        logger.error(f"   !! {msg}")
        relatorio.add_paralisacao_erro(capa_registro, p, msg)
        return False

    nome_sistema = mapeamento.motivo_sistema(p.motivo, config)
    if nome_sistema is None:
        msg = f"Motivo '{p.motivo}' nao mapeado em config.motivo_correspondencia"
        logger.warning(f"!! {msg}")
        relatorio.add_paralisacao_pulada(capa_registro, p, msg)
        return False

    logger.info(f"   + Paralisacao {p.inicio} -> {p.fim} | planilha='{p.motivo}' -> sist='{nome_sistema}'")

    # 1. Abrir popup via botao ⊕
    popup = abrir_popup_paralisacao(page, config, cod_registro)
    if not popup:
        relatorio.add_paralisacao_erro(capa_registro, p, "Popup nao abriu")
        return False

    try:
        # 2. Motivo: digitar codigo numerico e dar Tab para sistema reconhecer
        codigo = mapeamento.codigo_motivo(nome_sistema, config)
        if codigo:
            logger.info(f"     Preenchendo motivo codigo={codigo} ({nome_sistema})")
            campo_motivo = popup.locator(config.css["popup_motivo"])
            campo_motivo.click()
            browser.esperar(popup, 200)
            campo_motivo.fill(str(codigo))
            browser.esperar(popup, 300)
            campo_motivo.press("Tab")
            browser.esperar(popup, 1500)
        else:
            logger.info(f"     !! Codigo nao encontrado para '{nome_sistema}'. Tentando lookup...")
            if not selecionar_lookup_motivo(popup, nome_sistema, config):
                logger.warning("     Fallback: digitando texto diretamente.")

        # 3. Estadia
        if nome_navio:
            selecionar_estadia(popup, nome_navio, config)

        # 4. Inicio (data + hora ajustada por turno noturno)
        valor_inicio = _calcular_data_hora(capa_data, capa_periodo, p.inicio)
        preencher_data_hora(popup, config, config.css["popup_data_inicio"],
                             config.css["popup_hora_inicio"], valor_inicio)

        # 5. Fim
        valor_fim = _calcular_data_hora(capa_data, capa_periodo, p.fim)
        preencher_data_hora(popup, config, config.css["popup_data_fim"],
                             config.css["popup_hora_fim"], valor_fim)

        # 6. Observacao = motivo ORIGINAL da planilha
        if p.motivo and config.css.get("popup_observacao"):
            browser.preencher(popup, config, config.css["popup_observacao"], p.motivo)

        browser.esperar(popup, 1500)

        # 7. Gravar
        logger.info("     Gravando paralisacao...")
        browser.acionar(popup, config, config.css["popup_btn_gravar"])
        with contextlib.suppress(Exception):
            popup.wait_for_load_state("networkidle", timeout=8000)
        with contextlib.suppress(Exception):
            browser.esperar(popup, 2000)

        # 8. Verificar confirmacao real
        _verificar_gravacao(popup)
        logger.info("     Paralisacao registrada com sucesso.")

        # 9. Fechar se popup ainda estiver aberto
        if not popup.is_closed():
            try:
                popup.evaluate("CloseDialog()")
                browser.esperar(popup, 1000)
            except Exception:
                pass

        # 10. Clicar Atualizar na tela principal para recarregar a lista
        logger.info("     Clicando Atualizar na tela principal...")
        try:
            page.locator("xpath=/html/body/div[3]/div[1]/button[3]").evaluate("el => el.click()")
            page.wait_for_load_state("networkidle")
            browser.esperar(page, 2000)
            logger.info("     Tela atualizada.")
        except Exception as e:
            logger.warning(f"     (aviso: atualizar: {e})")

        relatorio.add_paralisacao_ok(capa_registro, p)
        return True

    except Exception as e:
        logger.error(f"   !! Erro ao preencher paralisacao: {e}")
        browser.salvar_screenshot(popup, config, f"erro_paralisacao_{capa_registro}")
        relatorio.add_paralisacao_erro(capa_registro, p, str(e))
        with contextlib.suppress(Exception):
            popup.evaluate("CloseDialog()")
        return False
    finally:
        if not popup.is_closed():
            with contextlib.suppress(Exception):
                popup.close()
