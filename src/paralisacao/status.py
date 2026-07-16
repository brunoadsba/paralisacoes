import json
import logging
from datetime import datetime
from pathlib import Path

from playwright.sync_api import Page

from paralisacao import mapeamento
from paralisacao.config import Config

logger = logging.getLogger("paralisacao.status")

def _normalizar_horario(h: str) -> str:
    """Normaliza o formato de horário removendo segundos se for ':00'."""
    h = h.strip()
    if h.count(":") == 2 and h.endswith(":00"):
        h = h[:-3]
    return h

def carregar_status(status_file: Path) -> dict:
    """Carrega o status do arquivo JSON local ou retorna um dicionário vazio estruturado."""
    if status_file.exists():
        try:
            return json.loads(status_file.read_text(encoding="utf-8"))
        except Exception as e:
            logger.error(f"Erro ao carregar arquivo de status {status_file}: {e}")
    return {"ultima_execucao": "", "planilha": "", "capas": {}}

def salvar_status(status: dict, status_file: Path) -> None:
    """Grava o status atualizado no arquivo JSON local."""
    try:
        status["ultima_execucao"] = datetime.now().isoformat()
        status_file.parent.mkdir(parents=True, exist_ok=True)
        status_file.write_text(json.dumps(status, indent=2, ensure_ascii=False), encoding="utf-8")
    except Exception as e:
        logger.error(f"Erro ao salvar arquivo de status: {e}")

def _status_capa(status: dict, capa_registro: str) -> dict:
    """Busca ou inicializa a entrada da capa correspondente no status."""
    if capa_registro not in status["capas"]:
        status["capas"][capa_registro] = {
            "codRegistro": 0,
            "navio": "",
            "data": "",
            "periodo": "",
            "status": "pendente",
            "paralisacoes": []
        }
    return status["capas"][capa_registro]

def _paralisacao_ok_no_status(status_capa: dict, p, codigo: int) -> bool:
    """Verifica se a paralisação específica já foi registrada de acordo com o status local."""
    hi = _normalizar_horario(p.inicio)
    for para in status_capa["paralisacoes"]:
        if para.get("codigo") == codigo and para.get("inicio") == hi and para.get("status") == "ok":
            return True
    return False

def _marcar_ok_no_status(status_capa: dict, p, codigo: int) -> None:
    """Marca uma paralisação como sucesso no status da capa."""
    hi = _normalizar_horario(p.inicio)
    for para in status_capa["paralisacoes"]:
        if para.get("codigo") == codigo and para.get("inicio") == hi:
            para["status"] = "ok"
            return
    status_capa["paralisacoes"].append({
        "inicio": hi,
        "fim": _normalizar_horario(p.fim),
        "motivo_planilha": p.motivo,
        "codigo": codigo,
        "status": "ok"
    })

def _atualizar_status_capa(sc: dict) -> None:
    """Atualiza o status geral da capa (parcial ou completa) baseado em suas paralisações."""
    if not sc["paralisacoes"]:
        return
    todos_ok = all(para["status"] == "ok" for para in sc["paralisacoes"])
    sc["status"] = "completa" if todos_ok else "parcial"

def ler_grid_paralisacoes(page: Page) -> list[list[str]]:
    """Lê a tabela de paralisações na tela ativa do OpenPort e retorna as linhas."""
    result = page.evaluate("""
        () => {
            const tables = document.querySelectorAll('table[id="TQuery"]');
            for (const t of tables) {
                const headerRow = t.rows[0];
                if (!headerRow) continue;
                const headerText = headerRow.innerText.toLowerCase();
                if (headerText.includes('inicio') || headerText.includes('fim') || headerText.includes('motivo')) {
                    const rows = [];
                    for (let i = 0; i < t.rows.length; i++) {
                        const cells = [];
                        for (let j = 0; j < t.rows[i].cells.length; j++) {
                            cells.push(t.rows[i].cells[j].innerText.trim());
                        }
                        rows.push(cells);
                    }
                    return rows;
                }
            }
            return [];
        }
    """)
    return result if result else []

def paralisacao_ja_existe(grid: list[list[str]], p, codigo: int, config: Config) -> bool:
    """Verifica se a paralisação já existe na grid do OpenPort."""
    if not grid:
        return False
    hi = _normalizar_horario(p.inicio)
    nome_sistema = mapeamento.motivo_sistema(p.motivo, config) or ""
    for row in grid[1:]:  # skip header
        row_text = " ".join(row).upper()
        if hi in row_text and nome_sistema.upper() in row_text:
            return True
    return False
