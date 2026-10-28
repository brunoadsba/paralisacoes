# Memória — RPA de paralisações OpenPort

Atualizado em 20/10/2026. Branch de trabalho: `fix/planilha-escolhida`. Não gravar senha neste arquivo.

## Quem pede

O usuário se chama Bruno e prefere ser chamado de Liara.

## Onde está o projeto

RPA de paralisações em `c:\Users\danyp\Downloads\paralisacoes`. Módulo `src/paralisacao`, com `pyproject.toml` e `requirements.txt`. Painel em `http://127.0.0.1:8080`.

## O que o sistema faz

Lê o resumo de embarque da Intermarítima, monta a planilha padrão do OpenPort e registra as paralisações no CODEBA. O operador da capa é sempre **30002** (Intermarítima). A agência da viagem TI SUNRISE é Marinav. O produto é níquel.

## Decisões fechadas

- A Intermarítima entrega navio, produto, agência, data do bloco, início, fim e o texto do motivo. O usuário entrega a programação da viagem e o código numérico dos motivos que ainda não existem em `data/motivos.json`.
- O bloco `Paralisações - DD/MM/AA` do resumo vai de 07h a 07h. A capa usa a data do bloco, exceto no turno 01:00/07:00, que vai para o dia seguinte (`data_da_capa` em `preparar.py`). Referência validada no lançamento manual do TI SUNRISE: capa 17/10, turno 1:00-7:00, `codRegistro` 75656, com as paralisações das 01:00, 04:45 e 06:45 datadas em 17/10.
- Capa 1:00-7:00 com a data do bloco cai antes da estadia (alerta 7052010). Horário depois das 01:00 na capa 19:00-1:00 é recusado (alerta 40030). Uma recusa com código numérico não é tentada de novo.
- `_calcular_data_hora` avança o dia quando a hora é menor que o início do período: 00:45 na capa 16/10 turno 19:00/01:00 vira 17/10 00:45; 01:00 na capa 17/10 turno 01:00/07:00 fica 17/10 01:00.
- Duplicidade: a paralisação é considerada lançada quando a grade da capa já tem uma linha que começa na mesma data e hora, seja qual for o motivo (lançamento manual pode usar outro código). O `status.json` é indexado pelo `codRegistro`.
- A busca da 7001 trata a data como "a partir de". `buscar_capa` só abre a linha cuja coluna Data é igual à data da capa.
- Não inventar um código fora da lista oficial. Se o texto do resumo não existir nela, usar o item mais próximo e gravar o texto original na observação (`Resumo: ...`).
  - TROCA DE TURNO → 435 TROCA TURNO - AGUARD.OPERADORA. A Intermarítima é a operadora.
  - DRAFT SURVEY → 460 VISTORIA. 299 seria espera do arqueador, não a vistoria em si.
  - MANUTENÇÃO SPREADER → 453 INTERDIÇÃO DO EQUIPAMENTO. 458 é manutenção da CODEBA.
- DDS mapeia para TROCA TURNO - AGUARD. TPA, código 434, e a observação guarda `Resumo: DDS`. CHUVA é código 5. DESCANSO continua em CONVENIENCIA DO USUARIO, código 34.
- O lote só libera depois da primeira paralisação gravada com sucesso (`STATE["uma_ok"]`).
- A interface reaproveita a casca visual da Automação SEV (`rpa-intermaritima`). Não copiar NF-e, PR, 9401 nem o CNPJ solicitante da SEV.

## Automação SEV (referência, não é o produto a empacotar)

Repositório clonado em `c:\Users\danyp\Downloads\rpa-intermaritima` (`https://github.com/brunoadsba/rpa-intermaritima.git`, branch `main`, v1.1.0). Stack: Flask, Playwright, openpyxl, PyYAML, keyring, cryptography, Pillow e pytest. O executável sai pelo PyInstaller em `build.bat` e `build_producao.bat`. A senha fica no cofre do Windows, serviço `rpa-sev-intermaritima`. OpenPort de teste: `https://ilheus.codeba.gov.br/qas/openportcodeba/default.aspx`. Produção, em `config.producao.ini`: `https://openportilheus.codeba.gov.br/openportcodeba/default.aspx`. Navegador Edge visível. Fluxo: login, tela 9401, Novo, gravar, enviar documento de carga.

## Viagem de teste — TI SUNRISE

Arquivo de origem: `C:\Users\danyp\Downloads\TI SUNRISE - Resumo de embarque.xlsx`.

Aba certa: **Resumo**. Motivo na coluna cujo cabeçalho contém "Motivo". A coluna AH "Tipo Ocorrência" é catálogo lateral e não entra na leitura. Agência, navio e produto são lidos na célula abaixo do rótulo, não na célula ao lado.

Doze paralisações em cinco capas (16/10 e 17/10/2026). Motivos do resumo: DDS, CHUVA, TROCA DE TURNO, DRAFT SURVEY, MANUTENÇÃO SPREADER.

Programação digitada na tela e ainda não necessariamente gravada: **1772**. Os três motivos do resumo que não estão na lista oficial já têm aproximação em `data/motivos.json`. A gravação ao vivo no QAS ainda não foi feita.

## URLs

A base usada pelo robô não leva `default.aspx`, porque `capa.py` concatena `cadastro.aspx`. `url_operacao` em `src/paralisacao/ui/ambiente.py` remove esse sufixo.

- QAS e produção simulada: `https://ilheus.codeba.gov.br/qas/openportcodeba/`
- Produção: `https://openportilheus.codeba.gov.br/openportcodeba/`

Teste desta máquina em 20/10/2026: `https://openportilheus.codeba.gov.br/openportcodeba/` e `.../default.aspx` passaram de 30 s sem código HTTP. O servidor aceita a conexão, mas a página não responde. O navegador do Bruno abre o site normalmente.

## Painel

`python -m paralisacao painel` sobe Flask em `127.0.0.1:8080` com `use_reloader=False`. Mudança de Python exige reinício. Reiniciar zera o estado em memória: login, resumo carregado e programação digitada e não enviada.

Dois cliques no executável também abrem esse painel. Não há planilha padrão embutida. Na etapa Planilha o usuário escolhe um arquivo `.xlsx` ou uma pasta com um único `.xlsx`. O painel lê o resumo da Intermarítima ou a planilha padrão. Na linha de comando o caminho vai em `--planilha`.

Etapas: Acesso, Resumo, Pendências, Execução, Resultado. O arquivo escolhido fica em `data/operacoes/` (pasta no `.gitignore`). A planilha padrão gerada só é gravada quando não há pendência. O modo padrão do código é produção. O teste de 20/10/2026 foi feito no QAS.

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

O empacotamento usa o `.venv` do projeto (Python 3.12) e o Playwright 1.49.1. O Chromium dessa versão é o **1148**. A pasta `chromium-1234` que sobrou na máquina não serve: o spec precisa cravar `chromium-1148`.

## Executável

Gerado em `c:\Users\danyp\Downloads\paralisacoes\dist\Paralisacoes\Paralisacoes.exe`. A pasta `dist` não entra no Git. O Chromium embutido é o **1148**. Uma montagem anterior tinha pego o 1234 e foi corrigida. O pacote que viaja para o computador do trabalho é a pasta `dist\Paralisacoes` inteira, não o exe sozinho. Não é preciso colocar uma pasta `data` ao lado do executável.

A planilha de teste do repositório é `data/planilha padrão.xlsx` (antes `data/Paralisacoes_YANGTZE_QUANTUM.xlsx`). O navio dentro dela continua YANGTZE QUANTUM, programação 1766.

Teste do painel pelo executável, em 20/10/2026, no QAS: a planilha foi lida, o resumo mostrou 7 capas e 16 paralisações, as pendências não pediram código e a execução listou as 16 na fila. **Gravar a primeira** não foi acionado. A tela Resultado ficou em "Nenhuma rodada concluída ainda". A gravação ao vivo no OpenPort continua pendente.

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
