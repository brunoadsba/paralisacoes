import json
import logging
import re
import unicodedata

from paralisacao.config import Config

logger = logging.getLogger("paralisacao.mapeamento")

_CODIGOS_MOTIVO_CACHE: dict[str, int] | None = None
_MOTIVOS_JSON: tuple[str, int, dict[str, str], dict[str, int]] | None = None

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

def _motivos_json(config: Config) -> tuple[dict[str, str], dict[str, int]]:
    """Lê motivos.json uma vez por alteração do arquivo."""
    global _MOTIVOS_JSON
    arquivo = config.project_root / "data" / "motivos.json"
    try:
        modificado = arquivo.stat().st_mtime_ns
    except OSError:
        return {}, {}
    caminho = str(arquivo)
    if _MOTIVOS_JSON and _MOTIVOS_JSON[0] == caminho and _MOTIVOS_JSON[1] == modificado:
        return _MOTIVOS_JSON[2], _MOTIVOS_JSON[3]
    try:
        dados = json.loads(arquivo.read_text(encoding="utf-8"))
    except Exception as e:
        logger.error(f"Erro ao ler motivos.json: {e}")
        return {}, {}
    mapeamentos = {
        normalizar(chave): valor
        for chave, valor in dados.get("mapeamentos", {}).items()
    }
    codigos: dict[str, int] = {}
    for nome, codigo in dados.get("codigos", {}).items():
        try:
            codigos[normalizar(nome)] = int(codigo)
        except (TypeError, ValueError):
            continue
    _MOTIVOS_JSON = (caminho, modificado, mapeamentos, codigos)
    return mapeamentos, codigos


def motivo_sistema(motivo: str, config: Config) -> str | None:
    """Retorna o nome do motivo no OpenPort correspondente ao motivo da planilha."""
    if not motivo:
        return None
    mapeamentos, _codigos = _motivos_json(config)
    chave = normalizar(motivo)
    if chave in mapeamentos:
        return mapeamentos[chave]
    return config.motivo_correspondencia.get(chave)

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
                codigos[normalizar(m.group(2))] = int(m.group(1))
    except Exception as e:
        logger.error(f"Erro ao carregar codigos de motivo: {e}")
    return codigos

def codigo_motivo(nome_sistema: str, config: Config) -> int | None:
    """Retorna o codigo numerico do motivo a partir do nome no sistema."""
    global _CODIGOS_MOTIVO_CACHE
    if _CODIGOS_MOTIVO_CACHE is None:
        _CODIGOS_MOTIVO_CACHE = _carregar_codigos_motivo(config)
    chave = normalizar(nome_sistema)
    _mapeamentos, codigos = _motivos_json(config)
    if chave in codigos:
        return codigos[chave]
    return _CODIGOS_MOTIVO_CACHE.get(chave)


def texto_observacao(motivo_resumo: str, nome_sistema: str) -> str:
    """Quando o código é aproximado, a observação guarda o texto do resumo."""
    if normalizar(motivo_resumo) == normalizar(nome_sistema):
        return motivo_resumo
    return f"Resumo: {motivo_resumo}"


def salvar_codigo_motivo(config: Config, motivo_planilha: str, codigo: int) -> None:
    """Grava o código informado uma vez. A viagem seguinte reutiliza motivos.json."""
    arquivo = config.project_root / "data" / "motivos.json"
    dados = {"mapeamentos": {}, "codigos": {}}
    if arquivo.exists():
        dados.update(json.loads(arquivo.read_text(encoding="utf-8")))
    dados.setdefault("mapeamentos", {})
    dados.setdefault("codigos", {})
    chave = normalizar(motivo_planilha)
    dados["mapeamentos"][chave] = chave
    dados["codigos"][chave] = int(codigo)
    global _MOTIVOS_JSON
    arquivo.write_text(json.dumps(dados, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    _MOTIVOS_JSON = None
