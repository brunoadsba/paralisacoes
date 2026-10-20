"""Estado do painel em memória. Vale só para o processo local."""
import threading

STATE = {
    "usuario": "",
    "senha": "",
    "modo": "producao",
    "resumo": None,
    "linhas": [],
    "programacao": "",
    "planilha": "",
    "operador": "30002",
    "log": [],
    "phase": "Aguardando início",
    "running": False,
    "uma_ok": False,
    "proc": 0,
    "tot": 0,
    "situacao": {},
    "relatorio": "",
}
LOCK = threading.Lock()
