# Guia Operacional da Automação — RPA Paralisações OpenPort CODEBA

Este documento descreve as diretrizes operacionais, a estrutura de dados de entrada, os mapeamentos de motivos, o fluxo de execução e a gestão de status do RPA.

---

## 1. Demanda da Planilha (Dados de Entrada)

A planilha de entrada deve ser inserida na pasta `data/` e seguir a estrutura abaixo.

### Estrutura das Colunas Obrigatórias

| Coluna | Descrição | Exemplo |
|---|---|---|
| `Registro` | Número sequencial da capa (identificador único da linha) | `1` |
| `Navio` | Nome da embarcação para filtro da estadia | `YANGTZE QUANTUM` |
| `Data` | Data da operação (DD/MM/YYYY) | `09/07/2026` |
| `Produto` | Descrição do produto carregado/descarregado | `Milho` |
| `Período` | Turno do período no formato `HH:MM/HH:MM` | `13:00/19:00` |
| `Início` | Horário de início da paralisação | `13:00` ou `13:00:00` |
| `Fim` | Horário de término da paralisação | `13:15` ou `13:15:00` |
| `Motivo` | Descrição do motivo conforme digitado na planilha | `DDS` |

### Dados do Exemplo Padrão
* **Navio:** YANGTZE QUANTUM (Programação: 1766)
* **Arquivo padrão:** `data/Paralisacoes_YANGTZE_QUANTUM.xlsx`
* **Turnos e correspondência:**
  * `01:00/07:00` → Turno 1 (01:00 - 07:00)
  * `07:00/13:00` → Turno 2 (07:00 - 13:00)
  * `13:00/19:00` → Turno 3 (13:00 - 19:00)
  * `19:00/01:00` → Turno 4 (19:00 - 01:00)

---

## 2. Mapeamento de Motivos

Para cadastrar ou atualizar o mapeamento de um motivo da planilha para o sistema OpenPort, **use o arquivo externo [`data/motivos.json`](file:///c:/Users/bruno.santos/Downloads/Projetos/paralisacao/data/motivos.json)**. Isso evita a necessidade de alterar o código-fonte da aplicação.

### Exemplo de Configuração em `motivos.json`
```json
{
  "mapeamentos": {
    "CHUVA": "CHUVA",
    "DDS": "CONVENIENCIA DO USUARIO",
    "DESCANSO": "CONVENIENCIA DO USUARIO",
    "DDS / CONVENIENCIA DO USUARIO": "CONVENIENCIA DO USUARIO",
    "DEFEITO NO SPEED": "DEFEITO MECANICO LINHA DE EMBARQUE"
  }
}
```

O RPA converte o motivo da planilha em código de preenchimento usando o arquivo auxiliar [`data/tipo-paralizacoes.md`](file:///c:/Users/bruno.santos/Downloads/Projetos/paralisacao/data/tipo-paralizacoes.md) que lista todos os IDs do OpenPort (por exemplo: `CHUVA` -> ID `5`, `CONVENIENCIA DO USUARIO` -> ID `34`).

---

## 3. Fluxo de Execução Técnica

Abaixo está o fluxo percorrido pelo Playwright no sistema OpenPort CODEBA:

```
Login → Tela 7001 → Buscar Capa 
  ├── Se Capa Não Existe → Executar Fluxo de Criação (Novo) → Salvar codRegistro
  └── Se Capa Existe → Abrir Capa
        └── Ir para Aba Paralisação → Clicar no Botão ⊕ (Novo) → 
              ├── Digitar Código do Motivo → Pressionar Tab (Carregamento AJAX)
              ├── Selecionar Estadia pelo Navio
              ├── Preencher Data/Hora de Início/Fim (com ajuste de data para Turnos Noturnos)
              ├── Gravar Paralisação → Executar Validação de Sucesso Real no DOM
              └── Fechar Popup (CloseDialog) → Atualizar Grid Principal
```

### Seletores e Elementos Utilizados
* **Login:** `input#User`, `input#Pass`, `button#Entrar`
* **Menu de Acesso Rápido:** `input#txtMenuAccess` (digitar `7001` + Enter)
* **Busca de Capa:** Operador (`#sqlNUM_EMPRESA_2`), Progr. Navio (`#SqlNUM_PROGR_NAVIO_2`), Data (`#sqlDAT_INICIO`), Turno (`select#sqlNUM_TURNO`), Filtrar (`button#BPESQUISAR`)
* **Botão Adicionar Paralisação:** Seletor CSS `#Detail7 table thead a img`
* **Gravação e Fechamento:** Botão Gravar (`button#GRAVAR`), JS para fechar (`CloseDialog()`)
* **Validação de Gravação:** Leitura de body (`body`) do popup para verificar existência de termos de sucesso ou erro (ex: `GravacaoError`).

---

## 4. Memória de Status (Anti-Duplicata)

### Arquivo de Controle: `data/status.json`

O RPA mantém em tempo de execução um histórico local das operações. Antes de inserir qualquer paralisação, duas verificações de duplicidade são realizadas:
1. **Verificação no Status Local:** Checagem no arquivo `data/status.json` se a paralisação já consta com status `ok`.
2. **Verificação Online na Grid:** Leitura em tempo real do grid de registros na aba **Paralisação** do OpenPort CODEBA (`table#TQuery`) para identificar se a paralisação foi lançada em outra execução ou manualmente.

### Estados das Capas no Status
* `pendente`: Capa identificada na planilha, mas ainda não processada.
* `parcial`: Capa processada, porém uma ou mais paralisações falharam ou foram puladas por falta de mapeamento de motivo.
* `completa`: Capa processada e todas as paralisações foram registradas com sucesso.

---

## 5. Auditoria e Logs

1. **Logs de Rodada:** Gravados na pasta `logs/` com o padrão `rodada_NNN.log`, contendo o rastreamento completo de cada clique, chamada de API e retentativas do decorator `@com_retry`.
2. **Relatório Executivo:** Gravado em `relatorios/` com o padrão `rodada_NNN.md` detalhando dados estatísticos, capas criadas/abertas, paralisações lançadas e motivos pulados.
3. **screenshots:** Em caso de erro técnico ou de validação, screenshots da tela do navegador no exato momento da falha são gravadas na pasta `screenshots/`.

---

## 6. Mapeamento de Arquivos do Projeto

| Arquivo/Pasta | Função Principal |
|---|---|
| [`src/paralisacao/main.py`](file:///c:/Users/bruno.santos/Downloads/Projetos/paralisacao/src/paralisacao/main.py) | Orquestrador principal e lógica CLI |
| [`src/paralisacao/config.py`](file:///c:/Users/bruno.santos/Downloads/Projetos/paralisacao/src/paralisacao/config.py) | Dataclass `Config` e seletores padrão |
| [`src/paralisacao/browser.py`](file:///c:/Users/bruno.santos/Downloads/Projetos/paralisacao/src/paralisacao/browser.py) | Helpers do Playwright (preenchimento, clique via JS, screenshots) |
| [`src/paralisacao/navegacao.py`](file:///c:/Users/bruno.santos/Downloads/Projetos/paralisacao/src/paralisacao/navegacao.py) | Controle de fluxos de login e navegação de menus |
| [`src/paralisacao/capa.py`](file:///c:/Users/bruno.santos/Downloads/Projetos/paralisacao/src/paralisacao/capa.py) | Busca e cadastro automatizado de capas |
| [`src/paralisacao/popup.py`](file:///c:/Users/bruno.santos/Downloads/Projetos/paralisacao/src/paralisacao/popup.py) | Preenchimento, cálculo de horas noturnas e validação do popup |
| [`src/paralisacao/status.py`](file:///c:/Users/bruno.santos/Downloads/Projetos/paralisacao/src/paralisacao/status.py) | Persistência de status local e leitura online da grid |
| [`src/paralisacao/mapeamento.py`](file:///c:/Users/bruno.santos/Downloads/Projetos/paralisacao/src/paralisacao/mapeamento.py) | Conversão de strings, turnos e leitura do `motivos.json` |
| [`src/paralisacao/retry.py`](file:///c:/Users/bruno.santos/Downloads/Projetos/paralisacao/src/paralisacao/retry.py) | Decorator `@com_retry` para resiliência |
| [`data/motivos.json`](file:///c:/Users/bruno.santos/Downloads/Projetos/paralisacao/data/motivos.json) | Cadastro externo de equivalência de motivos |
| [`data/tipo-paralizacoes.md`](file:///c:/Users/bruno.santos/Downloads/Projetos/paralisacao/data/tipo-paralizacoes.md) | Banco de códigos de paralisações do sistema |
