"""Ambiente OpenPort: QAS, produção ou produção simulada no QAS."""

MODO_QAS = "qas"
MODO_PRODUCAO = "producao"
MODO_PROD_SIMULADO = "prod_simulado"
MODOS_VALIDOS = (MODO_QAS, MODO_PRODUCAO, MODO_PROD_SIMULADO)

PERFIS = {
    MODO_QAS: {
        "titulo": "Testes (QAS)",
        "resumo": "OpenPort de teste. Use para a primeira paralisação antes do lote.",
        "url": "https://ilheus.codeba.gov.br/qas/openportcodeba/default.aspx",
    },
    MODO_PRODUCAO: {
        "titulo": "Produção",
        "resumo": "OpenPort real do porto de Ilhéus.",
        "url": "https://openportilheus.codeba.gov.br/openportcodeba/default.aspx",
    },
    MODO_PROD_SIMULADO: {
        "titulo": "Produção (simulado no QAS)",
        "resumo": "Mesmas regras da produção, conectado ao QAS.",
        "url": "https://ilheus.codeba.gov.br/qas/openportcodeba/default.aspx",
    },
}


def normalizar_modo(modo: str | None) -> str:
    escolhido = (modo or "").strip().lower()
    if escolhido in PERFIS:
        return escolhido
    return MODO_QAS


def url_operacao(modo: str | None) -> str:
    """Pasta do OpenPort, sem default.aspx, para a criação de capa concatenar cadastro.aspx."""
    bruto = PERFIS[normalizar_modo(modo)]["url"]
    if bruto.lower().endswith("default.aspx"):
        bruto = bruto[: -len("default.aspx")]
    if not bruto.endswith("/"):
        bruto += "/"
    return bruto
