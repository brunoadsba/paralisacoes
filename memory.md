# Memória — RPA de paralisações OpenPort

Atualizado em 20/10/2026. Branch de trabalho: `feat/preparar-resumo` (ainda sem commit desta etapa). Não gravar senha neste arquivo.

## O que o sistema faz

Lê o resumo de embarque da Intermarítima, monta a planilha padrão do OpenPort e registra as paralisações no CODEBA. O operador da capa é sempre **30002** (Intermarítima). A agência da viagem TI SUNRISE é Marinav. O produto é níquel.

## Decisões fechadas

- A Intermarítima entrega navio, produto, agência, data do bloco, início, fim e o texto do motivo. O usuário entrega a programação da viagem e o código numérico dos motivos que ainda não existem em `data/motivos.json`.
- A data da capa é a data impressa no bloco `Paralisações - DD/MM/AA`, não a manhã seguinte do calendário.
- O turno sai do horário de início. A função `_calcular_data_hora` só avança o dia quando a hora é menor que o início do período. Por isso 00:45 na capa 16/10 turno 19:00/01:00 continua nesse bloco; 01:00 fica na capa 01:00/07:00 da mesma data do bloco.
- Não inventar código de motivo. Parecidos não são o mesmo motivo:
  - TROCA DE TURNO não é 434 (TROCA TURNO - AGUARD. TPA) nem 435 (TROCA TURNO - AGUARD.OPERADORA).
  - MANUTENÇÃO SPREADER não é 458 (MANUTENÇÃO CODEBA).
  - DRAFT SURVEY não está na lista extraída em 13/07/2026 (`data/tipo-paralizacoes.md`).
- DDS mapeia para CONVENIENCIA DO USUARIO, código 34. CHUVA é código 5.
- O lote só libera depois da primeira paralisação gravada com sucesso (`STATE["uma_ok"]`).
- A interface reaproveita a casca visual da Automação SEV (`rpa-intermaritima`). Não copiar NF-e, PR, 9401 nem o CNPJ solicitante da SEV.

## Viagem de teste — TI SUNRISE

Arquivo de origem: `C:\Users\danyp\Downloads\TI SUNRISE - Resumo de embarque.xlsx`.

Aba certa: **Resumo**. Motivo na coluna cujo cabeçalho contém "Motivo". A coluna AH "Tipo Ocorrência" é catálogo lateral e não entra na leitura. Agência, navio e produto são lidos na célula abaixo do rótulo, não na célula ao lado.

Doze paralisações em cinco capas (16/10 e 17/10/2026). Motivos do resumo: DDS, CHUVA, TROCA DE TURNO, DRAFT SURVEY, MANUTENÇÃO SPREADER.

Programação digitada na tela e ainda não necessariamente gravada: **1772**. Os três motivos sem código continuam pendentes. A primeira linha (DDS 13:00–13:15, capa 16/10, turno 13:00/19:00) já tem código e pode ser a prova de uma gravação no QAS.

A gravação ao vivo no QAS ainda não foi feita.

## URLs

A base usada pelo robô não leva `default.aspx`, porque `capa.py` concatena `cadastro.aspx`. `url_operacao` em `src/paralisacao/ui/ambiente.py` remove esse sufixo.

- QAS e produção simulada: `https://ilheus.codeba.gov.br/qas/openportcodeba/`
- Produção: `https://openportilheus.codeba.gov.br/openportcodeba/`

## Painel

`python -m paralisacao painel` sobe Flask em `127.0.0.1:8080` com `use_reloader=False`. Mudança de Python exige reinício. Reiniciar zera o estado em memória: login, resumo carregado e programação digitada e não enviada.

Etapas: Acesso, Resumo, Pendências, Execução, Resultado. O upload vai para `data/operacoes/resumo_recebido.xlsx` (pasta no `.gitignore`). A planilha padrão só é gravada quando não há pendência.

Cada campo de Pendências tem um botão **i** (`ajuda-flag`) explicando o que preencher. O código informado é salvo em `data/motivos.json` (`mapeamentos` e `codigos`) e não é pedido de novo.

Marca visual, a partir do GeraPOP:

- Logo colorido `src/paralisacao/ui/static/logo-codeba.png` no tema claro.
- Logo branco `logo-codeba-branca.png` no tema escuro.
- Claro: fundo `#F4F7FB`, texto `#0B1F3A`, botão `#1F4E79`.
- Escuro: fundo `#0A1220`, superfície `#122033`, botão `#5BA3D9`.
- Faixa do cabeçalho: `#001956`, `#0050D0`, `#33A9A6`.

Credenciais ficam no keyring do serviço `rpa-sev-intermaritima`. Nunca imprimir a senha.

## Playwright e Chrome

A faixa "sinalizador de linha de comando não suportado: `--disable-blink-features=AutomationControlled`" é aviso do Chrome. O Playwright liga essa opção ao abrir o navegador. Fechar a faixa não interrompe a gravação.

O Playwright está instalado no Python 3.12. O `python` padrão desta máquina é o Anaconda 3.13, que sobe o painel, mas a execução do navegador falha até o Playwright existir nesse interpretador. Não repetir `pip install --target` da 3.12 para a Anaconda: o comando também alterou pacotes da 3.12.

Flags da CLI colocadas antes do subcomando `executar` são ignoradas. O dry-run válido é `python -m paralisacao executar --dry-run`.

## Leitura do resumo e da planilha

- `src/paralisacao/resumo.py` escolhe a aba pelo título `Paralisações` com data. A primeira aba BANCO DE DADOS contém "PARALISAÇÕES DA OPERAÇÃO" e não serve.
- `src/paralisacao/preparar.py` monta as linhas padrão, calcula pendências e grava o xlsx. `executar_preparar` sai com código 2 se ainda houver pendência.
- O leitor genérico da planilha padrão usa a programação e a tabela. A célula do operador no cabeçalho é ignorada.

## Confiabilidade ainda aberta

- `executar` em `main.py` pode terminar com código 0 mesmo após falha fatal.
- Status "completa" pode mentir se a falha não for anexada.
- A deduplicação na grade é por substring.
- `OPERADOR` do ambiente é ignorado: o valor fixo é 30002.
- Datas nativas do Excel na planilha genérica não saem como DD/MM/AAAA. O parser do resumo trata `datetime.time`.
- `HEADLESS` perde para `PRIMEIRO_PLANO`.
