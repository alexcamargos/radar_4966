# Documento de Especificação Técnica e Negocial (PRD)
## Projeto: Plataforma Executiva de Inteligência de Risco de Crédito e Dinâmica de Provisão
**Público-Alvo:** Diretoria Executiva (CEO, CRO, CFO, CCO) e Conselho de Administração  
**Normas de Referência:** Resolução CMN nº 4.966 / IFRS 9 e Resolução BCB nº 352  
**Fontes Oficiais de Benchmarking:** Banco Central do Brasil (Portal IF.data e Relatório de Estabilidade Financeira - REF)  
**Arquitetura de Entrega:** Aplicação Analítica Autônoma em Código Aberto (Python 3.12+ com Astral `uv`, DuckDB e Dashboard Nativo em HTML5/CSS3/JavaScript Vanilla, sem dependência de frameworks pesados).

---

## 1. Sumário Executivo e Proposta de Valor

### 1.1 Contexto e Justificativa
Com a vigência plena da Resolução CMN nº 4.966, a contabilidade bancária brasileira abandonou o modelo de *perda incorrida* (antiga Res. 2.682) em favor do modelo preditivo de *perda esperada* (*Expected Credit Loss* - ECL). Como demonstrado pelos relatórios agregados do Banco Central (REF e Panorama do SNCC), a provisão agora reconhece o risco ex-ante (via variáveis macroeconômicas *forward-looking* e aumento significativo de risco de crédito - SICR), fazendo com que o **custo de provisão chegue antes da inadimplência efetiva superior a 90 dias**.

### 1.2 Objetivo Estratégico
Fornecer à Diretoria Executiva um painel analítico automatizado que:
1. **Compare o desempenho da cooperativa singular contra o Sistema Nacional de Crédito Cooperativo (SNCC) e o Sistema Financeiro Nacional (SFN)** a partir dos dados do IF.data e REF.
2. **Decomponha a carteira interna em Estágios (1, 2 e 3)** e monitore as migrações de risco antes da materialização do *default*.
3. **Avalie o Custo de Crédito (*Cost of Risk*)** e o consumo do Patrimônio de Referência (Capital Regulatório) por produto e safra.
4. **Permita a tomada de decisão ágil** sobre precificação (*pricing* ajustado ao risco), mix de concessão e limites operacionais.

### 1.3 Decisão de Arquitetura de Software e Visualização
Para viabilizar a construção, teste e manutenção autônoma por agentes de IA e assegurar portabilidade total sem lock-in corporativo:
* **Engine e Pipeline Analítico:** Python 3.12+ gerenciado exclusivamente via Astral `uv`. Uso de **DuckDB** e **Polars/Pandas** para processamento analítico de alta performance, manipulação com `Decimal` de precisão fixa e exportação em Parquet.
* **Camada de Validação de Dados:** Modelos formais em **Pydantic V2** para garantir contratos de dados e tipagem estrita na ingestão e transformação.
* **Interface Executiva (Dashboard C-Level):** Frontend desenvolvido estritamente em **HTML5 semântico, CSS3 puro (Design Tokens, Grid/Flexbox modernos, paleta escura executiva) e JavaScript Vanilla (ESModules, Fetch API e Chart.js via CDN/local)**.
* **Proibição de Frameworks Complexos:** Fica estritamente vedado o uso de frameworks pesados de frontend (como React, Vue, Angular, Tailwind CSS) ou frameworks de backend que exijam infraestrutura dedicada complexa (como FastAPI ou Django em runtime de dashboard). O pipeline Python compila os dados finais em `dashboard_data.json`, permitindo visualização estática instantânea (`file://` ou servidor local leve com `python -m http.server`).

---

## 2. Arquitetura do Modelo de Dados

O modelo analítico segue um esquema estrela (*Star Schema*) padronizado, gerenciado no DuckDB / Parquet:

```
                      ┌──────────────────────┐
                      │    d_Calendario      │
                      └──────────┬───────────┘
                                 │
      ┌──────────────────────────┼──────────────────────────┐
      │                          │                          │
┌─────┴──────────────┐ ┌─────────┴────────────┐ ┌───────────┴──────────┐
│   d_Associado      │ │  f_Carteira_Mensal   │ │   f_IFData_SNCC      │
└────────────────────┘ └─────────┬────────────┘ └──────────────────────┘
                                 │
┌────────────────────┐           │              ┌──────────────────────┐
│   d_LinhaCredito   ├───────────┤              │   f_REF_Macro_BCB    │
└────────────────────┘           │              └──────────────────────┘
                       ┌─────────┴────────────┐
                       │   f_DRE_Gerencial    │
                       └──────────────────────┘
```

---

## 3. Schemas de Validação (Pydantic V2) e Dicionário de Dados

Todos os registros ingeridos e transformados devem ser validados através dos contratos formais em Pydantic especificados abaixo.

### 3.1 Schemas das Tabelas Dimensão

```python
from datetime import date
from decimal import Decimal
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict


class TipoPessoaEnum(str, Enum):
    PF = "PF"
    PJ = "PJ"


class SegmentoCooperadoEnum(str, Enum):
    AGRO = "Agro"
    COMERCIAL = "Comercial"
    VAREJO = "Varejo"
    SERVIDOR_PUBLICO = "Servidor Publico"
    OUTROS = "Outros"


class GrupoModalidadeBacenEnum(str, Enum):
    CREDITO_RURAL = "Credito Rural"
    CAPITAL_DE_GIRO = "Capital de Giro"
    CONSUMO = "Consumo"
    HABITACIONAL = "Habitacional"


class TipoGarantiaEnum(str, Enum):
    FIDEJUSSORIA = "Fidejussoria"
    ALIENACAO_FIDUCIARIA = "Alienacao Fiduciaria"
    PENHOR_AGRICOLA = "Penhor Agricola"
    LIMPA = "Limpa"


class DimCalendarioSchema(BaseModel):
    """Schema para a dimensão temporal mensal."""
    model_config = ConfigDict(strict=True)

    data: date = Field(..., description="Chave temporal no último dia de cada mês (PK)")
    ano: int = Field(..., ge=2000, le=2100, description="Ano no formato AAAA")
    mes_ano: str = Field(..., pattern=r"^(Jan|Fev|Mar|Abr|Mai|Jun|Jul|Ago|Set|Out|Nov|Dez)/\d{4}$")
    trimestre: str = Field(..., pattern=r"^[1-4]T$")


class DimAssociadoSchema(BaseModel):
    """Schema para a dimensão de associados da cooperativa."""
    model_config = ConfigDict(strict=True)

    id_associado: int = Field(..., ge=1, description="Identificador unívoco anonimizado (PK)")
    tipo_pessoa: TipoPessoaEnum
    segmento_cooperado: SegmentoCooperadoEnum
    data_admissao: date
    rating_interno_comportamental: int = Field(..., ge=1, le=10, description="Score interno de 1 (melhor) a 10 (pior)")


class DimLinhaCreditoSchema(BaseModel):
    """Schema para a dimensão de modalidades de crédito."""
    model_config = ConfigDict(strict=True)

    id_linha: int = Field(..., ge=1, description="Código interno da modalidade (PK)")
    nome_linha: str = Field(..., min_length=3, max_length=100)
    grupo_modalidade: GrupoModalidadeBacenEnum
    tipo_garantia_predominante: TipoGarantiaEnum
```

### 3.2 Schemas das Tabelas Fato Internas

```python
class FatoCarteiraMensalSchema(BaseModel):
    """Schema da carteira analítica individual por operação/contrato."""
    model_config = ConfigDict(strict=True)

    data_fechamento: date = Field(..., description="Último dia do mês contábil (FK)")
    id_contrato: int = Field(..., ge=1, description="Identificador do contrato (PK Composta)")
    id_associado: int = Field(..., ge=1, description="FK para d_Associado")
    id_linha: int = Field(..., ge=1, description="FK para d_LinhaCredito")
    data_concessao: date = Field(..., description="Data da contratação/liberação da operação")
    saldo_devedor_contabil: Decimal = Field(..., max_digits=18, decimal_places=2, ge=Decimal("0.00"))
    dias_atraso: int = Field(..., ge=0, description="Dias de atraso (DPD - Days Past Due)")
    saldo_vencido_over90: Decimal = Field(..., max_digits=18, decimal_places=2, ge=Decimal("0.00"))
    indicador_renegociacao: int = Field(..., ge=0, le=1, description="1 se renegociado por estresse financeiro, 0 cc")
    indicador_ativo_problematico: int = Field(..., ge=0, le=1, description="1 se AP conforme Res. 4.966, 0 cc")
    estagio_contabil: int = Field(..., ge=1, le=3, description="Estágio Res. 4.966 (1, 2 ou 3)")
    probabilidade_default_pd: Decimal = Field(..., max_digits=6, decimal_places=4, ge=Decimal("0.0000"), le=Decimal("1.0000"))
    loss_given_default_lgd: Decimal = Field(..., max_digits=6, decimal_places=4, ge=Decimal("0.0000"), le=Decimal("1.0000"))
    saldo_provisao_constituida: Decimal = Field(..., max_digits=18, decimal_places=2, ge=Decimal("0.00"))


class FatoDREGerencialSchema(BaseModel):
    """Schema do balancete/DRE mensal da cooperativa singular."""
    model_config = ConfigDict(strict=True)

    data_fechamento: date = Field(..., description="Data do fechamento contábil mensal (PK)")
    despesa_pdd_mes: Decimal = Field(..., max_digits=18, decimal_places=2, ge=Decimal("0.00"))
    recuperacao_credito_mes: Decimal = Field(..., max_digits=18, decimal_places=2, ge=Decimal("0.00"))
    despesa_liquida_pdd_mes: Decimal = Field(..., max_digits=18, decimal_places=2)
    saldo_carteira_total: Decimal = Field(..., max_digits=18, decimal_places=2, ge=Decimal("0.00"))
    sobras_liquidas_exercicio: Decimal = Field(..., max_digits=18, decimal_places=2)
    patrimonio_referencia_pr: Decimal = Field(..., max_digits=18, decimal_places=2, ge=Decimal("0.00"))
    rwa_risco_credito: Decimal = Field(..., max_digits=18, decimal_places=2, ge=Decimal("0.00"))
```

### 3.3 Schemas das Tabelas Fato Externas (Bacen / Benchmarking)

```python
class SegmentoIFDataEnum(str, Enum):
    COOPERATIVAS_SINGULARES = "Cooperativas Singulares"
    SNCC_CONSOLIDADO = "SNCC Consolidado"
    SFN_TOTAL = "SFN Total"


class SegmentoREFEnum(str, Enum):
    SNCC = "SNCC"
    SFN = "SFN"


class FatoIFDataSNCCSchema(BaseModel):
    """Schema para dados agregados do portal IF.data do Banco Central (Trimestral)."""
    model_config = ConfigDict(strict=True)

    data_trimestre: date = Field(..., description="Fim do trimestre de referência")
    segmento_analise: SegmentoIFDataEnum
    carteira_total_bacen: Decimal = Field(..., max_digits=18, decimal_places=2, ge=Decimal("0.00"))
    provisao_total_bacen: Decimal = Field(..., max_digits=18, decimal_places=2, ge=Decimal("0.00"))
    ativo_problematico_bacen: Decimal = Field(..., max_digits=18, decimal_places=2, ge=Decimal("0.00"))
    ap_over90_bacen: Decimal = Field(..., max_digits=18, decimal_places=2, ge=Decimal("0.00"))
    percentual_ap_ifdata: Decimal = Field(..., max_digits=6, decimal_places=4, ge=Decimal("0.0000"), le=Decimal("1.0000"))
    percentual_provisao_ifdata: Decimal = Field(..., max_digits=6, decimal_places=4, ge=Decimal("0.0000"), le=Decimal("1.0000"))


class FatoREFMacroBCBSchema(BaseModel):
    """Schema para indicadores macroprudenciais do Relatório de Estabilidade Financeira (Semestral)."""
    model_config = ConfigDict(strict=True)

    data_semestre: date = Field(..., description="Fim do semestre de referência")
    segmento: SegmentoREFEnum
    taxa_perda_esperada_estimada: Decimal = Field(..., max_digits=6, decimal_places=4, ge=Decimal("0.0000"), le=Decimal("1.0000"))
    indice_cobertura_perda_esperada: Decimal = Field(..., max_digits=6, decimal_places=4, ge=Decimal("0.0000"))
    custo_credito_12m_percentual: Decimal = Field(..., max_digits=6, decimal_places=4, ge=Decimal("0.0000"), le=Decimal("1.0000"))
```

---

## 4. Regras Determinísticas de Enquadramento (Resolução CMN 4.966)

Para eliminar qualquer ambiguidade ou alucinação do agente na classificação das operações, aplicam-se estritamente os seguintes critérios determinísticos:

### 4.1 Classificação em Estágios (1, 2 e 3)

1. **Estágio 3 (Ativo Problemático / Default):** Uma operação é classificada em Estágio 3 se atender a **qualquer** uma das seguintes condições:
   * Atraso no pagamento de principal ou juros superior a 90 dias (`dias_atraso > 90`);
   * Operação renegociada/reestruturada por estresse financeiro (*forbearance*) (`indicador_renegociacao = 1`);
   * Rating de crédito interno deteriorado ao nível máximo de risco (`rating_interno_comportamental = 10`);
   * Indício objetivo de perda ou falência/recuperação judicial comunicada.

2. **Estágio 2 (Aumento Significativo de Risco de Crédito - SICR):** Uma operação **não enquadrada no Estágio 3** é classificada em Estágio 2 se atender a **pelo menos um** dos seguintes critérios:
   * Atraso entre 31 e 90 dias (`dias_atraso BETWEEN 31 AND 90`);
   * Aumento relativo de PD superior a $250\%$ em relação à concessão ($\frac{PD_{\text{atual}}}{PD_{\text{origem}}} \ge 2.5$);
   * Rebaixamento de rating interno comportamental superior ou igual a 2 níveis desde a concessão ($\Delta \text{Rating} \ge 2$).

3. **Estágio 1 (Risco Inicial / Sem SICR):** Todas as operações adimplentes ou com atraso menor ou igual a 30 dias que não apresentem aumento significativo de risco de crédito.

### 4.2 Indicador de Ativo Problemático (AP)
O campo `indicador_ativo_problematico` é binário ($1$ ou $0$):
$$\text{indicador\_ativo\_problematico} = 1 \iff \text{estagio\_contabil} = 3$$

### 4.3 Cálculo da Perda Esperada Regulamentar (ECL)
* **Para Estágio 1:** Perda esperada calculada para o horizonte de 12 meses:
  $$ECL_{12M} = \text{Saldo\_Devedor\_Contabil} \times \text{PD}_{12M} \times \text{LGD}$$
* **Para Estágio 2 e 3:** Perda esperada calculada para toda a vida útil remanescente da operação (*Lifetime*):
  $$ECL_{\text{Lifetime}} = \text{Saldo\_Devedor\_Contabil} \times \text{PD}_{\text{Lifetime}} \times \text{LGD}$$

---

## 5. Medidas de Negócio e Fórmulas Analíticas (SQL Canônico e Python)

Todas as métricas descritas a seguir devem ser calculadas no motor DuckDB e exportadas para o arquivo estático de visualização `dashboard_data.json`.

### 5.1 Métricas de Carteira e Risco Estrutural

#### A. Saldo da Carteira Ativa
* **Conceito:** Volume financeiro total das operações de crédito ativas na data-base.
* **SQL (DuckDB):**
  ```sql
  SELECT SUM(saldo_devedor_contabil) AS carteira_ativa
  FROM f_Carteira_Mensal
  WHERE data_fechamento = :data_base;
  ```

#### B. Estoque de Ativo Problemático (AP)
* **Conceito:** Soma do saldo devedor de todos os contratos com indicador de AP ativo.
* **SQL (DuckDB):**
  ```sql
  SELECT SUM(saldo_devedor_contabil) AS saldo_ativo_problematico
  FROM f_Carteira_Mensal
  WHERE data_fechamento = :data_base AND indicador_ativo_problematico = 1;
  ```

#### C. Taxa de Ativo Problemático ($AP\%$)
* **Conceito:** Proporção do saldo de AP em relação à carteira total.
* **SQL (DuckDB):**
  ```sql
  SELECT 
      ROUND(
          SUM(CASE WHEN indicador_ativo_problematico = 1 THEN saldo_devedor_contabil ELSE 0 END) / 
          NULLIF(SUM(saldo_devedor_contabil), 0) * 100, 
          2
      ) AS percentual_ativo_problematico
  FROM f_Carteira_Mensal
  WHERE data_fechamento = :data_base;
  ```

#### D. Taxa de Provisão Constituída ($Prov\%$)
* **Conceito:** Razão entre o estoque contábil de provisão (PDD) e a carteira ativa total.
* **SQL (DuckDB):**
  ```sql
  SELECT 
      ROUND(
          SUM(saldo_provisao_constituida) / 
          NULLIF(SUM(saldo_devedor_contabil), 0) * 100, 
          2
      ) AS percentual_provisao_constituida
  FROM f_Carteira_Mensal
  WHERE data_fechamento = :data_base;
  ```

#### E. Diferencial de Cobertura de AP (Gap)
* **Conceito:** $Prov\% - AP\%$. Quando negativo, alerta que a provisão constituída não cobre o volume total de ativos em estresse.
* **Python:**
  ```python
  gap_cobertura = percentual_provisao_constituida - percentual_ativo_problematico
  ```

---

### 5.2 Decomposição do Ativo Problemático e Inadimplência

#### A. Saldo e Taxa Over90 (Inadimplência Efetiva $> 90$ dias)
* **SQL (DuckDB):**
  ```sql
  SELECT 
      SUM(CASE WHEN dias_atraso > 90 THEN saldo_devedor_contabil ELSE 0 END) AS saldo_over90,
      ROUND(
          SUM(CASE WHEN dias_atraso > 90 THEN saldo_devedor_contabil ELSE 0 END) / 
          NULLIF(SUM(saldo_devedor_contabil), 0) * 100, 
          2
      ) AS taxa_inadimplencia_over90
  FROM f_Carteira_Mensal
  WHERE data_fechamento = :data_base;
  ```

#### B. Proporção do Over90 dentro do Ativo Problemático
* **Conceito:** Parcela do AP composta por inadimplência clássica prolongada versus renegociações e critérios preventivos.
* **SQL (DuckDB):**
  ```sql
  SELECT 
      ROUND(
          SUM(CASE WHEN dias_atraso > 90 THEN saldo_devedor_contabil ELSE 0 END) / 
          NULLIF(SUM(CASE WHEN indicador_ativo_problematico = 1 THEN saldo_devedor_contabil ELSE 0 END), 0) * 100, 
          2
      ) AS percentual_over90_no_ap
  FROM f_Carteira_Mensal
  WHERE data_fechamento = :data_base;
  ```

#### C. Distribuição da Carteira por Estágios da Resolução 4.966
* **SQL (DuckDB):**
  ```sql
  SELECT 
      estagio_contabil,
      SUM(saldo_devedor_contabil) AS saldo_estagio,
      ROUND(SUM(saldo_devedor_contabil) / NULLIF((SELECT SUM(saldo_devedor_contabil) FROM f_Carteira_Mensal WHERE data_fechamento = :data_base), 0) * 100, 2) AS percentual_estagio
  FROM f_Carteira_Mensal
  WHERE data_fechamento = :data_base
  GROUP BY estagio_contabil
  ORDER BY estagio_contabil;
  ```

---

### 5.3 Métricas de Custo de Crédito e Impacto no Capital

#### A. Custo de Provisão em 12 Meses (*Cost of Risk* - CoR 12M%)
* **Conceito:** Despesa líquida de provisão acumulada nos últimos 12 meses dividida pela carteira média do mesmo período.
* **SQL (DuckDB sobre `f_DRE_Gerencial`):**
  ```sql
  WITH dre_acumulado AS (
      SELECT 
          data_fechamento,
          despesa_liquida_pdd_mes,
          saldo_carteira_total,
          SUM(despesa_liquida_pdd_mes) OVER (
              ORDER BY data_fechamento 
              ROWS BETWEEN 11 PRECEDING AND CURRENT ROW
          ) AS despesa_pdd_12m,
          AVG(saldo_carteira_total) OVER (
              ORDER BY data_fechamento 
              ROWS BETWEEN 11 PRECEDING AND CURRENT ROW
          ) AS media_carteira_12m
      FROM f_DRE_Gerencial
  )
  SELECT 
      data_fechamento,
      despesa_pdd_12m,
      media_carteira_12m,
      ROUND((despesa_pdd_12m / NULLIF(media_carteira_12m, 0)) * 100, 2) AS percentual_custo_provisao_12m
  FROM dre_acumulado
  ORDER BY data_fechamento;
  ```

#### B. Índice de Cobertura da Perda Esperada Estimada (Benchmarking REF)
* **Conceito:** Razão entre a Provisão Constituída e o somatório de Perda Esperada ($EAD \times PD \times LGD$).
* **SQL (DuckDB):**
  ```sql
  SELECT 
      ROUND(
          SUM(saldo_provisao_constituida) / 
          NULLIF(SUM(saldo_devedor_contabil * probabilidade_default_pd * loss_given_default_lgd), 0), 
          4
      ) AS indice_cobertura_ecl
  FROM f_Carteira_Mensal
  WHERE data_fechamento = :data_base;
  ```

---

## 6. Layout e Storytelling do Painel C-Level (HTML5 / CSS3 / Vanilla JS)

O painel deve ser entregue como uma aplicação web nativa leve contida no diretório `src/dashboard/`:
* `index.html`: Estrutura semântica das 3 visões executivas.
* `styles.css`: Estilização corporativa sóbria (paleta escura bancária, design tokens, tipografia nativa Inter/Segoe UI, layouts CSS Grid e Flexbox responsivos).
* `app.js`: Script Vanilla moderno para carregamento assíncrono do arquivo compilado `data/dashboard_data.json`, manipulação dinâmica dos cards e renderização de gráficos via Chart.js.

### 6.1 Tela 1: Posicionamento Estratégico e Benchmarking (O Post Executivo)
* **KPI Header Cards:**
  1. `% Ativo Problemático` (com tag de status vs. média SNCC).
  2. `% Provisão Constituída` (com indicador visual de gap de cobertura).
  3. `% Custo de Provisão 12M (CoR)`.
  4. `% Over90 no Ativo Problemático`.
* **Gráfico Central:** Gráfico temporal de linhas comparando:
  * Taxa de AP da Cooperativa Singular.
  * Taxa de Provisão Constituída da Cooperativa Singular.
  * Taxa de AP do SNCC (IF.data Bacen).
  * **Anotação Dinâmica:** Ponto exato da data em que a linha de Provisão cruzou abaixo da linha de AP.
* **Régua de Cobertura vs. REF:** Gráfico de barra ou bullet chart comparando o índice de cobertura da singular com SNCC ($1,03\text{x}$) e SFN ($0,98\text{x}$).

### 6.2 Tela 2: Anatomia do Risco e Antecipação (Resolução 4.966)
* **Evolução de Estágios:** Gráfico de barras empilhadas / área temporal exibindo a transição de saldos entre Estágio 1, Estágio 2 (alerta precoce) e Estágio 3.
* **Quebra da Origem do AP:** Gráfico de rosca categorizando:
  * Atraso Prolongado ($> 90$ dias).
  * Renegociações por Estresse Financeiro (*Forbearance*).
  * Deterioração de Rating e Alertas Preventivos (SICR).
* **Dispersão por Linha de Crédito:** Scatter Plot de Crescimento da Carteira 12M versus Custo de Provisão 12M por modalidade.

### 6.3 Tela 3: Curvas de Safra (Vintages) e Simulador de Capital
* **Matriz de Safras (Vintage por MOB):** Gráfico de linhas com curvas de maturação por safra de concessão ($1, 3, 6, 12, 24$ meses).
* **Simulador Interativo What-If de Capital (Vanilla JS):**
  * Slider de sensibilidade com ajuste dinâmico de $+0.5\%$ a $+3.0\%$ de estresse no Ativo Problemático.
  * Recálculo instantâneo em JavaScript do impacto financeiro nas Sobras do Exercício e no Índice de Basileia / Consumo de Patrimônio de Referência.

---

## 7. Módulo de Geração de Dados Sintéticos e Validação Contábil

Para assegurar testes determinísticos e reprodução auditável sem violar sigilo bancário:
1. **Script de Geração:** `src/ingestion/synthetic_generator.py` gerará uma base histórica completa (24 meses) com semente aleatória reproduzível (`seed=42`).
2. **Conciliação Estrita:** O gerador deve garantir matematicamente que para toda competência $t$:
   $$\sum \text{Saldo\_Devedor\_Contabil} = \text{f\_DRE\_Gerencial.Saldo\_Carteira\_Total}$$
   $$\sum \text{Saldo\_Provisao\_Constituida} = \text{f\_DRE\_Gerencial.Despesa\_Acumulada\_PDD}$$
3. **Casos de Teste Limítrofes Inclusos:** O conjunto sintético deve obrigatoriamente incluir contratos com:
   * Atraso de 35 dias com rebaixamento de rating (teste de Estágio 2);
   * Operação renegociada com 0 dias de atraso (teste de Estágio 3 / AP);
   * Operação com 95 dias de atraso (teste de Estágio 3 e Over90).

---

## 8. Roteiro de Implementação e Entregáveis

| Fase | Entregável Técnico | Stack / Ferramenta | Critério de Aceite Automatizado |
| :--- | :--- | :--- | :--- |
| **Fase 1: Ingestão e Validação** | Conectores IF.data, REF e gerador sintético determinístico com Schemas Pydantic. | Python 3.12, Pydantic V2, `uv` | `uv run pytest tests/test_ingestion.py` com 100% de sucesso. |
| **Fase 2: Classificação 4.966** | Motor de enquadramento em Estágios 1, 2 e 3 e cálculo de AP e ECL. | DuckDB, Polars/Pandas | `uv run pytest tests/test_staging.py` cobrindo todas as regras da Res. 4.966. |
| **Fase 3: Métricas e Agregação** | Pipeline de cálculo de CoR 12M, Vintages e exportação de `dashboard_data.json`. | DuckDB, Python | `uv run pytest tests/test_analytics.py` e conferência de conciliação contábil. |
| **Fase 4: Frontend C-Level** | Dashboard executivo com as 3 telas estratégicas, storytelling e simulador What-If. | HTML5, CSS3 puro, Vanilla JS, Chart.js | Interface abre localmente sem erros de console e os dados batem com o JSON compilado. |
