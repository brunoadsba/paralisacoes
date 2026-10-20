"""Telas de resumo e pendências."""
import html
from pathlib import Path

from flask import redirect, request

from paralisacao.mapeamento import (
    codigo_motivo,
    motivo_sistema,
    normalizar,
    salvar_codigo_motivo,
    texto_observacao,
)
from paralisacao.planilha import ler_planilha
from paralisacao.preparar import (
    caminho_padrao,
    gravar_planilha_padrao,
    linhas_de_planilha,
    montar_linhas,
    pendencias,
    resumo_de_planilha,
)
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
            return pagina(_html_resumo(resumo_lido, linhas, config_fn()), 2)
        config = config_fn()
        destino_dir = Path(config.project_root) / "data" / "operacoes"
        salvos = _gravar_uploads(destino_dir, request.files.getlist("resumo"), request.files.getlist("pasta"))
        if not salvos:
            return pagina(form_resumo("Selecione a planilha ou uma pasta com um arquivo .xlsx."), 2)
        if len(salvos) > 1:
            nomes = ", ".join(item.name for item in salvos)
            return pagina(form_resumo(f"A pasta tem mais de uma planilha. Escolha o arquivo: {nomes}"), 2)
        destino = salvos[0]
        try:
            lido, linhas, programacao = _ler_escolha(destino)
        except ValueError as exc:
            return pagina(form_resumo(str(exc)), 2)
        with LOCK:
            STATE["resumo"] = lido
            STATE["linhas"] = linhas
            if programacao:
                STATE["programacao"] = programacao
            STATE["planilha"] = ""
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


def _gravar_uploads(destino_dir: Path, arquivos, pastas) -> list[Path]:
    destino_dir.mkdir(parents=True, exist_ok=True)
    escolhidos = list(arquivos or [])
    if not any(getattr(item, "filename", "") for item in escolhidos):
        escolhidos = list(pastas or [])
    salvos: list[Path] = []
    for item in escolhidos:
        nome = Path(getattr(item, "filename", "") or "").name
        if not nome or nome.startswith("~$") or Path(nome).suffix.lower() not in {".xlsx", ".xlsm"}:
            continue
        destino = destino_dir / nome
        item.save(destino)
        if destino not in salvos:
            salvos.append(destino)
    return salvos


def _ler_escolha(destino: Path):
    try:
        lido = ler_resumo(destino)
        return lido, montar_linhas(lido), ""
    except ValueError as erro_resumo:
        try:
            dados = ler_planilha(str(destino))
        except ValueError as erro_padrao:
            raise ValueError(
                "Não foi possível ler este arquivo como resumo da Intermarítima "
                f"nem como planilha padrão. {erro_padrao}"
            ) from erro_resumo
        if not dados.capas:
            raise ValueError("A planilha não tem paralisações.")
        return resumo_de_planilha(dados), linhas_de_planilha(dados), dados.prog_navio or ""


def _html_resumo(resumo_lido, linhas, config) -> str:
    partes = []
    for linha in linhas:
        nome = motivo_sistema(linha.motivo, config)
        codigo = codigo_motivo(nome, config) if nome else None
        if codigo and normalizar(linha.motivo) != normalizar(nome):
            aberto = (
                f"{codigo} · {html.escape(nome)}"
                f"<br><span class=\"mutedx\">Observação: {html.escape(texto_observacao(linha.motivo, nome))}</span>"
            )
        elif codigo:
            aberto = f"{codigo} · {html.escape(nome)}"
        else:
            aberto = "código pendente"
        partes.append(
            "<tr>"
            f"<td>{html.escape(linha.registro)}</td>"
            f"<td>{html.escape(linha.data)}</td>"
            f"<td>{html.escape(linha.periodo)}</td>"
            f"<td>{html.escape(linha.inicio)} → {html.escape(linha.fim)}</td>"
            f"<td>{html.escape(linha.motivo)}</td>"
            f"<td>{aberto}</td></tr>"
        )
    capas = len({linha.registro for linha in linhas})
    return painel_resumo(
        resumo_lido.navio, resumo_lido.agencia, resumo_lido.produto,
        capas, len(linhas), "".join(partes),
    )
