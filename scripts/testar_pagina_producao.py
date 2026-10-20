"""Consulta as duas URLs de produção do OpenPort e imprime o resultado."""
import time
import urllib.error
import urllib.request

URLS = (
    "https://openportilheus.codeba.gov.br/openportcodeba/",
    "https://openportilheus.codeba.gov.br/openportcodeba/default.aspx",
)
TIMEOUT_S = 30


def consultar(url: str) -> None:
    inicio = time.perf_counter()
    pedido = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    try:
        with urllib.request.urlopen(pedido, timeout=TIMEOUT_S) as resposta:
            corpo = resposta.read(4096)
            tempo_ms = int((time.perf_counter() - inicio) * 1000)
            print(f"URL {url}")
            print(f"HTTP {resposta.status}")
            print(f"tempo_ms {tempo_ms}")
            print(f"conteudo {'sim' if corpo else 'nao'} bytes {len(corpo)}")
    except urllib.error.HTTPError as erro:
        tempo_ms = int((time.perf_counter() - inicio) * 1000)
        trecho = b""
        try:
            trecho = erro.read(4096)
        except Exception:
            pass
        print(f"URL {url}")
        print(f"HTTP {erro.code}")
        print(f"tempo_ms {tempo_ms}")
        print(f"conteudo {'sim' if trecho else 'nao'} bytes {len(trecho)}")
    except Exception as erro:
        tempo_ms = int((time.perf_counter() - inicio) * 1000)
        print(f"URL {url}")
        print("HTTP nenhum")
        print(f"tempo_ms {tempo_ms}")
        print("conteudo nao bytes 0")
        print(f"erro {type(erro).__name__}: {erro}")


def main() -> None:
    for url in URLS:
        consultar(url)
        print("---")


if __name__ == "__main__":
    main()
