import os
import sys
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv


@dataclass(frozen=True)
class Config:
    url: str
    login: str
    senha: str
    planilha: str
    headless: bool
    primeiro_plano: bool
    timeout_ms: int
    slow_mo_ms: int
    pausa_visual_ms: int
    manter_aberto_seg: int
    estadia_label: str
    operador: str
    project_root: Path
    css: dict[str, str] = field(default_factory=dict)
    motivo_correspondencia: dict[str, str] = field(default_factory=dict)
    turnos: dict[str, dict] = field(default_factory=dict)

    @classmethod
    def from_env(cls, dotenv_path: str | None = None) -> "Config":
        if getattr(sys, "frozen", False):
            project_root = Path(getattr(sys, "_MEIPASS"))
            load_dotenv(Path(sys.executable).resolve().parent / ".env")
        else:
            project_root = Path(__file__).resolve().parent.parent.parent
            load_dotenv(project_root / ".env")
        load_dotenv(dotenv_path)

        primeiro_plano = os.getenv("PRIMEIRO_PLANO", "true").strip().lower() in ("1", "true", "yes", "sim")
        headless = os.getenv("HEADLESS", "false").strip().lower() in ("1", "true", "yes", "sim")

        css = {
            # Login
            "login": "input#User",
            "senha": "input#Pass",
            "entrar": "button#Entrar",
            # Menu
            "menu_acesso": "input#txtMenuAccess",
            # 7001 — busca/listagem
            "busca_operador": "#sqlNUM_EMPRESA_2",
            "busca_prog_navio": "#SqlNUM_PROGR_NAVIO_2",
            "busca_data": "#sqlDAT_INICIO",
            "busca_turno": "select#sqlNUM_TURNO",
            "btn_filtrar": "button#BPESQUISAR",
            "btn_novo": "button#INSERIR",
            "grid_resultados": "table#TQuery",
            # 7001 — formulario da capa
            "capa_operador": "#NUM_EMPRESA_2",
            "capa_prog_navio": "#NUM_PROGR_NAVIO_2",
            "capa_data": "#DAT_INICIO",
            "capa_turno": "select#NUM_TURNO",
            "btn_gravar_capa": "button#GRAVAR",
            "aba_paralisacao": "li#Aba6 a",
            # Popup dlgEdtInformParalisManual — CADASTRO DE PARALISAÇÃO
            "popup_motivo": "#NUM_TIP_PARALIS_2",
            "popup_btn_motivo": "#ANUM_TIP_PARALIS",
            "popup_estadia": "#NUM_ESTADIA_BERCO",
            "popup_data_inicio": "#DAT_INICIO",
            "popup_hora_inicio": "#DAT_INICIO_2",
            "popup_data_fim": "#DAT_FIM",
            "popup_hora_fim": "#DAT_FIM_2",
            "popup_observacao": "#DCR_OBS",
            "popup_btn_gravar": "button#GRAVAR",
            # Botao ⊕ verde na aba Paralisacao (abre o popup)
            "btn_adicionar_paralisacao": "#Detail7 table thead a img",
        }

        motivo_correspondencia = {
            "CHUVA":                          "CHUVA",
            "DDS":                            "TROCA TURNO - AGUARD. TPA",
            "DESCANSO":                       "CONVENIENCIA DO USUARIO",
            "DDS / CONVENIENCIA DO USUARIO":  "CONVENIENCIA DO USUARIO",
            "DEFEITO NO SPEED":               "DEFEITO MECANICO LINHA DE EMBARQUE",
        }

        turnos = {
            "01:00": {"numero": 1, "label": "1:00 - 7:00"},
            "07:00": {"numero": 2, "label": "7:00 - 13:00"},
            "13:00": {"numero": 3, "label": "13:00 - 19:00"},
            "19:00": {"numero": 4, "label": "19:00 - 1:00"},
        }

        return cls(
            url=os.getenv("OPENPORT_URL", "https://openportilheus.codeba.gov.br/openportcodeba/"),
            login=os.getenv("OPENPORT_LOGIN", ""),
            senha=os.getenv("OPENPORT_SENHA", ""),
            planilha=os.getenv("PLANILHA", ""),
            headless=headless,
            primeiro_plano=primeiro_plano,
            timeout_ms=int(os.getenv("TIMEOUT_MS", "30000")),
            slow_mo_ms=int(os.getenv("SLOW_MO_MS", "400" if primeiro_plano else "0")),
            pausa_visual_ms=int(os.getenv("PAUSA_VISUAL_MS", "800" if primeiro_plano else "0")),
            manter_aberto_seg=int(os.getenv("MANTER_ABERTO_SEG", "600")),
            estadia_label=os.getenv("ESTADIA_LABEL", "").strip(),
            operador="30002",
            project_root=project_root,
            css=css,
            motivo_correspondencia=motivo_correspondencia,
            turnos=turnos,
        )

# Instância padrão para manter compatibilidade com código existente
_config_instance = Config.from_env()

URL = _config_instance.url
URL_INTRANET = os.getenv("OPENPORT_URL_INTRANET", "")
LOGIN = _config_instance.login
SENHA = _config_instance.senha
PLANILHA = _config_instance.planilha
HEADLESS = _config_instance.headless
PRIMEIRO_PLANO = _config_instance.primeiro_plano
TIMEOUT_MS = _config_instance.timeout_ms
SLOW_MO_MS = _config_instance.slow_mo_ms
PAUSA_VISUAL_MS = _config_instance.pausa_visual_ms
MANTER_ABERTO_SEG = _config_instance.manter_aberto_seg
ESTADIA_LABEL = _config_instance.estadia_label
OPERADOR_INTERMARITIMA = _config_instance.operador
CSS = _config_instance.css
MOTIVO_CORRESPONDENCIA = _config_instance.motivo_correspondencia
TURNOS = _config_instance.turnos
