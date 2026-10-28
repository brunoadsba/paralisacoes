from paralisacao.config import Config
from paralisacao.planilha import DadosPlanilha, Paralisacao
from paralisacao.relatorio import Relatorio


def test_rodada_so_com_ja_lancadas_sai_zero(tmp_path):
    relatorio = Relatorio(tmp_path, 1)
    relatorio.add_paralisacao_ok("1", Paralisacao("13:00", "13:15", "DDS"))
    assert relatorio.codigo_de_saida() == 0


def test_motivo_nao_mapeado_sai_zero(tmp_path):
    relatorio = Relatorio(tmp_path, 1)
    relatorio.add_paralisacao_pulada("1", Paralisacao("13:00", "13:15", "X"), "nao mapeado")
    assert relatorio.codigo_de_saida() == 0


def test_recusa_sai_um(tmp_path):
    relatorio = Relatorio(tmp_path, 1)
    relatorio.add_paralisacao_erro("1", Paralisacao("01:00", "01:15", "DDS"), "40030; fora do turno")
    assert relatorio.codigo_de_saida() == 1


def test_capa_com_erro_sai_um(tmp_path):
    relatorio = Relatorio(tmp_path, 1)
    relatorio.add_capa_erro("1", "grade de paralisações ilegível")
    assert relatorio.codigo_de_saida() == 1


def test_capa_inexistente_sai_um(tmp_path):
    relatorio = Relatorio(tmp_path, 1)
    relatorio.add_capa_nao_encontrada("2")
    assert relatorio.codigo_de_saida() == 1


def test_falha_fatal_sai_um(tmp_path):
    relatorio = Relatorio(tmp_path, 1)
    assert relatorio.codigo_de_saida(falha_fatal=True) == 1


def _config(tmp_path) -> Config:
    return Config(
        url="http://localhost",
        login="usuario",
        senha="senha",
        planilha="",
        headless=True,
        primeiro_plano=False,
        timeout_ms=1000,
        slow_mo_ms=0,
        pausa_visual_ms=0,
        manter_aberto_seg=0,
        estadia_label="",
        operador="30002",
        project_root=tmp_path,
    )


def test_main_devolve_falha_da_execucao(monkeypatch, tmp_path):
    from paralisacao.main import main

    monkeypatch.setattr("sys.argv", ["paralisacao", "--planilha", "a.xlsx"])
    monkeypatch.setattr("paralisacao.main.Config.from_env", lambda: _config(tmp_path))
    monkeypatch.setattr("paralisacao.main.resolver_entrada", lambda caminho, raiz=None: tmp_path / "a.xlsx")
    monkeypatch.setattr("paralisacao.main.ler_planilha", lambda caminho: DadosPlanilha("1772", []))
    monkeypatch.setattr("paralisacao.main.obter_proxima_rodada", lambda diretorio: 1)
    monkeypatch.setattr("paralisacao.main.executar", lambda *args, **kwargs: 1)
    assert main() == 1


def test_main_devolve_zero_quando_a_execucao_conclui(monkeypatch, tmp_path):
    from paralisacao.main import main

    monkeypatch.setattr("sys.argv", ["paralisacao", "--planilha", "a.xlsx"])
    monkeypatch.setattr("paralisacao.main.Config.from_env", lambda: _config(tmp_path))
    monkeypatch.setattr("paralisacao.main.resolver_entrada", lambda caminho, raiz=None: tmp_path / "a.xlsx")
    monkeypatch.setattr("paralisacao.main.ler_planilha", lambda caminho: DadosPlanilha("1772", []))
    monkeypatch.setattr("paralisacao.main.obter_proxima_rodada", lambda diretorio: 1)
    monkeypatch.setattr("paralisacao.main.executar", lambda *args, **kwargs: 0)
    assert main() == 0
