"""Execução no OpenPort em thread, uma paralisação ou o lote."""
import logging
import threading
from dataclasses import replace

from paralisacao.config import Config
from paralisacao.preparar import apenas_primeira, dados_de_linhas
from paralisacao.ui.ambiente import url_operacao
from paralisacao.ui.estado import LOCK, STATE

logger = logging.getLogger("paralisacao.ui.execucao")


class _LogPainel(logging.Handler):
    def emit(self, record: logging.LogRecord) -> None:
        with LOCK:
            STATE["log"].append(self.format(record))


def _anexar_log() -> _LogPainel:
    handler = _LogPainel()
    handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s", "%H:%M:%S"))
    logging.getLogger().addHandler(handler)
    return handler


def iniciar(escopo: str) -> str | None:
    with LOCK:
        if STATE["running"]:
            return "Já existe uma execução em andamento."
        if escopo == "lote" and not STATE["uma_ok"]:
            return "O lote só libera depois da primeira paralisação."
        if not STATE["planilha"] or not STATE["senha"] or not STATE["linhas"]:
            return "Preencha o acesso e as pendências antes de executar."
        STATE["running"] = True
        STATE["phase"] = "Abrindo o OpenPort"
        STATE["proc"] = 0
        STATE["tot"] = 1 if escopo == "uma" else len(STATE["linhas"])
        STATE["log"] = []
    threading.Thread(target=_rodar, args=(escopo,), daemon=True).start()
    return None


def _rodar(escopo: str) -> None:
    from paralisacao.main import executar
    from paralisacao.relatorio import Relatorio, obter_proxima_rodada

    handler = _anexar_log()
    try:
        base = Config.from_env()
        with LOCK:
            config = replace(
                base,
                url=url_operacao(STATE["modo"]),
                login=STATE["usuario"],
                senha=STATE["senha"],
                headless=False,
                primeiro_plano=True,
                manter_aberto_seg=8,
                planilha=STATE["planilha"],
            )
            dados = dados_de_linhas(STATE["linhas"], STATE["programacao"])
            if escopo == "uma":
                dados = apenas_primeira(dados)
            planilha = STATE["planilha"]
            primeira = STATE["linhas"][0]
            chave_primeira = f"{primeira.registro}|{primeira.inicio}|{primeira.motivo}"
        relatorios = config.project_root / "relatorios"
        numero = obter_proxima_rodada(relatorios)
        relatorio = Relatorio(relatorios, numero)
        status_file = config.project_root / "data" / "status.json"
        with LOCK:
            STATE["phase"] = "Gravando no OpenPort"
        executar(dados, config, relatorio, status_file, planilha_path=planilha)
        texto = ""
        caminho = relatorios / f"rodada_{numero:03d}.md"
        if caminho.exists():
            texto = caminho.read_text(encoding="utf-8")
        with LOCK:
            STATE["relatorio"] = texto
            STATE["proc"] = len(relatorio.paralisacoes_ok)
            if relatorio.paralisacoes_ok:
                STATE["uma_ok"] = True
                if escopo == "uma":
                    STATE["situacao"][chave_primeira] = "gravada"
                elif len(relatorio.paralisacoes_ok) == len(STATE["linhas"]):
                    for linha in STATE["linhas"]:
                        chave = f"{linha.registro}|{linha.inicio}|{linha.motivo}"
                        STATE["situacao"][chave] = "gravada"
            STATE["phase"] = "Concluída" if relatorio.paralisacoes_ok else "Falhou"
    except Exception as exc:
        logger.exception("Falha na execução")
        with LOCK:
            STATE["phase"] = f"Falhou: {exc}"
            STATE["log"].append(str(exc))
    finally:
        logging.getLogger().removeHandler(handler)
        with LOCK:
            STATE["running"] = False


def linhas_html() -> str:
    import html

    with LOCK:
        situacao = dict(STATE["situacao"])
        linhas = list(STATE["linhas"])
    partes = []
    for linha in linhas:
        chave = f"{linha.registro}|{linha.inicio}|{linha.motivo}"
        status = situacao.get(chave, "na fila")
        partes.append(
            "<tr>"
            f"<td>{html.escape(linha.registro)}</td>"
            f"<td>{html.escape(linha.inicio)} → {html.escape(linha.fim)}</td>"
            f"<td>{html.escape(linha.motivo)}</td>"
            f"<td>{html.escape(status)}</td>"
            "</tr>"
        )
    return "".join(partes)
