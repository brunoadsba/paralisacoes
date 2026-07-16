import pytest

from paralisacao.config import Config
from paralisacao.mapeamento import codigo_motivo, motivo_sistema, normalizar, turno_do_periodo


@pytest.fixture
def config():
    return Config.from_env()

class TestNormalizar:
    def test_remove_acentos(self):
        assert normalizar("Conveniência") == "CONVENIENCIA"

    def test_uppercase(self):
        assert normalizar("chuva") == "CHUVA"

    def test_espacos_multiplos(self):
        assert normalizar("  defeito   no   speed  ") == "DEFEITO NO SPEED"

    def test_unicode_nfkd(self):
        assert normalizar("DDS / CONVENIÊNCIA") == "DDS / CONVENIENCIA"

class TestTurnoDoPeriodo:
    @pytest.mark.parametrize("periodo,esperado", [
        ("01:00/07:00", 1),
        ("07:00/13:00", 2),
        ("13:00/19:00", 3),
        ("19:00/01:00", 4),
    ])
    def test_turnos_validos(self, config, periodo, esperado):
        turno = turno_do_periodo(periodo, config)
        assert turno is not None
        assert turno["numero"] == esperado

    def test_periodo_invalido(self, config):
        assert turno_do_periodo("08:00/14:00", config) is None

class TestMotivoSistema:
    def test_mapeamento_direto(self, config):
        assert motivo_sistema("CHUVA", config) == "CHUVA"

    def test_mapeamento_dds(self, config):
        assert motivo_sistema("DDS", config) == "CONVENIENCIA DO USUARIO"

    def test_case_insensitive(self, config):
        assert motivo_sistema("chuva", config) == "CHUVA"

    def test_motivo_desconhecido(self, config):
        assert motivo_sistema("MOTIVO_INEXISTENTE", config) is None

class TestCodigoMotivo:
    def test_codigo_valido(self, config):
        assert codigo_motivo("CHUVA", config) == 5
        assert codigo_motivo("CONVENIENCIA DO USUARIO", config) == 34
        assert codigo_motivo("DEFEITO MECANICO LINHA DE EMBARQUE", config) == 304

    def test_codigo_invalido(self, config):
        assert codigo_motivo("CODIGO_INEXISTENTE", config) is None
