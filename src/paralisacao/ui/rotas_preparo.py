"""Telas de resumo e pendências."""
import html
from pathlib import Path

from flask import redirect, request

from paralisacao.mapeamento import salvar_codigo_motivo
from paralisacao.preparar import caminho_padrao, gravar_planilha_padrao, montar_linhas, pendencias
from paralisacao.resumo import ler_resumo
from paralisacao.ui.estado import LOCK, STATE
from paralisacao.ui.paginas import form_pendencias, form_resumo, painel_resumo


def registrar(app, pagina, config_fn) -> None:
    @app.route("/resumo", methods=["GET", "POST"])
    def resumo():
        if request.method == "GET":
            with LOCK:
                resumo_lido = STATE["resumo"]
                linhas = list(STATE["linhas"])
            if resumo_lido is None:
                return pagina(form_resumo(), 2)
            return pagina(_html_resumo(resumo_lido, linhas), 2)
        arquivo = request.files.get("resumo")
        if arquivo is None or not arquivo.filename:
            return pagina(form_resumo("Selecione a planilha do resumo."), 2)
        destino = Path(config_fn().project_root) / "data" / "operacoes" / "resumo_recebido.xlsx"
        destino.parent.mkdir(parents=True, exist_ok=True)
        arquivo.save(destino)
        try:
            lido = ler_resumo(destino)
            linhas = montar_linhas(lido)
        except ValueError as exc:
            return pagina(form_resumo(str(exc)), 2)
        with LOCK:
            STATE["resumo"] = lido
            STATE["linhas"] = linhas
            STATE["uma_ok"] = False
            STATE["situacao"] = {}
        return redirect("/resumo")

    @app.route("/pendencias", methods=["GET", "POST"])
    def pendencias_view():
        config = config_fn()
        with LOCK:
            linhas = list(STATE["linhas"])
            programacao = STATE["programacao"]
            resumo_lido = STATE["resumo"]
        if not linhas or resumo_lido is None:
            return redirect("/resumo")
        if request.method == "POST":
            programacao = request.form.get("programacao", "").strip()
            motivos = request.form.getlist("motivo")
            codigos = request.form.getlist("codigo")
            for motivo, codigo in zip(motivos, codigos, strict=False):
                if codigo.strip().isdigit():
                    salvar_codigo_motivo(config, motivo, int(codigo.strip()))
            faltas = pendencias(linhas, config, programacao)
            if faltas:
                motivos_falta = [item for item in faltas if item != "Programação do navio"]
                return pagina(form_pendencias(programacao, motivos_falta, ", ".join(faltas)), 3)
            destino = caminho_padrao(resumo_lido, config.project_root)
            gravar_planilha_padrao(destino, resumo_lido, linhas, programacao, "30002")
            with LOCK:
                STATE["programacao"] = programacao
                STATE["planilha"] = str(destino)
            return redirect("/execucao")
        faltas = pendencias(linhas, config, programacao)
        motivos_falta = [item for item in faltas if item != "Programação do navio"]
        return pagina(form_pendencias(programacao, motivos_falta), 3)


def _html_resumo(resumo_lido, linhas) -> str:
    partes = []
    for linha in linhas:
        partes.append(
            "<tr>"
            f"<td>{html.escape(linha.registro)}</td>"
            f"<td>{html.escape(linha.data)}</td>"
            f"<td>{html.escape(linha.periodo)}</td>"
            f"<td>{html.escape(linha.inicio)} → {html.escape(linha.fim)}</td>"
            f"<td>{html.escape(linha.motivo)}</td></tr>"
        )
    capas = len({linha.registro for linha in linhas})
    return painel_resumo(
        resumo_lido.navio, resumo_lido.agencia, resumo_lido.produto,
        capas, len(linhas), "".join(partes),
    )
