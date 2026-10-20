"""Casca visual herdada da Automação SEV."""

ETAPAS = ["Acesso", "Resumo", "Pendências", "Execução", "Resultado"]

BASE = """<!doctype html><html lang="pt-BR"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Paralisações | CODEBA</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Source+Sans+3:wght@400;600;700&display=swap" rel="stylesheet">
<link href="/static/vendor/bootstrap.min.css" rel="stylesheet">
<link href="/static/app.css" rel="stylesheet">
<link rel="icon" type="image/png" href="/static/logo-codeba.png">
<script>
(function(){
  var d = document.documentElement;
  var t = localStorage.getItem("par_theme");
  if (!t) t = (window.matchMedia && matchMedia("(prefers-color-scheme: dark)").matches) ? "dark" : "light";
  d.setAttribute("data-theme", t);
  window.toggleTheme = function(){
    var dark = d.getAttribute("data-theme") === "dark";
    d.setAttribute("data-theme", dark ? "light" : "dark");
    localStorage.setItem("par_theme", dark ? "light" : "dark");
  };
})();
</script>
</head><body>
<header>
 <nav class="navbar nv" aria-label="Navegação principal">
  <div class="container-fluid px-3 px-md-4">
   <span class="navbar-brand d-flex align-items-center gap-3 mb-0">
    <span class="marca">
     <img class="marca-cor" src="/static/logo-codeba.png" alt="CODEBA">
     <img class="marca-branca" src="/static/logo-codeba-branca.png" alt="CODEBA">
    </span>
    <span class="d-flex flex-column nv-brand-txt">
     <span class="fw-bold nv-brand-title">Paralisações</span>
     <span class="small nv-brand-sub d-none d-sm-block">Porto de Ilhéus</span>
    </span>
   </span>
   <span class="ms-auto d-flex align-items-center gap-2">
    <button id="btnTheme" type="button" class="nv-toggle" onclick="toggleTheme()" title="Alternar claro/escuro">Tema</button>
   </span>
  </div>
 </nav>
 <div class="nv-bar small">
  <div class="container-fluid px-3 px-md-4 d-flex flex-wrap align-items-center gap-2 py-2">
   <span class="badge-env {{ env_cls }}">{{ env_label }}</span>
   <span class="nv-status d-none d-lg-inline">Execução supervisionada</span>
   <span class="nv-user ms-auto">{{ user }}</span>
  </div>
 </div>
</header>
<main class="container py-4"><div class="pagina">{{ etapas|safe }}{{ body|safe }}</div></main>
</body></html>"""


def etapas_html(atual: int | None) -> str:
    if not atual:
        return ""
    itens = []
    for indice, nome in enumerate(ETAPAS, 1):
        if indice < atual:
            classe = "feita"
        elif indice == atual:
            classe = "atual"
        else:
            classe = ""
        itens.append(f'<li class="{classe}"><span class="n">{indice}</span>{nome}</li>')
    return '<ol class="etapas" aria-label="Etapas">' + "".join(itens) + "</ol>"
