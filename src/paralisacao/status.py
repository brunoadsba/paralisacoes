import json
import logging
import re
from datetime import datetime
from pathlib import Path

from playwright.sync_api import Page

logger = logging.getLogger("paralisacao.status")

_DATA_HORA = re.compile(r"\d{2}/\d{2}/\d{4} \d{2}:\d{2}")

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
        if para.get("inicio") == hi:
            para["status"] = "ok"
            para["codigo"] = codigo
            return
    status_capa["paralisacoes"].append({
        "inicio": hi,
        "fim": _normalizar_horario(p.fim),
        "motivo_planilha": p.motivo,
        "codigo": codigo,
        "status": "ok"
    })

def _marcar_erro_no_status(status_capa: dict, p, codigo: int) -> None:
    """Registra a paralisação que não gravou, para a capa não parecer completa."""
    hi = _normalizar_horario(p.inicio)
    for para in status_capa["paralisacoes"]:
        if para.get("inicio") == hi:
            para["status"] = "erro"
            para["codigo"] = codigo
            return
    status_capa["paralisacoes"].append({
        "inicio": hi,
        "fim": _normalizar_horario(p.fim),
        "motivo_planilha": p.motivo,
        "codigo": codigo,
        "status": "erro"
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

def paralisacao_ja_existe(grid: list[list[str]], inicio: str) -> str | None:
    """Devolve a linha da grade que começa em `inicio` ('DD/MM/AAAA HH:MM'), seja qual for o motivo.

    Lançamentos manuais podem usar outro código; o início é o que identifica a paralisação na capa.
    """
    for row in grid[1:]:
        horarios = [achado.group(0) for celula in row if (achado := _DATA_HORA.search(celula))]
        if horarios and horarios[0] == inicio:
            return " | ".join(celula for celula in row if celula)
    return None
