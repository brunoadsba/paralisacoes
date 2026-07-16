import argparse
import logging
import sys
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

from paralisacao import browser, capa, mapeamento, navegacao, popup, status
from paralisacao.config import Config
from paralisacao.planilha import DadosPlanilha, ler_planilha
from paralisacao.relatorio import Relatorio, obter_proxima_rodada

# Configuração básica do logging para fallback/desenvolvimento
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S"
)
logger = logging.getLogger("paralisacao.main")

def mostrar_plano(dados: DadosPlanilha, config: Config) -> None:
    """Mostra um resumo em texto de todas as ações planejadas a partir da planilha."""
    logger.info(f"Programacao do navio: {dados.prog_navio}")
    logger.info(f"Capas a processar: {len(dados.capas)}")
    for c in dados.capas:
        turno = mapeamento.turno_do_periodo(c.periodo, config)
        turno_txt = f"turno {turno['numero']}" if turno else "TURNO?"
        logger.info(f"  Capa {c.registro} | {c.data} | {c.periodo} ({turno_txt})")
        for p in c.paralisacoes:
            sist = mapeamento.motivo_sistema(p.motivo, config)
            obs = f" [obs: {p.motivo}]" if sist else ""
            marca = f"-> {sist}{obs}" if sist else "MOTIVO NAO MAPEADO"
            logger.info(f"     - {p.inicio} -> {p.fim} | {p.motivo} {marca}")

def executar(dados: DadosPlanilha, config: Config, relatorio: Relatorio, status_file: Path, planilha_path: str = "") -> None:
    """Orquestra a execução completa do RPA pelo Playwright."""
    prog_navio = dados.prog_navio or ""
    if not prog_navio:
        logger.warning("!! Programacao do navio nao encontrada na planilha.")

    headless = config.headless and not config.primeiro_plano
    if config.primeiro_plano:
        logger.info("Modo primeiro plano: navegador visivel para acompanhamento.")

    relatorio.planilha = planilha_path or config.planilha

    with sync_playwright() as pw:
        browser_instance = pw.chromium.launch(
            headless=headless,
            slow_mo=config.slow_mo_ms,
            args=["--start-maximized", "--window-position=0,0"],
        )
        context = browser_instance.new_context(no_viewport=True)
        context.set_default_timeout(config.timeout_ms)
        browser.registrar_tela_cheia_em_novas_paginas(context, config)
        page = context.new_page()
        browser.maximizar_tela_cheia(page)
        browser.bloquear_interacao_usuario(page)

        try:
            # 1. Login e navegação para tela de programação
            navegacao.login(page, config)
            navegacao.abrir_tela_7001(page, config)

            # 2. Iteração sobre cada capa da planilha
            for i, c in enumerate(dados.capas):
                logger.info(f"\n=== Processando capa {c.registro} ===")

                cod_registro = capa.buscar_capa(page, config, c, prog_navio)
                if not cod_registro or cod_registro <= 0:
                    logger.info("   Capa nao encontrada. Tentando criar...")
                    cod_registro = capa.criar_capa(page, config, c, prog_navio)
                    if not cod_registro:
                        relatorio.add_capa_nao_encontrada(c.registro)
                        continue
                    logger.info(f"   Capa criada com sucesso (codRegistro={cod_registro}).")

                relatorio.add_capa_ok(c.registro, cod_registro)
                logger.info(f"Capa aberta (codRegistro={cod_registro}). {len(c.paralisacoes)} paralisacao(oes) pendente(s).")

                # Clicar na aba Paralisação
                logger.info("Clicando na aba Paralisacao...")
                try:
                    page.locator(config.css["aba_paralisacao"]).wait_for(state="visible", timeout=5000)
                    page.evaluate("document.querySelector('li#Aba6 a').click()")
                    browser.esperar(page, 1500)
                except Exception as e:
                    logger.warning(f"   (aviso: aba paralisacao: {e})")

                # Carrega status local
                status_dict = status.carregar_status(status_file)
                sc = status._status_capa(status_dict, c.registro)
                sc["codRegistro"] = cod_registro
                sc["navio"] = c.navio
                sc["data"] = c.data
                sc["periodo"] = c.periodo

                # Ler grid do OpenPort para detectar duplicatas existentes online
                grid = status.ler_grid_paralisacoes(page)
                if grid:
                    logger.info(f"   Grid contem {len(grid)-1} paralisacao(oes) ja registrada(s).")
                else:
                    logger.warning("   (nao foi possivel ler a grid de paralisações)")

                # Processar cada paralisação da capa
                for p in c.paralisacoes:
                    nome_sist = mapeamento.motivo_sistema(p.motivo, config) or ""
                    codigo = mapeamento.codigo_motivo(nome_sist, config)

                    # Verificar se já existe no status local
                    if codigo and status._paralisacao_ok_no_status(sc, p, codigo):
                        logger.info(f"   - {p.inicio}->{p.fim} {p.motivo}: ja registrada (status local)")
                        relatorio.add_paralisacao_ok(c.registro, p)
                        continue

                    # Verificar se já existe na grid online do OpenPort
                    if codigo and status.paralisacao_ja_existe(grid, p, codigo, config):
                        logger.info(f"   - {p.inicio}->{p.fim} {p.motivo}: ja registrada (grid OpenPort)")
                        status._marcar_ok_no_status(sc, p, codigo)
                        status.salvar_status(status_dict, status_file)
                        relatorio.add_paralisacao_ok(c.registro, p)
                        continue

                    # Inserir paralisação
                    try:
                        ok = popup.adicionar_paralisacao(
                            page, config, relatorio,
                            capa_registro=c.registro,
                            cod_registro=cod_registro,
                            p=p,
                            nome_navio=c.navio,
                            capa_data=c.data,
                            capa_periodo=c.periodo
                        )
                        if ok:
                            logger.info("   OK")
                            if codigo:
                                status._marcar_ok_no_status(sc, p, codigo)
                                status.salvar_status(status_dict, status_file)
                        else:
                            logger.warning("   FALHOU")
                    except Exception as e:
                        logger.error(f"!! Erro na paralisacao {p.inicio}->{p.fim}: {e}")
                        relatorio.add_paralisacao_erro(c.registro, p, str(e))
                        browser.salvar_screenshot(page, config, f"erro_capa{c.registro}")

                status._atualizar_status_capa(sc)
                status.salvar_status(status_dict, status_file)

                # Voltar para lista apenas se houver mais capas
                if i < len(dados.capas) - 1:
                    navegacao.voltar_para_lista(page, config)

            logger.info("\nProcessamento concluido.")

        except Exception as e:
            logger.exception(f"!! Erro fatal na execucao: {e}")
            browser.salvar_screenshot(page, config, "erro_fatal")
        finally:
            relatorio.gerar_arquivo(planilha_path=planilha_path)

            # Manter aberto condicionalmente para auditoria visual
            if not config.headless and config.primeiro_plano:
                if config.manter_aberto_seg > 0:
                    logger.info(f"Navegador aberto por {config.manter_aberto_seg}s para acompanhar...")
                    time.sleep(config.manter_aberto_seg)
                else:
                    logger.info("Aguardando finalização manual...")
                    try:
                        input("Pressione Enter para fechar o navegador...")
                    except EOFError:
                        time.sleep(30)

            context.close()
            browser_instance.close()

def main() -> int:
    parser = argparse.ArgumentParser(description="RPA de Paralisações — OpenPort CODEBA")

    # Parâmetros globais para compatibilidade retroativa
    parser.add_argument("--planilha", default=None, help="Caminho da planilha .xlsx")
    parser.add_argument("--dry-run", action="store_true", help="Apenas lê a planilha e exibe o plano (sem automatizar)")

    subparsers = parser.add_subparsers(dest="comando", help="Subcomandos opcionais")

    # Subcomando executar
    exec_parser = subparsers.add_parser("executar", help="Executa a automação completa")
    exec_parser.add_argument("--planilha", default=None, help="Caminho da planilha .xlsx")
    exec_parser.add_argument("--dry-run", action="store_true", help="Apenas lê a planilha e exibe o plano")

    # Subcomando status
    subparsers.add_parser("status", help="Mostra o status de execução local das capas")

    # Subcomando validar
    validar_parser = subparsers.add_parser("validar", help="Apenas valida a planilha de entrada")
    validar_parser.add_argument("planilha_caminho", nargs="?", default=None, help="Caminho da planilha .xlsx")

    args = parser.parse_args()
    config = Config.from_env()

    # Resolver subcomando ou compatibilidade retroativa
    comando = args.comando
    planilha_alvo = args.planilha or config.planilha
    is_dry_run = args.dry_run

    if comando == "executar":
        planilha_alvo = args.planilha or planilha_alvo
        is_dry_run = args.dry_run or is_dry_run
    elif comando == "validar":
        planilha_alvo = args.planilha_caminho or planilha_alvo
        is_dry_run = True
    elif comando == "status":
        status_file = config.project_root / "data" / "status.json"
        status_dict = status.carregar_status(status_file)
        logger.info(f"=== Status da Automação ({status_file.name}) ===")
        if not status_dict.get("capas"):
            logger.info("Nenhuma capa registrada no status local.")
            return 0
        for capa_id, c in status_dict["capas"].items():
            logger.info(f"Capa {capa_id} ({c.get('data')} | {c.get('periodo')}): {c.get('status').upper()} (codRegistro={c.get('codRegistro')})")
            for p in c.get("paralisacoes", []):
                logger.info(f"  - {p.get('inicio')} -> {p.get('fim')} | {p.get('motivo_planilha')}: {p.get('status').upper()}")
        return 0

    # Fluxo principal (executar / validar / compatibilidade)
    if not Path(planilha_alvo).exists():
        logger.error(f"Planilha nao encontrada: {planilha_alvo}")
        return 1

    dados = ler_planilha(planilha_alvo)

    if is_dry_run or comando == "validar":
        mostrar_plano(dados, config)
        return 0

    if not config.login or not config.senha:
        logger.error("!! Credenciais ausentes. Configure OPENPORT_LOGIN e OPENPORT_SENHA no .env")
        return 1

    # Definir caminhos relativos ao projeto para persistência
    relatorios_dir = config.project_root / "relatorios"
    status_file = config.project_root / "data" / "status.json"

    num_rodada = obter_proxima_rodada(relatorios_dir)

    # Configurar FileHandler dinamicamente
    logs_dir = config.project_root / "logs"
    logs_dir.mkdir(exist_ok=True)
    file_handler = logging.FileHandler(logs_dir / f"rodada_{num_rodada:03d}.log", encoding="utf-8")
    file_handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s", datefmt="%H:%M:%S"))
    logging.getLogger().addHandler(file_handler)

    relatorio = Relatorio(relatorios_dir, num_rodada)

    executar(dados, config, relatorio, status_file, planilha_path=planilha_alvo)
    return 0

if __name__ == "__main__":
    sys.exit(main())
