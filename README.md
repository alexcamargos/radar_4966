# Radar 4966 — Plataforma de Inteligência em Risco de Crédito e Capital

Plataforma analítica e executiva voltada à Diretoria (CEO, CRO, CFO, CCO) e Conselhos de Cooperativas de Crédito para gestão de risco de crédito, perda esperada (*Expected Credit Loss* - ECL) e capital regulatório sob a vigência da **Resolução CMN nº 4.966 / IFRS 9** e **Resolução BCB nº 352**.

---

## 1. Visão Geral da Arquitetura

O projeto adota uma arquitetura de alta performance, 100% em código aberto e livre de dependências pesadas de frontend ou microsserviços proprietários:

* **Engine Analítico & Pipeline:** Python 3.12+ gerenciado pelo Astral `uv`, **DuckDB** para agregação analítica em SQL canônico e precisão monetária fixa (`Decimal(18, 2)`).
* **Contratos de Dados:** Modelos formais estritos em **Pydantic V2** em `src/schemas/`.
* **Benchmarking Oficial Bacen:** Clientes para séries históricas do **IF.data** (SNCC e SFN) e **Relatório de Estabilidade Financeira (REF)** em `src/ingestion/`.
* **Painel Executivo C-Level:** Aplicação web estática em HTML5 semântico, CSS3 corporativo puro (Dark Theme) e JavaScript Vanilla moderno (ESModules e Chart.js) em `dashboard/`.

---

## 2. Estrutura do Projeto

```text
radar_4966/
├── pyproject.toml               # Dependências uv, pytest, ruff e mypy
├── spec.md                      # Especificação técnica e negocial (PRD)
├── agents.md                    # Diretrizes de IA, personas e eval gates
├── dashboard/                   # Interface Web executiva (HTML5 / CSS3 / Vanilla JS)
│   ├── index.html
│   ├── styles.css
│   ├── app.js
│   └── data/
│       └── dashboard_data.json
├── src/
│   ├── schemas/                 # Contratos Pydantic V2 (dimensões e fatos)
│   ├── ingestion/               # Conectores Bacen e gerador sintético determinístico
│   ├── staging/                 # Motor de enquadramento 4.966 (Estágios 1, 2 e 3 e AP)
│   └── analytics/               # DuckDB, CoR 12M, Vintages e exportador do dashboard
└── tests/                       # Suíte completa de testes automatizados com pytest
```

---

## 3. Instalação e Execução com Astral `uv`

### Pré-requisitos
* Python 3.12+
* [Astral `uv`](https://github.com/astral-sh/uv)

### Instalação de dependências
```bash
uv sync
```

### Execução do Pipeline Analítico
Para compilar a base sintética determinística de 24 meses, aplicar as regras regulatórias e exportar o dataset consolidado:
```bash
uv run python -m src.analytics.data_exporter
```

### Visualização do Dashboard C-Level
Inicie um servidor web local leve e abra no navegador:
```bash
uv run python -m http.server 8000 --directory dashboard
```
Acesse: [http://localhost:8000](http://localhost:8000)

---

## 4. Validação e Qualidade de Código (Eval Gates)

### Execução de toda a suíte de testes
```bash
uv run pytest
```

### Execução segmentada por etapa (Eval Gates)
* **Etapa 1 (Schemas e Ingestão):**
  ```bash
  uv run pytest tests/test_schemas.py tests/test_ingestion.py
  ```
* **Etapa 2 (Classificação 4.966):**
  ```bash
  uv run pytest tests/test_classifier_4966.py
  ```
* **Etapa 3 (Métricas Analíticas e Conciliação):**
  ```bash
  uv run pytest tests/test_analytics.py tests/test_reconciliation.py
  ```

### Verificação de Tipagem Estrita e Estilo PEP 8
```bash
uv run ruff check src tests
uv run ruff format --check src tests
uv run mypy src tests
```
