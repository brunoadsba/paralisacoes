"""Painel local em 127.0.0.1:8080."""
import html
from pathlib import Path

from flask import Flask, jsonify, redirect, render_template_string, request

from paralisacao.config import Config
from paralisacao.ui.ambiente import normalizar_modo
from paralisacao.ui.credenciais import carregar, esquecer, salvar
from paralisacao.ui.estado import LOCK, STATE
from paralisacao.ui.execucao import iniciar, linhas_html
from paralisacao.ui.layout import BASE, etapas_html
from paralisacao.ui.paginas import form_login, painel_execucao, painel_resultado
from paralisacao.ui.rotas_preparo import registrar

RAIZ_UI = Path(__file__).resolve().parent
app = Flask(__name__, static_folder=str(RAIZ_UI / "static"))
registrar(app, lambda body, etapa: _pagina(body, etapa), lambda: Config.from_env())


def _pagina(body: str, etapa: int | None) -> str:
    with LOCK:
        modo = STATE["modo"]
        usuario = STATE["usuario"]
    rotulo = {"qas": "Ambiente de testes (QAS)", "producao": "Produção",
              "prod_simulado": "Produção simulada · QAS"}.get(modo, "QAS")
    classe = "prod" if modo == "producao" else "qas"
    usuario_txt = usuario if usuario else "sem acesso"
    return render_template_string(
        BASE, body=body, etapas=etapas_html(etapa),
        env_cls=classe, env_label=rotulo, user=usuario_txt,
    )


@app.get("/")
def raiz():
    return redirect("/login")


@app.route("/login", methods=["GET", "POST"])
def login():
    cred = carregar()
    with LOCK:
        modo = STATE["modo"]
    if request.method == "POST" and request.form.get("acao") == "esquecer":
        esquecer()
        with LOCK:
            STATE["usuario"] = ""
            STATE["senha"] = ""
        return redirect("/login")
    if request.method == "POST":
        usuario = request.form.get("usuario", "").strip()
        senha = request.form.get("senha", "")
        if not senha and cred.get("usuario") == usuario:
            senha = cred.get("senha", "")
        if not usuario or not senha:
            return _pagina(form_login(cred, modo), 1)
        if request.form.get("lembrar"):
            salvar(usuario, senha)
        with LOCK:
            STATE["usuario"] = usuario
            STATE["senha"] = senha
            STATE["modo"] = normalizar_modo(request.form.get("modo"))
        return redirect("/resumo")
    return _pagina(form_login(cred, modo), 1)


@app.route("/execucao", methods=["GET"])
def execucao():
    with LOCK:
        uma_ok = STATE["uma_ok"]
        pronto = bool(STATE["planilha"] and STATE["senha"])
    return _pagina(painel_execucao(linhas_html(), uma_ok, pronto), 4)


@app.post("/executar")
def executar_rota():
    aviso = iniciar(request.form.get("escopo", "uma"))
    if aviso:
        return _pagina(f'<p class="aviso-err">{html.escape(aviso)}</p>' + painel_execucao(linhas_html(), False, True), 4)
    return redirect("/execucao")


@app.get("/api/status")
def api_status():
    desde = int(request.args.get("desde", "0") or 0)
    with LOCK:
        novas = list(STATE["log"][desde:])
        total = len(STATE["log"])
        tot = STATE["tot"] or 1
        running = STATE["running"]
        proc = STATE["proc"]
        phase = STATE["phase"]
        lote = STATE["uma_ok"]
    if proc and not running:
        pct = int(100 * proc / tot)
    elif running:
        pct = 10
    else:
        pct = 0
    return jsonify({
        "running": running,
        "phase": phase,
        "pct": pct,
        "log": [{"t": linha} for linha in novas],
        "log_total": total,
        "linhas_html": linhas_html(),
        "lote_liberado": lote,
    })


@app.get("/resultado")
def resultado():
    with LOCK:
        texto = STATE["relatorio"]
    return _pagina(painel_resultado(texto), 5)


def main() -> int:
    app.run(host="127.0.0.1", port=8080, threaded=True, use_reloader=False)
    return 0
