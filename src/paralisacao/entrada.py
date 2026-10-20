"""Caminho da planilha escolhido na hora: arquivo ou pasta. Sem arquivo padrão."""
from pathlib import Path

_EXTENSOES = {".xlsx", ".xlsm"}


def deve_abrir_painel(comando: str | None, planilha: str | None, dry_run: bool) -> bool:
    """Duplo clique e `python -m paralisacao` sem arquivo abrem o painel."""
    return comando is None and not (planilha or "").strip() and not dry_run


def resolver_entrada(caminho: str, raiz: Path | None = None) -> Path:
    """Aceita um .xlsx ou uma pasta com um único .xlsx."""
    origem = _localizar(caminho, raiz)
    if origem.is_dir():
        return _unico_xlsx(origem)
    if not origem.is_file():
        raise ValueError(f"Planilha nao encontrada: {origem}")
    if origem.suffix.lower() not in _EXTENSOES:
        raise ValueError(f"O arquivo precisa ser .xlsx: {origem.name}")
    return origem


def _localizar(caminho: str, raiz: Path | None) -> Path:
    origem = Path(caminho).expanduser()
    if origem.is_absolute():
        return origem
    candidatos = [Path.cwd() / origem]
    if raiz is not None:
        candidatos.append(raiz / origem)
    for candidato in candidatos:
        if candidato.exists():
            return candidato
    return candidatos[0]


def _unico_xlsx(pasta: Path) -> Path:
    arquivos = sorted(
        item
        for item in pasta.iterdir()
        if item.is_file()
        and item.suffix.lower() in _EXTENSOES
        and not item.name.startswith("~$")
    )
    if not arquivos:
        raise ValueError(f"Nenhuma planilha .xlsx em {pasta}")
    if len(arquivos) > 1:
        nomes = ", ".join(item.name for item in arquivos)
        raise ValueError(f"A pasta tem mais de uma planilha. Escolha o arquivo: {nomes}")
    return arquivos[0]
