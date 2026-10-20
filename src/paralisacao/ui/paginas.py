"""Telas do painel. A senha salva nunca entra no HTML."""
import html


def form_login(cred: dict, modo: str) -> str:
    from paralisacao.ui.ambiente import MODOS_VALIDOS, PERFIS

    usuario = html.escape(cred.get("usuario", ""))
    lem = " checked" if cred.get("lembrar") else ""
    tem_salva = bool(cred.get("senha"))
    placeholder = ' placeholder="Senha salva neste computador"' if tem_salva else ""
    obrigatorio = "" if tem_salva else " required"
    ajuda = (
        '<p class="small mutedx mb-3">Deixe em branco para usar a senha salva.</p>'
        if tem_salva else ""
    )
    cards = []
    for mid in MODOS_VALIDOS:
        perfil = PERFIS[mid]
        chk = " checked" if mid == modo else ""
        cards.append(
            f'<label class="env-card">'
            f'<input type="radio" name="modo" value="{mid}"{chk} required>'
            f'<div class="env-card-title">{html.escape(perfil["titulo"])}</div>'
            f'<p class="env-card-desc">{html.escape(perfil["resumo"])}</p>'
            f'</label>'
        )
    return f"""<div class="mx-auto py-4 py-md-5" style="max-width:520px">
  <div class="cardx p-4 p-md-5 text-center">
    <span class="marca marca-login">
      <img class="marca-cor" src="/static/logo-codeba.png" alt="CODEBA">
      <img class="marca-branca" src="/static/logo-codeba-branca.png" alt="CODEBA">
    </span>
    <h4 class="fw-bold mt-3 mb-1 titulo-pagina">Paralisações</h4>
    <p class="small mutedx mb-4">Porto de Ilhéus</p>
    <form method="post" class="text-start">
      <p class="rotulo mb-2">Onde vai operar?</p>
      <div class="env-pick" role="radiogroup" aria-label="Ambiente de operação">
        {"".join(cards)}
      </div>
      <label class="form-label small mutedx mb-1" for="usr">Usuário</label>
      <input id="usr" class="inputx form-control form-control-lg mb-3" name="usuario" value="{usuario}"
             autocomplete="username" required>
      <label class="form-label small mutedx mb-1" for="pwd">Senha</label>
      <input id="pwd" type="password" class="inputx form-control form-control-lg mb-2" name="senha"
             autocomplete="current-password"{placeholder}{obrigatorio}>
      {ajuda}
      <div class="form-check mb-4">
        <input class="form-check-input" type="checkbox" name="lembrar" id="lembrar"{lem}>
        <label class="form-check-label small" for="lembrar">Lembrar credenciais neste computador</label>
      </div>
      <button class="btn btn-brand btn-lg w-100 mb-2" type="submit" name="acao" value="entrar">Entrar</button>
      <button class="btn btn-link btn-sm w-100" type="submit" name="acao" value="esquecer">Esquecer credenciais salvas</button>
    </form>
  </div>
</div>"""


def form_resumo(aviso: str = "") -> str:
    bloco = f'<p class="aviso-err mb-3">{html.escape(aviso)}</p>' if aviso else ""
    return f"""<div class="py-2" style="max-width:640px">
  <h1 class="titulo-pagina">Planilha</h1>
  <p class="mutedx mb-3">Escolha o arquivo .xlsx ou a pasta em que ele está. O programa não procura um caminho fixo.</p>
  {bloco}
  <form method="post" enctype="multipart/form-data" class="cardx p-4">
    <label class="form-label" for="resumo">Arquivo</label>
    <input id="resumo" class="form-control mb-3" type="file" name="resumo" accept=".xlsx,.xlsm">
    <label class="form-label" for="pasta">Pasta</label>
    <input id="pasta" class="form-control mb-3" type="file" name="pasta" webkitdirectory directory multiple>
    <button class="btn btn-brand" type="submit">Ler planilha</button>
  </form>
</div>"""


def painel_resumo(navio: str, agencia: str, produto: str, capas: int, total: int, linhas_html: str) -> str:
    return f"""<div class="py-2">
  <h1 class="titulo-pagina">{html.escape(navio)}</h1>
  <p class="mb-3">{html.escape(agencia)} · {html.escape(produto)} · {capas} capas · {total} paralisações</p>
  <div class="cardx mb-3"><table class="tbl"><thead><tr>
    <th>Capa</th><th>Data</th><th>Turno</th><th>Horário</th><th>Motivo</th><th>No OpenPort</th>
  </tr></thead><tbody>{linhas_html}</tbody></table></div>
  <a class="btn btn-brand" href="/pendencias">Continuar</a>
</div>"""


def _flag(identificador: str, texto: str) -> tuple[str, str]:
    botao = (
        f'<button type="button" class="ajuda-flag" aria-expanded="false" '
        f'aria-controls="{identificador}" title="O que é este campo">i</button>'
    )
    texto_html = f'<p id="{identificador}" class="ajuda-texto" hidden>{html.escape(texto)}</p>'
    return botao, texto_html


def form_pendencias(programacao: str, motivos: list[str], aviso: str = "") -> str:
    bloco = f'<p class="aviso-err mb-3">{html.escape(aviso)}</p>' if aviso else ""
    ajuda_prog = (
        "Número da viagem no OpenPort, o mesmo usado na busca da capa na tela 7001. "
        "A Intermarítima não envia esse dado no resumo. O operador permanece 30002, "
        "código da Intermarítima no sistema."
    )
    botao_prog, texto_prog = _flag("ajuda-prog", ajuda_prog)
    campos = [
        '<div class="rotulo-linha">'
        '<label class="form-label" for="prog">Programação do navio</label>'
        + botao_prog
        + "</div>"
        + texto_prog,
        f'<input id="prog" class="inputx form-control form-control-lg mb-3" name="programacao" '
        f'value="{html.escape(programacao)}" required>',
    ]
    for indice, motivo in enumerate(motivos):
        texto = (
            "Este texto não está na lista do OpenPort. Digite o código mais próximo. "
            "O texto original do resumo vai para o campo observação."
        )
        botao, explicacao = _flag(f"ajuda-cod{indice}", texto)
        campos.append(
            '<div class="rotulo-linha">'
            f'<label class="form-label" for="cod{indice}">{html.escape(motivo)}</label>'
            + botao
            + "</div>"
            + explicacao
            + f'<input type="hidden" name="motivo" value="{html.escape(motivo)}">'
            f'<input id="cod{indice}" class="inputx form-control mb-3" name="codigo" '
            f'inputmode="numeric" required>'
        )
    lista = "".join(campos)
    return f"""<div class="py-2" style="max-width:640px">
  <h1 class="titulo-pagina">Pendências</h1>
  <p class="mutedx mb-3">O botão i ao lado de cada campo explica o que preencher.</p>
  {bloco}
  <form method="post" class="cardx p-4">
    {lista}
    <button class="btn btn-brand" type="submit">Gravar planilha padrão</button>
  </form>
</div>
<script>
document.querySelectorAll(".ajuda-flag").forEach(function (botao) {{
  botao.addEventListener("click", function () {{
    var alvo = document.getElementById(botao.getAttribute("aria-controls"));
    var aberto = botao.getAttribute("aria-expanded") === "true";
    botao.setAttribute("aria-expanded", aberto ? "false" : "true");
    if (alvo) alvo.hidden = aberto;
  }});
}});
</script>"""


def painel_execucao(linhas_html: str, uma_ok: bool, pronto: bool) -> str:
    lote_disabled = "" if uma_ok else " disabled"
    aviso = "" if uma_ok else '<p class="mutedx mb-3">O lote libera depois que a primeira paralisação gravar no OpenPort.</p>'
    pronto_aviso = "" if pronto else '<p class="aviso-err mb-3">Preencha as pendências antes de executar.</p>'
    return f"""<div class="py-2">
  <h1 id="ttl" class="titulo-pagina">Execução</h1>
  <div id="phaseTxt" class="small mutedx mb-2">Aguardando início</div>
  {aviso}{pronto_aviso}
  <div class="progress mb-3 sev-progress">
    <div id="bar" class="progress-bar" role="progressbar" style="width:0%"></div>
  </div>
  <div class="cardx mb-3"><table class="tbl"><thead><tr>
    <th>Capa</th><th>Horário</th><th>Motivo</th><th>Situação</th>
  </tr></thead><tbody id="tbLinhas">{linhas_html}</tbody></table></div>
  <details id="logBox" class="mb-3"><summary>Detalhes técnicos (log)</summary>
    <div id="log" class="log-console p-3 mt-2"></div>
  </details>
  <form method="post" action="/executar" class="d-flex gap-2 flex-wrap">
    <button class="btn btn-brand" name="escopo" value="uma" type="submit" {"disabled" if not pronto else ""}>Gravar a primeira</button>
    <button class="btn btn-ghost" name="escopo" value="lote" type="submit"{lote_disabled}>Gravar o lote</button>
    <a id="btnResult" class="btn btn-ghost" href="/resultado">Ver resultado</a>
  </form>
</div>
<script src="/static/painel.js"></script>"""


def painel_resultado(texto: str) -> str:
    corpo = html.escape(texto) if texto else "Nenhuma rodada concluída ainda."
    return f"""<div class="py-2">
  <h1 class="titulo-pagina">Resultado</h1>
  <pre class="cardx p-3" style="white-space:pre-wrap">{corpo}</pre>
</div>"""
