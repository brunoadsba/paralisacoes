import json
import logging
import re
import unicodedata

from paralisacao.config import Config

logger = logging.getLogger("paralisacao.mapeamento")

_CODIGOS_MOTIVO_CACHE: dict[str, int] | None = None

def normalizar(texto: str) -> str:
    """Normaliza texto removendo acentuação, espaços extras e convertendo para maiúsculo."""
    texto = unicodedata.normalize("NFKD", texto)
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    return " ".join(texto.upper().split())

def turno_do_periodo(periodo: str, config: Config) -> dict | None:
    """Retorna a configuração do turno correspondente ao período (ex: '13:00/19:00')."""
    if not periodo or "/" not in periodo:
        return None
    inicio = periodo.split("/")[0].strip()
    return config.turnos.get(inicio)

def motivo_sistema(motivo: str, config: Config) -> str | None:
    """Retorna o nome do motivo no OpenPort correspondente ao motivo da planilha."""
    if not motivo:
        return None

    # Tenta carregar do arquivo externo motivos.json
    arquivo_motivos = config.project_root / "data" / "motivos.json"
    if arquivo_motivos.exists():
        try:
            dados_motivos = json.loads(arquivo_motivos.read_text(encoding="utf-8"))
            mapeamentos = dados_motivos.get("mapeamentos", {})
            normalized_motivo = normalizar(motivo)
            if normalized_motivo in mapeamentos:
                return mapeamentos[normalized_motivo]
        except Exception as e:
            logger.error(f"Erro ao ler motivos.json: {e}")

    return config.motivo_correspondencia.get(normalizar(motivo))

def _carregar_codigos_motivo(config: Config) -> dict[str, int]:
    """Carrega {descricao_upper: codigo} do arquivo tipo-paralizacoes.md."""
    arquivo = config.project_root / "data" / "tipo-paralizacoes.md"
    if not arquivo.exists():
        logger.warning(f"Arquivo de tipos de paralisação nao encontrado: {arquivo}")
        return {}

    codigos = {}
    try:
        conteudo = arquivo.read_text(encoding="utf-8")
        for linha in conteudo.splitlines():
            m = re.match(r"^\|\s*\d+\s*\|\s*(\d+)\s*\|\s*(.+?)\s*\|", linha)
            if m:
                codigos[m.group(2).strip().upper()] = int(m.group(1))
    except Exception as e:
        logger.error(f"Erro ao carregar codigos de motivo: {e}")
    return codigos

def codigo_motivo(nome_sistema: str, config: Config) -> int | None:
    """Retorna o codigo numerico do motivo a partir do nome no sistema."""
    global _CODIGOS_MOTIVO_CACHE
    if _CODIGOS_MOTIVO_CACHE is None:
        _CODIGOS_MOTIVO_CACHE = _carregar_codigos_motivo(config)
    return _CODIGOS_MOTIVO_CACHE.get(nome_sistema.strip().upper())
