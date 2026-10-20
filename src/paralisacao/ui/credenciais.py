"""Credenciais do OpenPort no cofre já usado pela Automação SEV."""

SERVICO = "rpa-sev-intermaritima"
USUARIO_CHAVE = "ultimo_usuario"
LEMBRAR_CHAVE = "lembrar_ativo"


def _keyring():
    import keyring

    return keyring


def carregar() -> dict:
    vazio = {"usuario": "", "senha": "", "lembrar": False}
    try:
        keyring = _keyring()
        lembrar = (keyring.get_password(SERVICO, LEMBRAR_CHAVE) or "") == "1"
        usuario = keyring.get_password(SERVICO, USUARIO_CHAVE) or ""
        if lembrar and usuario:
            senha = keyring.get_password(SERVICO, usuario) or ""
            if senha:
                return {"usuario": usuario, "senha": senha, "lembrar": True}
    except Exception:
        return vazio
    return vazio


def salvar(usuario: str, senha: str) -> None:
    keyring = _keyring()
    keyring.set_password(SERVICO, USUARIO_CHAVE, usuario)
    keyring.set_password(SERVICO, usuario, senha)
    keyring.set_password(SERVICO, LEMBRAR_CHAVE, "1")


def esquecer() -> None:
    try:
        keyring = _keyring()
        usuario = keyring.get_password(SERVICO, USUARIO_CHAVE)
        if usuario:
            try:
                keyring.delete_password(SERVICO, usuario)
            except Exception:
                pass
        for chave in (USUARIO_CHAVE, LEMBRAR_CHAVE):
            try:
                keyring.delete_password(SERVICO, chave)
            except Exception:
                pass
    except Exception:
        return
