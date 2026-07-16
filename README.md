# RPA de Paralisações — OpenPort CODEBA

Automação em Python utilizando Playwright que lê uma planilha de paralisações de navio (.xlsx) e as registra no sistema **OpenPort CODEBA**. O RPA busca a capa correspondente (operador, programação do navio, data, turno) ou a cria automaticamente se necessário, inserindo cada uma das paralisações (motivo, estadia, horários de início/fim e observações) com checagem automática contra duplicatas.

## 🏗️ Nova Estrutura de Módulos

O projeto foi totalmente refatorado de um monolito para uma arquitetura modularizada e de baixo acoplamento:

```
paralisacao/
├── src/
│   └── paralisacao/          # Pacote principal
│       ├── __init__.py
│       ├── __main__.py       # Ponto de entrada da CLI
│       ├── main.py           # Orquestrador principal da automação
│       ├── config.py         # Configurações imutáveis (dataclass Config)
│       ├── exceptions.py     # Centralização das exceções customizadas
│       ├── planilha.py       # Leitura e validação do .xlsx
│       ├── mapeamento.py     # Tradução e normalização de motivos/turnos
│       ├── relatorio.py      # Geração de relatórios executivos (Markdown)
│       ├── status.py         # Controle local de status e anti-duplicata
│       ├── navegacao.py      # Login e navegação pelas telas do OpenPort
│       ├── capa.py           # Métodos de busca e criação de capas
│       ├── popup.py          # Preenchimento e gravação no modal de paralisação
│       └── retry.py          # Mecanismo genérico de retry com backoff exponencial
├── tests/                    # Suíte de testes unitários (pytest)
├── relatorios/               # Relatórios executivos por rodada (rodada_*.md)
├── logs/                     # Logs de execução técnica (rodada_*.log)
├── data/                     # Planilhas, tabelas de referência e motivos.json
├── docs/                     # Documentação de apoio
├── screenshots/              # Evidências em caso de falha/erro
├── .env                      # Variáveis de ambiente locais (não versionado)
├── .env.example              # Modelo de variáveis de ambiente
├── pyproject.toml            # Configuração do build system, Ruff, pytest e coverage
└── requirements.txt
```

## 🚀 Instalação e Execução

### Pré-requisitos
* Python >= 3.10

### Instalação
```bash
python -m venv .venv
.venv\Scripts\activate        # Windows (PowerShell)
pip install -r requirements.txt
python -m playwright install chromium
```

### Configuração
1. Crie um arquivo `.env` baseado no `.env.example`.
2. Configure as credenciais do OpenPort (`OPENPORT_LOGIN` e `OPENPORT_SENHA`).
3. (Opcional) Ajuste a variável `OPERADOR` caso utilize outro código de empresa (padrão: `30002` para Intermarítima).

---

## 💻 Interface de Linha de Comando (CLI)

O RPA agora conta com uma CLI robusta que suporta diferentes subcomandos:

```bash
# Executar a automação completa
python -m paralisacao executar

# Apenas validar a planilha e exibir o plano de execução (Dry-Run)
python -m paralisacao validar [caminho_da_planilha.xlsx]

# Exibir o status de execução das capas salvas localmente
python -m paralisacao status
```

*Nota: Para compatibilidade retroativa, a execução sem subcomandos (`python -m paralisacao`) ou usando o parâmetro `--dry-run` continuam funcionando.*

---

## 🛠️ Regras de Negócio e Confiabilidade

### 1. Criação Automática de Capas
Caso a capa correspondente à linha do Excel não exista no OpenPort, o RPA realiza a criação automática navegando diretamente para a URL de criação (`Mv=Novo`), selecionando operador, programação de navio, data e turno, e extraindo o `codRegistro` recém-criado.

### 2. Mapeamento de Motivos
Os motivos da planilha são traduzidos usando duas opções complementares:
* **Mapeamento Externo (Recomendado):** Configurado no arquivo [`data/motivos.json`](file:///c:/Users/bruno.santos/Downloads/Projetos/paralisacao/data/motivos.json). Permite adicionar ou alterar traduções de motivos sem modificar o código.
* **Mapeamento Interno (Fallback):** Configurado no arquivo `config.py`.

A busca pelo código do motivo no OpenPort é feita digitando o código numérico extraído do arquivo [`data/tipo-paralizacoes.md`](file:///c:/Users/bruno.santos/Downloads/Projetos/paralisacao/data/tipo-paralizacoes.md) diretamente no campo do motivo.

### 3. Validação Real de Sucesso
O RPA não assume que a gravação teve sucesso meramente pelo fechamento do popup. O módulo `popup.py` inspeciona o DOM, detecta mensagens de sucesso e lança exceções explicitamente em caso de erro na tela ou dados obrigatórios ausentes.

### 4. Retry com Backoff Exponencial
Toda a comunicação crítica e instável com o OpenPort (login, busca/criação de capas, inserção de paralisações) é protegida pelo decorator `@com_retry()`, realizando até 3 tentativas automáticas antes de registrar uma falha.

---

## 🧪 Testes e Qualidade

O projeto está equipado com testes automatizados utilizando `pytest`, gerando relatórios de cobertura com `pytest-cov` e formatado pelo linter `Ruff`.

```bash
# Executar testes unitários e validar cobertura
$env:PYTHONPATH="src"; pytest

# Rodar o linter Ruff
ruff check src/
```
