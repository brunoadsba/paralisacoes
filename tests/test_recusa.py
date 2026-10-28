from paralisacao.browser import alerta_de_recusa
from paralisacao.retry import com_retry


def test_alerta_com_codigo_e_recusa():
    assert alerta_de_recusa("40030; Data de Início da paralisação está fora do período da turma")
    assert alerta_de_recusa("7052010; A data informada está fora do período da estadia.")
    assert alerta_de_recusa("Os Dados não foram Salvos. Descartar Alteracoes?") is None
    assert alerta_de_recusa("") is None


def test_recusa_nao_dispara_nova_tentativa():
    chamadas = {"n": 0}

    @com_retry(tentativas=3, backoff_base=0)
    def gravar():
        chamadas["n"] += 1
        if alerta_de_recusa("40030; fora do período"):
            return False
        raise RuntimeError("nao deveria repetir")

    assert gravar() is False
    assert chamadas["n"] == 1
