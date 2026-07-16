"""Hierarquia de exceções do RPA."""

class RPAError(Exception):
    """Erro base de toda a automação."""

class LoginError(RPAError):
    """Falha no login do OpenPort."""

class CapaNaoEncontradaError(RPAError):
    """Capa não existe no OpenPort e não pôde ser criada."""

class CriacaoCapaError(RPAError):
    """Falha ao criar uma nova capa."""

class ParalisacaoError(RPAError):
    """Falha ao registrar uma paralisação."""

class GravacaoError(ParalisacaoError):
    """O sistema não confirmou gravação com sucesso."""

class LookupError(ParalisacaoError):
    """Motivo não encontrado no lookup do sistema."""

class PlanilhaError(RPAError):
    """Erro de leitura ou validação da planilha."""
