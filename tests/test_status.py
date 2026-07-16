import json

import pytest

from paralisacao.config import Config
from paralisacao.planilha import Paralisacao
from paralisacao.status import (
    _atualizar_status_capa,
    _marcar_ok_no_status,
    _paralisacao_ok_no_status,
    carregar_status,
    paralisacao_ja_existe,
    salvar_status,
)


@pytest.fixture
def status_file(tmp_path):
    return tmp_path / "status.json"

@pytest.fixture
def config():
    return Config.from_env()

class TestCarregarStatus:
    def test_arquivo_inexistente(self, status_file):
        status_dict = carregar_status(status_file)
        assert status_dict["capas"] == {}

    def test_arquivo_existente(self, status_file):
        status_file.write_text('{"capas": {"1": {}}}', encoding="utf-8")
        status_dict = carregar_status(status_file)
        assert "1" in status_dict["capas"]

class TestSalvarStatus:
    def test_cria_arquivo(self, status_file):
        salvar_status({"capas": {}, "planilha": ""}, status_file)
        assert status_file.exists()
        dados = json.loads(status_file.read_text(encoding="utf-8"))
        assert "ultima_execucao" in dados

class TestStatusCapaLogic:
    def test_paralisacao_ok_e_marcacao(self):
        sc = {
            "codRegistro": 123,
            "paralisacoes": []
        }
        p = Paralisacao(inicio="13:00", fim="13:15", motivo="DDS")
        codigo = 34

        assert not _paralisacao_ok_no_status(sc, p, codigo)

        _marcar_ok_no_status(sc, p, codigo)
        assert _paralisacao_ok_no_status(sc, p, codigo)

        _atualizar_status_capa(sc)
        assert sc["status"] == "completa"

    def test_status_parcial(self):
        sc = {
            "codRegistro": 123,
            "paralisacoes": [
                {"inicio": "13:00", "fim": "13:15", "motivo_planilha": "DDS", "codigo": 34, "status": "ok"},
                {"inicio": "14:00", "fim": "14:15", "motivo_planilha": "Chuva", "codigo": 5, "status": "pendente"}
            ]
        }
        _atualizar_status_capa(sc)
        assert sc["status"] == "parcial"

class TestParalisacaoJaExiste:
    def test_paralisacao_existe_na_grid(self, config):
        grid = [
            ["Inicio", "Fim", "Motivo"],
            ["09/07/2026 13:00", "09/07/2026 13:15", "CONVENIENCIA DO USUARIO"],
        ]
        p = Paralisacao(inicio="13:00", fim="13:15", motivo="DDS")
        assert paralisacao_ja_existe(grid, p, 34, config)

    def test_paralisacao_nao_existe_na_grid(self, config):
        grid = [
            ["Inicio", "Fim", "Motivo"],
            ["09/07/2026 14:00", "09/07/2026 14:15", "CHUVA"],
        ]
        p = Paralisacao(inicio="13:00", fim="13:15", motivo="DDS")
        assert not paralisacao_ja_existe(grid, p, 34, config)
