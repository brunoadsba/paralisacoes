import logging
from collections import Counter
from datetime import datetime
from pathlib import Path

from paralisacao.planilha import Paralisacao

logger = logging.getLogger("paralisacao.relatorio")

class Relatorio:
    def __init__(self, diretorio_saida: Path, num_rodada: int):
        self.inicio = datetime.now()
        self.planilha = ""
        self.diretorio_saida = diretorio_saida
        self.num_rodada = num_rodada
        self.capas_ok: list[str] = []
        self.capas_nao_encontradas: list[str] = []
        self.capas_erro: list[str] = []
        self.paralisacoes_ok: list[str] = []
        self.paralisacoes_puladas: list[str] = []
        self.paralisacoes_erro: list[str] = []
        self.erros_detalhe: list[str] = []

    def add_capa_ok(self, registro: str, cod: int):
        self.capas_ok.append(f"Capa {registro} (codRegistro={cod})")

    def add_capa_nao_encontrada(self, registro: str):
        self.capas_nao_encontradas.append(f"Capa {registro}: nao existe no OpenPort")

    def add_capa_erro(self, registro: str, motivo: str):
        self.capas_erro.append(f"Capa {registro}: {motivo}")

    def add_paralisacao_ok(self, capa: str, p: Paralisacao):
        self.paralisacoes_ok.append(f"Capa {capa} | {p.inicio} -> {p.fim} | {p.motivo}")

    def add_paralisacao_pulada(self, capa: str, p: Paralisacao, motivo: str):
        self.paralisacoes_puladas.append(f"Capa {capa} | {p.inicio} -> {p.fim} | {p.motivo} | {motivo}")

    def add_paralisacao_erro(self, capa: str, p: Paralisacao, erro: str):
        self.paralisacoes_erro.append(f"Capa {capa} | {p.inicio} -> {p.fim} | {p.motivo} | {erro}")
        self.erros_detalhe.append(f"Capa {capa} - {p.inicio}->{p.fim} ({p.motivo}): {erro}")

    def gerar_arquivo(self, planilha_path: str = ""):
        fim = datetime.now()
        duracao = (fim - self.inicio).total_seconds()
        relatorio_path = self.diretorio_saida / f"rodada_{self.num_rodada:03d}.md"

        planilha_exibida = planilha_path or self.planilha

        total_capas = len(self.capas_ok) + len(self.capas_nao_encontradas) + len(self.capas_erro)
        total_para_ok = len(self.paralisacoes_ok)
        total_para_pul = len(self.paralisacoes_puladas)
        total_para_err = len(self.paralisacoes_erro)

        nenhuma_paralisacao_registrada = total_para_ok == 0

        linhas = []
        linhas.append(f"# Relatório de Execução - Rodada {self.num_rodada:03d}")
        linhas.append("")
        linhas.append(f"**Data:** {self.inicio:%d/%m/%Y %H:%M:%S}")
        linhas.append(f"**Duração:** {duracao:.0f}s ({duracao/60:.1f}min)")
        linhas.append(f"**Planilha:** {planilha_exibida}")
        linhas.append("")

        # Conclusao executiva
        linhas.append("## Resultado da Execução")
        linhas.append("")

        def _plu(n: int, sing: str, plur: str) -> str:
            return sing if n == 1 else plur

        partes_conclusao = []
        if total_para_ok > 0:
            n = total_para_ok
            partes_conclusao.append(
                f"{n} {_plu(n, 'paralisação foi registrada', 'paralisações foram registradas')} "
                "com sucesso no OpenPort."
            )
        if total_para_pul > 0:
            n = total_para_pul
            partes_conclusao.append(
                f"{n} {_plu(n, 'paralisação foi pulada', 'paralisações foram puladas')} "
                "porque o motivo não está mapeado no config.motivo_correspondencia."
            )
        if total_para_err > 0:
            n = total_para_err
            partes_conclusao.append(
                f"{n} {_plu(n, 'paralisação apresentou', 'paralisações apresentaram')} "
                "erro durante o registro."
            )
        if nenhuma_paralisacao_registrada and total_para_pul == 0 and total_para_err == 0:
            partes_conclusao.append(
                "Nenhuma paralisação foi registrada porque não havia dados a processar."
            )

        if len(self.capas_ok) > 0:
            n = len(self.capas_ok)
            partes_conclusao.append(
                f"{n} {_plu(n, 'capa foi aberta', 'capas foram abertas')} para edição."
            )
        if len(self.capas_nao_encontradas) > 0:
            n = len(self.capas_nao_encontradas)
            partes_conclusao.append(
                f"{n} {_plu(n, 'capa não existe', 'capas não existem')} no OpenPort "
                "e precisam ser criadas."
            )
        if len(self.capas_erro) > 0:
            n = len(self.capas_erro)
            partes_conclusao.append(
                f"{n} {_plu(n, 'capa apresentou', 'capas apresentaram')} erro na busca."
            )

        for p in partes_conclusao:
            linhas.append(f"- {p}")
        linhas.append("")

        # Tabela resumo
        linhas.append("## Indicadores")
        linhas.append("")
        linhas.append("| Indicador | Valor |")
        linhas.append("|---|---|")
        linhas.append(f"| Capas na planilha | {total_capas} |")
        linhas.append(f"| Capas encontradas e abertas | {len(self.capas_ok)} |")
        linhas.append(f"| Capas inexistentes no OpenPort | {len(self.capas_nao_encontradas)} |")
        linhas.append(f"| Capas com erro de busca | {len(self.capas_erro)} |")
        linhas.append(f"| Paralisações registradas | {total_para_ok} |")
        linhas.append(f"| Paralisações puladas (motivo não mapeado) | {total_para_pul} |")
        linhas.append(f"| Paralisações com erro | {total_para_err} |")
        linhas.append("")

        # Detalhamento
        if self.capas_ok:
            linhas.append("## ✅ Capas Encontradas e Abertas")
            linhas.append("")
            for c in self.capas_ok:
                linhas.append(f"- {c}")
            linhas.append("")

        if self.capas_nao_encontradas:
            linhas.append("## ⏭️ Capas Inexistentes no OpenPort")
            linhas.append("")
            n = len(self.capas_nao_encontradas)
            if n == 1:
                linhas.append("Esta capa está na planilha mas não foi encontrada no OpenPort. "
                               "Precisa ser criada antes de registrar as paralisações.")
            else:
                linhas.append(f"Estas {n} capas estão na planilha mas não foram encontradas no OpenPort. "
                               "Precisam ser criadas antes de registrar as paralisações.")
            linhas.append("")
            for c in self.capas_nao_encontradas:
                linhas.append(f"- {c}")
            linhas.append("")

        if self.capas_erro:
            linhas.append("## ❌ Capas com Erro de Busca")
            linhas.append("")
            for c in self.capas_erro:
                linhas.append(f"- {c}")
            linhas.append("")

        if self.paralisacoes_ok:
            linhas.append("### ✅ Paralisações Registradas")
            linhas.append("")
            for p in self.paralisacoes_ok:
                linhas.append(f"- {p}")
            linhas.append("")

        if self.paralisacoes_puladas:
            linhas.append("## ⏭️ Paralisações Puladas")
            linhas.append("")
            linhas.append("Motivo: o tipo de paralisação não está mapeado. "
                          "O RPA não sabe em qual linha da tabela de lookup clicar.")
            linhas.append("")
            for p in self.paralisacoes_puladas:
                linhas.append(f"- {p}")
            linhas.append("")

            motivos_agrupados = Counter()
            for p in self.paralisacoes_puladas:
                partes = p.split(" | ")
                if len(partes) >= 3:
                    motivos_agrupados[partes[2]] += 1
            if motivos_agrupados:
                linhas.append("### Motivos não mapeados (ocorrências)")
                linhas.append("")
                for motivo, qtd in sorted(motivos_agrupados.items(), key=lambda x: -x[1]):
                    linhas.append(f"- {motivo}: {qtd}x")
                linhas.append("")

        if self.paralisacoes_erro:
            linhas.append("## ❌ Paralisações com Erro de Registro")
            linhas.append("")
            for p in self.paralisacoes_erro:
                linhas.append(f"- {p}")
            linhas.append("")

        if self.erros_detalhe:
            linhas.append("### Detalhamento dos Erros")
            linhas.append("")
            for e in self.erros_detalhe:
                linhas.append(f"- {e}")
            linhas.append("")

        # Diagnóstico da rodada
        linhas.append("## 🔍 Diagnóstico da Rodada")
        linhas.append("")

        diagnosticos = []
        if total_para_pul > 0:
            diagnosticos.append(
                f"- **Motivos não mapeados**: {total_para_pul} paralisações foram puladas. "
                "O RPA sabe quais capas abrir mas não consegue selecionar o motivo."
            )
        if len(self.capas_nao_encontradas) > 0:
            c = len(self.capas_nao_encontradas)
            s_capa = "capa" if c == 1 else "capas"
            diagnosticos.append(
                f"- **Capas inexistentes**: {c} {s_capa} da planilha não foram encontradas no "
                "OpenPort. O RPA tentou criá-las automaticamente."
            )
        if total_para_err > 0:
            diagnosticos.append(
                f"- **Falhas de registro**: {total_para_err} paralisações falharam ao ser "
                "registradas. Revisar os logs e screenshots para identificar a causa."
            )
        if total_para_ok > 0 and total_para_pul == 0 and total_para_err == 0:
            diagnosticos.append(
                f"- **Sucesso total**: todas as {total_para_ok} paralisações foram registradas "
                "em todas as capas processadas."
            )
        if not diagnosticos:
            diagnosticos.append(
                "- Nenhuma ação foi executada. Verifique se a planilha contém dados válidos."
            )

        for d in diagnosticos:
            linhas.append(d)
        linhas.append("")

        # Proximos passos
        linhas.append("## 🚀 Próximos Passos")
        linhas.append("")

        passo = 1
        if total_para_pul > 0:
            linhas.append(f"{passo}. **Mapear motivos**: abrir manualmente o lookup `dlgPsqTipoParalisacao` "
                          "no OpenPort, identificar o motivo pendente e atualizar `config.py` ou `motivos.json`.")
            passo += 1
        if len(self.capas_nao_encontradas) > 0:
            s_capa = "capa" if len(self.capas_nao_encontradas) == 1 else "capas"
            linhas.append(f"{passo}. **Verificar capas criadas**: "
                          f"confirmar se as {len(self.capas_nao_encontradas)} {s_capa} foram criadas corretamente.")
            passo += 1
        if nenhuma_paralisacao_registrada:
            linhas.append(f"{passo}. **Re-executar o RPA** após ajustes.")
            passo += 1
        else:
            linhas.append(f"{passo}. **Verificar no OpenPort**: confirmar se as paralisações "
                          "foram registradas corretamente em cada capa.")

        self.diretorio_saida.mkdir(exist_ok=True)
        relatorio_path.write_text("\n".join(linhas), encoding="utf-8")
        logger.info(f"\n>>> Relatório salvo: {relatorio_path}")

def obter_proxima_rodada(diretorio_saida: Path) -> int:
    """Retorna o número da próxima rodada de execução baseado nos relatórios existentes."""
    if not diretorio_saida.exists():
        return 1
    existentes = [int(p.stem.split("_")[1]) for p in diretorio_saida.glob("rodada_*.md")]
    return max(existentes) + 1 if existentes else 1
