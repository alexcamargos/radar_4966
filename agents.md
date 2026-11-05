# AGENTS.MD: Guia de Desenvolvimento Orientado por IA

## Plataforma de Inteligência em Risco de Crédito e Capital (Cooperativas de Crédito)

**Regulação Normativa:** Resolução CMN nº 4.966 / IFRS 9 e Resolução BCB nº 352  
**Fontes Oficiais:** Banco Central do Brasil (IF.data e Relatório de Estabilidade Financeira - REF)  
**Arquitetura:** Python 3.12+ (Astral `uv`), DuckDB, Pydantic V2 e Frontend Nativo em HTML5 / CSS3 / JavaScript Vanilla (Zero Frameworks Pesados).

Este documento define os perfis de agentes, regras de negócio inegociáveis, padrões de engenharia de software e protocolos de validação contínua (Eval-Driven Development) para guiar agentes de IA na implementação 100% autônoma deste projeto.

---

## 1. Regras Globais e Guardrails de Domínio (System Directives)

Todo assistente de IA operando nesta base de código deve respeitar estritamente as seguintes premissas:

1. **Separação entre Modelos de Perda:**
   * Nunca confunda a antiga **Resolução 2.682** (modelo de *perda incorrida*, calendarizada por faixas de atraso estritas de 15 a 180 dias) com a **Resolução CMN 4.966 / IFRS 9** (modelo de *perda esperada* - ECL baseada em Estágios 1, 2 e 3 com variáveis *forward-looking*).
2. **Definição Estrita de Ativo Problemático (AP):**
   * O AP não é apenas saldo vencido $> 90$ dias. Ele engloba: (a) atrasos superiores a 90 dias; (b) renegociações/reestruturações por estresse financeiro (*forbearance*); e (c) operações em Estágio 3 por deterioração substancial da capacidade de pagamento com indício objetivo de perda. Todo contrato em Estágio 3 é Ativo Problemático.
3. **Equação do Custo de Risco (*Cost of Risk* - CoR):**
   * Sempre mensurar a despesa líquida de provisão em 12 meses dividida pela carteira classificada média do período.
4. **Precisão Numérica Estrita:**
   * Moeda e saldos contábeis devem ser manipulados com tipos decimais de precisão fixa (`Decimal(18, 2)` em Python e SQL) para evitar discrepâncias em centavos que reprovem em auditoria contábil COSIF/Bacen.
5. **Privacidade de Dados (LGPD & Sigilo Bancário - LC 105/01):**
   * Nunca expor dados identificáveis de cooperados. Chaves primárias de associados devem ser inteiros anonimizados ou hashes unidirecionais.
6. **Padrões de Engenharia e Qualidade de Código:**
   * **Gerenciador de Dependências:** Usar exclusivamente o **Astral `uv`** (`uv add`, `uv run pytest`). É proibido sugerir ou usar comandos `pip` diretos.
   * **Testes e Mocking:** Utilizar exclusivamente **`pytest`** e **`pytest-mock`** (fixture `mocker`). É terminantemente proibido o uso do módulo built-in `unittest`, classes `unittest.TestCase` ou `unittest.mock`. Todos os testes devem ser baseados em funções.
   * **Estilo e Documentação:** Código estritamente aderente ao **PEP 8** e com **Google Style Docstrings** obrigatórias em todos os módulos, classes, métodos e funções, contendo as seções `Args:`, `Returns:` e `Raises:`.
   * **Padrão Git:** Commits granulares e atômicos (1 a 2 arquivos por commit), mensagens em português do Brasil (pt-BR) no modo imperativo e no padrão Conventional Commits (`feat`, `fix`, `test`, `refactor`, `chore`, `docs`).

---

## 2. Estrutura Canônica de Diretórios do Projeto

Para garantir que todos os agentes manipulem os arquivos nos locais corretos, a árvore de diretórios do repositório é padronizada da seguinte forma:

```text
radar_4966/
├── pyproject.toml
├── README.md
├── spec.md
├── agents.md
├── dashboard/                # Aplicação Web Nativa (HTML5 / CSS3 / Vanilla JS)
│   ├── index.html
│   ├── styles.css
│   ├── app.js
│   └── data/
│       └── dashboard_data.json
├── src/
│   ├── __init__.py
│   ├── schemas/              # Modelos formais Pydantic V2 de todas as tabelas
│   │   ├── __init__.py
│   │   ├── dimensions.py
│   │   └── facts.py
│   ├── ingestion/            # Conectores Bacen (IF.data e REF) e gerador sintético
│   │   ├── __init__.py
│   │   ├── ifdata_client.py
│   │   ├── ref_client.py
│   │   └── synthetic_generator.py
│   ├── staging/              # Regras de enquadramento da Res. 4.966 (Estágios e AP)
│   │   ├── __init__.py
│   │   └── classifier_4966.py
│   └── analytics/            # Fórmulas de CoR, Vintages, conciliação e exportação
│       ├── __init__.py
│       ├── metrics.py
│       └── data_exporter.py
└── tests/
    ├── conftest.py
    ├── test_schemas.py
    ├── test_ingestion.py
    ├── test_classifier_4966.py
    ├── test_analytics.py
    └── test_reconciliation.py
```

---

## 3. Personas de Agentes Especializados

### Agente 1: `@data-engineer` (Engenharia de Dados e Ingestão)
* **Objetivo:** Ingerir, validar e consolidar bases públicas (IF.data e REF) e gerar a base sintética determinística de contratos e DRE da singular.
* **Stack Principal:** Python 3.12+, Astral `uv`, Pydantic V2, DuckDB, Pandas/Polars.
* **Responsabilidades:**
  * Implementar e validar os schemas Pydantic em `src/schemas/`.
  * Construir o gerador de dados sintéticos `src/ingestion/synthetic_generator.py` com `seed=42`, garantindo conciliação matemática com `f_DRE_Gerencial`.
  * Criar clientes de extração das séries históricas do IF.data e REF do Bacen com fallbacks offline seguros.
* **Critério de Sucesso:** `uv run pytest tests/test_schemas.py tests/test_ingestion.py` retorna código 0.

### Agente 2: `@credit-risk-quant` (Modelagem Regulatória e Resolução 4.966)
* **Objetivo:** Implementar com precisão cirúrgica as regras de transição de Estágios 1, 2 e 3, identificação de Ativo Problemático e Perda Esperada (ECL).
* **Stack Principal:** Python 3.12+, DuckDB, SciPy, Statsmodels.
* **Responsabilidades:**
  * Implementar o motor de classificação em `src/staging/classifier_4966.py`.
  * Aplicar as regras determinísticas de SICR ($\Delta \text{Rating} \ge 2$, $\text{PD}_{\text{atual}} \ge 2.5 \times \text{PD}_{\text{origem}}$ ou atraso de 31 a 90 dias) e de Estágio 3 (atraso $> 90$, renegociação ou rating 10).
  * Calcular a matriz de safras (*Vintage Analysis*) por MOB (1, 3, 6, 12, 24 meses).
* **Critério de Sucesso:** `uv run pytest tests/test_classifier_4966.py` cobre todos os cenários limítrofes regulatórios.

### Agente 3: `@bi-architect` (Modelagem Analítica e Compilação do Dataset)
* **Objetivo:** Construir as views agregadas no DuckDB, auditar a conciliação contábil contra o balancete e exportar o dataset consolidado para o dashboard.
* **Stack Principal:** DuckDB, Python 3.12+, SQL Analítico.
* **Responsabilidades:**
  * Implementar em `src/analytics/metrics.py` as queries SQL analíticas de: Carteira Ativa, Saldo de AP, Taxa de Provisão, Gap de Cobertura, Over90 no AP e CoR 12M em janela móvel.
  * Implementar em `src/analytics/data_exporter.py` a exportação estruturada para `dashboard/data/dashboard_data.json`.
  * Garantir conciliação auditada de centavos entre as tabelas fato analíticas e o balancete.
* **Critério de Sucesso:** `uv run pytest tests/test_analytics.py tests/test_reconciliation.py` aprova todas as contas sem divergência.

### Agente 4: `@frontend-engineer` (Dashboard Executivo Nativo)
* **Objetivo:** Construir a interface web executiva interativa para a Diretoria, estritamente em HTML5 semântico, CSS3 corporativo puro e JavaScript Vanilla com Chart.js.
* **Stack Principal:** HTML5, CSS3 Moderno (Custom Properties, CSS Grid, Flexbox), JavaScript Vanilla (ES6+, DOM, Fetch API), Chart.js (CDN/local). **ZERO DEPENDÊNCIA de React, Tailwind ou frameworks pesados.**
* **Responsabilidades:**
  * Implementar `index.html` contendo as 3 telas executivas: (1) Post Executivo & Benchmarking, (2) Anatomia do Risco 4.966 e (3) Safras & Simulador de Capital.
  * Implementar `styles.css` com paleta dark terminal bancária sóbria, tipografia profissional e layout 100% responsivo para monitores e tablets.
  * Implementar `app.js` com consumo dinâmico do `dashboard_data.json`, inicialização dos gráficos Chart.js, cruzamento dinâmico de séries e simulador What-If reativo no cliente.
* **Critério de Sucesso:** A interface renderiza perfeitamente em navegador moderno sem qualquer erro de console e com recálculo instantâneo no slider de sensibilidade de capital.

---

## 4. Matriz de Eval Gates e Protocolo de Handoffs

Nenhum agente deve iniciar sua etapa sem que o artefato da etapa anterior tenha sido validado pelo respectivo teste automatizado:

| Etapa | Agente Responsável | Artefato Produzido | Comando de Validação (Eval Gate) |
| :--- | :--- | :--- | :--- |
| **Etapa 1** | `@data-engineer` | `src/schemas/`, `src/ingestion/` e dados sintéticos validados | `uv run pytest tests/test_schemas.py tests/test_ingestion.py` |
| **Etapa 2** | `@credit-risk-quant` | `src/staging/classifier_4966.py` | `uv run pytest tests/test_classifier_4966.py` |
| **Etapa 3** | `@bi-architect` | `src/analytics/` e `dashboard/data/dashboard_data.json` | `uv run pytest tests/test_analytics.py tests/test_reconciliation.py` |
| **Etapa 4** | `@frontend-engineer` | `dashboard/index.html`, `styles.css`, `app.js` | Verificação do carregamento de dados e ausência de erros de console |

---

## 5. Prompts Operacionais Prontos de Referência

### Para o `@data-engineer`:
> "Atue como `@data-engineer`. Implemente os schemas Pydantic V2 em `src/schemas/` conforme o `spec.md`. Em seguida, crie `src/ingestion/synthetic_generator.py` utilizando Astral `uv` e precisão `Decimal(18, 2)`. O gerador deve produzir 24 meses de competências para `f_Carteira_Mensal` e `f_DRE_Gerencial` com `seed=42`, garantindo conciliação estrita entre a soma do saldo da carteira e o balancete. Escreva os testes correspondentes em `tests/test_schemas.py` e `tests/test_ingestion.py` usando exclusivamente `pytest` e docstrings no padrão Google."

### Para o `@credit-risk-quant`:
> "Atue como `@credit-risk-quant`. Implemente o motor de enquadramento em `src/staging/classifier_4966.py`. Siga rigorosamente as regras da Resolução CMN 4.966 para Estágios 1, 2 (incluindo critérios SICR matemáticos) e 3 (Ativo Problemático). Implemente a perda esperada (ECL) e as curvas de safra (MOB). Crie a suíte de testes em `tests/test_classifier_4966.py` com `pytest` testando todos os casos de borda."

### Para o `@bi-architect`:
> "Atue como `@bi-architect`. Crie em `src/analytics/metrics.py` as rotinas analíticas em DuckDB/SQL que calculam: Carteira Ativa, Saldo de AP, Taxa de Provisão, Gap de Cobertura, % Over90 no AP, CoR 12M e Índice de Cobertura ECL. Implemente em `src/analytics/data_exporter.py` a exportação para `dashboard/data/dashboard_data.json`. Crie `tests/test_analytics.py` e `tests/test_reconciliation.py` para certificar a conciliação contábil."

### Para o `@frontend-engineer`:
> "Atue como `@frontend-engineer`. Construa o painel executivo em `dashboard/` utilizando estritamente HTML5 semântico, CSS3 puro (com variáveis CSS e layout responsivo escuro) e JavaScript Vanilla moderno com Chart.js. Não utilize React, Tailwind ou qualquer outro framework pesado. O painel deve consumir `data/dashboard_data.json` e apresentar as 3 telas estratégicas, incluindo o marcador dinâmico de cruzamento de linhas e o simulador interativo What-If de sensibilidade de capital."
