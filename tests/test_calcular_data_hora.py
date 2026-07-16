from paralisacao.popup import _calcular_data_hora


class TestCalcularDataHora:
    def test_turno_diurno_sem_ajuste(self):
        # Turno 13:00-19:00, hora 15:00 → mesma data
        assert _calcular_data_hora("09/07/2026", "13:00/19:00", "15:00") == "09/07/2026 15:00"

    def test_turno_noturno_antes_meia_noite(self):
        # Turno 19:00-01:00, hora 23:50 → mesma data
        assert _calcular_data_hora("09/07/2026", "19:00/01:00", "23:50") == "09/07/2026 23:50"

    def test_turno_noturno_apos_meia_noite(self):
        # Turno 19:00-01:00, hora 00:45 → dia seguinte
        assert _calcular_data_hora("09/07/2026", "19:00/01:00", "00:45") == "10/07/2026 00:45"

    def test_hora_com_segundos(self):
        assert _calcular_data_hora("09/07/2026", "13:00/19:00", "13:00:00") == "09/07/2026 13:00"

    def test_hora_vazia(self):
        assert _calcular_data_hora("09/07/2026", "13:00/19:00", "") == "09/07/2026"
