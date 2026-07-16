import logging
import time
from collections.abc import Callable
from functools import wraps
from typing import TypeVar

T = TypeVar("T")
logger = logging.getLogger("paralisacao.retry")

def com_retry(
    tentativas: int = 3,
    backoff_base: float = 2.0,
    excecoes: tuple = (Exception,),
) -> Callable:
    """Decorator para realizar retry de funções com backoff exponencial em caso de exceções."""
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args, **kwargs) -> T:
            for tentativa in range(1, tentativas + 1):
                try:
                    return func(*args, **kwargs)
                except excecoes as e:
                    if tentativa == tentativas:
                        logger.error(f"Função {func.__name__} falhou definitivamente após {tentativas} tentativas.")
                        raise
                    espera = backoff_base ** tentativa
                    logger.warning(
                        f"Função {func.__name__} falhou na tentativa {tentativa}/{tentativas} ({e}). "
                        f"Realizando nova tentativa em {espera:.1f}s..."
                    )
                    time.sleep(espera)
            raise RuntimeError("Unreachable")
        return wrapper
    return decorator
