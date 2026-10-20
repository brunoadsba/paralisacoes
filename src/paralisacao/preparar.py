import logging
from dataclasses import dataclass
from pathlib import Path

import openpyxl

from paralisacao.config import Config
from paralisacao.mapeamento import codigo_motivo, motivo_sistema, normalizar
from paralisacao.resumo import ResumoEmbarque, ler_resumo

logger = logging.getLogger("paralisacao.preparar")


@dataclass
class LinhaPadrao:
    registro: str
    navio: str
    data: str
    produto: str
    periodo: str
    inicio: str
    fim: str
    motivo: str


def periodo_de_inicio(inicio: str) -> str:
    """Turno OpenPort a partir do horário de início. A data da capa permanece a do bloco."""
    hora, minuto = (int(parte) for parte in inicio.split(":")[:2])
    minutos = hora * 60 + minuto
    if minutos >= 19 * 60 or minutos < 60:
        return "19:00/01:00"
    if minutos < 7 * 60:
        return "01:00/07:00"
    if minutos < 13 * 60:
        return "07:00/13:00"
    return "13:00/19:00"


def montar_linhas(resumo: ResumoEmbarque) -> list[LinhaPadrao]:
    registros: dict[tuple[str, str], str] = {}
    linhas: list[LinhaPadrao] = []
    for evento in resumo.eventos:
        periodo = periodo_de_inicio(evento.inicio)
        chave = (evento.data, periodo)
        if chave not in registros:
            registros[chave] = str(len(registros) + 1)
        linhas.append(
            LinhaPadrao(
                registro=registros[chave],
                navio=resumo.navio,
                data=evento.data,
                produto=resumo.produto,
                periodo=periodo,
                inicio=evento.inicio,
                fim=evento.fim,
                motivo=evento.motivo,
            )
        )
    return linhas


def gravar_planilha_padrao(
    caminho: str | Path,
    resumo: ResumoEmbarque,
    linhas: list[LinhaPadrao],
    programacao: str,
    operador: str,
) -> None:
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Paralisações"
    ws.append(["Operador Intermarítima", operador])
    ws.append(["Agência", resumo.agencia])
    ws.append(["Programação do navio", programacao or None])
    ws.append(["Turno 1", "01:00 - 07:00"])
    ws.append(["Turno 2", "07:00 - 13:00"])
    ws.append(["Turno 3", "13:00 - 19:00"])
    ws.append(["Turno 4", "19:00 - 01:00"])
    ws.append([])
    ws.append(["Registro", "Navio", "Data", "Produto", "Período", "Início", "Fim", "Motivo"])
    for linha in linhas:
        ws.append([
            linha.registro,
            linha.navio,
            linha.data,
            linha.produto,
            linha.periodo,
            linha.inicio,
            linha.fim,
            linha.motivo,
        ])
    destino = Path(caminho)
    destino.parent.mkdir(parents=True, exist_ok=True)
    wb.save(destino)


def pendencias(linhas: list[LinhaPadrao], config: Config, programacao: str) -> list[str]:
    faltas: list[str] = []
    if not programacao.strip():
        faltas.append("Programação do navio")
    vistos: set[str] = set()
    for linha in linhas:
        if linha.motivo in vistos:
            continue
        vistos.add(linha.motivo)
        nome = motivo_sistema(linha.motivo, config)
        codigo = codigo_motivo(nome, config) if nome else None
        if not codigo:
            faltas.append(linha.motivo)
    return faltas


def dados_de_linhas(linhas: list[LinhaPadrao], programacao: str):
    """Monta o objeto que o executor já sabe ler, sem passar de novo pelo Excel."""
    from paralisacao.planilha import Capa, DadosPlanilha, Paralisacao

    capas: dict[str, Capa] = {}
    ordem: list[str] = []
    for linha in linhas:
        if linha.registro not in capas:
            capas[linha.registro] = Capa(
                linha.registro, linha.navio, linha.data, linha.produto, linha.periodo, []
            )
            ordem.append(linha.registro)
        capas[linha.registro].paralisacoes.append(
            Paralisacao(linha.inicio, linha.fim, linha.motivo)
        )
    return DadosPlanilha(programacao or None, [capas[registro] for registro in ordem])


def apenas_primeira(dados):
    capa = dados.capas[0]
    from paralisacao.planilha import Capa, DadosPlanilha

    unica = Capa(
        capa.registro, capa.navio, capa.data, capa.produto, capa.periodo, capa.paralisacoes[:1]
    )
    return DadosPlanilha(dados.prog_navio, [unica])


def caminho_padrao(resumo: ResumoEmbarque, raiz: Path) -> Path:
    navio = normalizar(resumo.navio).replace(" ", "_") or "OPERACAO"
    data = resumo.eventos[0].data.replace("/", "-")
    return raiz / "data" / "operacoes" / f"{navio}_{data}.xlsx"


def executar_preparar(resumo_path: str, saida: str | None, programacao: str, operador: str, config: Config) -> int:
    resumo = ler_resumo(resumo_path)
    linhas = montar_linhas(resumo)
    destino = Path(saida) if saida else caminho_padrao(resumo, config.project_root)
    gravar_planilha_padrao(destino, resumo, linhas, programacao, operador)
    logger.info(f"Arquivo padrão: {destino}")
    logger.info(f"Navio: {resumo.navio} | Agência: {resumo.agencia} | Produto: {resumo.produto}")
    logger.info(f"Paralisações: {len(linhas)} | Capas: {len({ln.registro for ln in linhas})}")
    faltas = pendencias(linhas, config, programacao)
    if faltas:
        logger.warning("Pendências antes de executar no OpenPort: " + ", ".join(faltas))
        return 2
    logger.info("Nenhuma pendência. A planilha pode ir para validar e executar.")
    return 0
