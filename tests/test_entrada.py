from pathlib import Path

import openpyxl
import pytest

from paralisacao.entrada import deve_abrir_painel, resolver_entrada


def _xlsx(pasta: Path, nome: str) -> Path:
    caminho = pasta / nome
    wb = openpyxl.Workbook()
    wb.active["A1"] = "ok"
    wb.save(caminho)
    return caminho


def test_duplo_clique_abre_painel():
    assert deve_abrir_painel(None, None, False) is True
    assert deve_abrir_painel(None, "", False) is True


def test_comando_explicito_nao_abre_painel():
    assert deve_abrir_painel("executar", None, False) is False
    assert deve_abrir_painel(None, "navio.xlsx", False) is False
    assert deve_abrir_painel(None, None, True) is False
    assert deve_abrir_painel("painel", None, False) is False


def test_caminho_inexistente(tmp_path):
    with pytest.raises(ValueError, match="nao encontrada"):
        resolver_entrada(str(tmp_path / "ausente.xlsx"))


def test_arquivo_informado(tmp_path):
    arquivo = _xlsx(tmp_path, "navio.xlsx")
    assert resolver_entrada(str(arquivo)) == arquivo


def test_pasta_com_uma_planilha(tmp_path):
    arquivo = _xlsx(tmp_path, "navio.xlsx")
    assert resolver_entrada(str(tmp_path)) == arquivo


def test_pasta_sem_planilha(tmp_path):
    with pytest.raises(ValueError, match="Nenhuma planilha"):
        resolver_entrada(str(tmp_path))


def test_pasta_com_duas_planilhas(tmp_path):
    _xlsx(tmp_path, "a.xlsx")
    _xlsx(tmp_path, "b.xlsx")
    with pytest.raises(ValueError, match="mais de uma planilha"):
        resolver_entrada(str(tmp_path))


def test_arquivo_que_nao_e_planilha(tmp_path):
    arquivo = tmp_path / "notas.txt"
    arquivo.write_text("x", encoding="utf-8")
    with pytest.raises(ValueError, match=".xlsx"):
        resolver_entrada(str(arquivo))


def test_caminho_relativo_na_raiz(tmp_path, monkeypatch):
    outro = tmp_path / "outro"
    outro.mkdir()
    monkeypatch.chdir(outro)
    arquivo = _xlsx(tmp_path, "navio.xlsx")
    assert resolver_entrada("navio.xlsx", tmp_path) == arquivo
