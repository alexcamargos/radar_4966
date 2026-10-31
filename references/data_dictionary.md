# Dicionário de Dados e Catálogo de Entidades (Radar 4966)

Este documento especifica o catálogo canônico de dados analíticos do projeto **Radar 4966**, estruturado conforme o esquema estrela (*Star Schema*) e alinhado aos padrões da **Resolução CMN nº 4.966 / IFRS 9** e **Resolução BCB nº 352**.

---

## 1. Esquema Relacional Estrela (*Star Schema*)

```text
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

## 2. Tabelas de Dimensão

### 2.1 `d_Calendario` (Dimensão Temporal Mensal)
Armazena as datas de fechamento mensal para agregação contábil e séries temporais.

| Atributo | Tipo de Dado | Chave | Restrições / Domínio | Descrição |
| :--- | :--- | :--- | :--- | :--- |
| `data` | `date` | PK | Último dia de cada mês (2020 a 2026) | Data de fechamento da competência contábil mensal. |
| `ano` | `int` | | $2000 \le \text{ano} \le 2100$ | Ano civil da competência (AAAA). |
| `mes_ano` | `string` | | Regex: `^(Jan\|Fev\|...\|Dez)/\d{4}$` | Representação textual amigável (ex.: `Jun/2025`). |
| `trimestre` | `string` | | `1T`, `2T`, `3T`, `4T` | Trimestre civil de referência. |

### 2.2 `d_Associado` (Dimensão de Cooperados)
Registra o perfil cadastral e rating comportamental dos membros da cooperativa.

| Atributo | Tipo de Dado | Chave | Restrições / Domínio | Descrição |
| :--- | :--- | :--- | :--- | :--- |
| `id_associado` | `int` | PK | $\ge 1$ (anonimizado) | Identificador único do associado na cooperativa. |
| `tipo_pessoa` | `string` | | `PF`, `PJ` | Natureza jurídica do associado. |
| `segmento_cooperado` | `string` | | `Agro`, `Comercial`, `Varejo`, `Servidor Publico`, `Outros` | Segmento operacional do associado. |
| `data_admissao` | `date` | | Data válida $\le$ data de fechamento | Data de ingresso do associado na cooperativa. |
| `rating_interno_comportamental` | `int` | | $1 \le \text{rating} \le 10$ | Score comportamental interno ($1$ melhor risco, $10$ default). |

### 2.3 `d_LinhaCredito` (Dimensão de Linhas e Modalidades)
Categorização das operações de crédito segundo taxonomia Bacen.

| Atributo | Tipo de Dado | Chave | Restrições / Domínio | Descrição |
| :--- | :--- | :--- | :--- | :--- |
| `id_linha` | `int` | PK | $\ge 1$ | Código identificador da linha de crédito. |
| `nome_linha` | `string` | | 3 a 100 caracteres | Nome comercial da linha operacional. |
| `grupo_modalidade` | `string` | | `Credito Rural`, `Capital de Giro`, `Consumo`, `Habitacional` | Segmentação regulatória Bacen. |
| `tipo_garantia_predominante` | `string` | | `Fidejussoria`, `Alienacao Fiduciaria`, `Penhor Agricola`, `Limpa` | Natureza do colateral principal. |

---

## 3. Tabelas Fato Internas (Cooperativa Singular)

### 3.1 `f_Carteira_Mensal` (Operações Analíticas por Contrato)
Grão por contrato individual em cada competência contábil mensal.

| Atributo | Tipo de Dado | Chave | Restrições / Domínio | Descrição |
| :--- | :--- | :--- | :--- | :--- |
| `data_fechamento` | `date` | PK (Composta), FK | Referência para `d_Calendario.data` | Data-base de encerramento do mês contábil. |
| `id_contrato` | `int` | PK (Composta) | $\ge 1$ | Identificador unívoco do contrato de crédito. |
| `id_associado` | `int` | FK | Referência para `d_Associado.id_associado` | Código do associado tomador. |
| `id_linha` | `int` | FK | Referência para `d_LinhaCredito.id_linha` | Linha/modalidade de crédito contratada. |
| `data_concessao` | `date` | | $\le \text{data\_fechamento}$ | Data de contratação e liberação dos recursos. |
| `saldo_devedor_contabil` | `Decimal(18,2)` | | $\ge 0.00$ | Saldo devedor principal + encargos na data-base. |
| `dias_atraso` | `int` | | $\ge 0$ | Dias decorridos desde o vencimento da obrigação mais antiga. |
| `saldo_vencido_over90` | `Decimal(18,2)` | | $\ge 0.00$ | Saldo vencido há mais de 90 dias (inadimplência clássica). |
| `indicador_renegociacao` | `int` | | $0$ ou $1$ | $1$ se renegociado por estresse (*forbearance*), $0$ cc. |
| `indicador_ativo_problematico` | `int` | | $0$ ou $1$ | $1$ se Ativo Problemático (Resolução CMN 4.966), $0$ cc. |
| `estagio_contabil` | `int` | | $1$, $2$ ou $3$ | Estágio de risco de crédito (Res. 4.966 / IFRS 9). |
| `probabilidade_default_pd` | `Decimal(6,4)` | | $0.0000 \le \text{PD} \le 1.0000$ | Probabilidade de inadimplemento estimada. |
| `loss_given_default_lgd` | `Decimal(6,4)` | | $0.0000 \le \text{LGD} \le 1.0000$ | Severidade da perda em caso de default. |
| `saldo_provisao_constituida` | `Decimal(18,2)` | | $\ge 0.00$ | Provisão para perdas esperadas constituída. |

### 3.2 `f_DRE_Gerencial` (Balancete e Resultados Mensais)
Demonstrativo contábil mensal e parâmetros de capital regulatório.

| Atributo | Tipo de Dado | Chave | Restrições / Domínio | Descrição |
| :--- | :--- | :--- | :--- | :--- |
| `data_fechamento` | `date` | PK, FK | Referência para `d_Calendario.data` | Data do encerramento contábil da competência. |
| `despesa_pdd_mes` | `Decimal(18,2)` | | $\ge 0.00$ | Despesa bruta de provisão de crédito no mês. |
| `recuperacao_credito_mes` | `Decimal(18,2)` | | $\ge 0.00$ | Receitas com recuperação de créditos baixados. |
| `despesa_liquida_pdd_mes` | `Decimal(18,2)` | | $\text{despesa\_pdd} - \text{recuperacao}$ | Despesa líquida de provisão (impacto no resultado). |
| `saldo_carteira_total` | `Decimal(18,2)` | | $\ge 0.00$ | Saldo total da carteira classificada no balanço. |
| `sobras_liquidas_exercicio` | `Decimal(18,2)` | | Livre | Resultado contábil acumulado no exercício social. |
| `patrimonio_referencia_pr` | `Decimal(18,2)` | | $\ge 0.00$ | Capital regulatório apurado para fins de Basileia. |
| `rwa_risco_credito` | `Decimal(18,2)` | | $\ge 0.00$ | Ativos ponderados pelo risco de crédito. |

---

## 4. Tabelas Fato Externas (Banco Central do Brasil)

### 4.1 `f_IFData_SNCC` (Portal IF.data Bacen - Trimestral)
| Atributo | Tipo de Dado | Descrição |
| :--- | :--- | :--- |
| `data_trimestre` | `date` | Fim do trimestre civil de referência. |
| `segmento_analise` | `string` | `Cooperativas Singulares`, `SNCC Consolidado`, `SFN Total`. |
| `carteira_total_bacen` | `Decimal(18,2)` | Saldo agregado da carteira de crédito. |
| `provisao_total_bacen` | `Decimal(18,2)` | Estoque agregado de provisão constituída. |
| `ativo_problematico_bacen`| `Decimal(18,2)` | Saldo agregado de Ativos Problemáticos. |
| `ap_over90_bacen` | `Decimal(18,2)` | Parcela do AP com atraso superior a 90 dias. |
| `percentual_ap_ifdata` | `Decimal(6,4)` | Taxa agregada de AP ($\%$). |
| `percentual_provisao_ifdata`| `Decimal(6,4)` | Taxa agregada de Provisão ($\%$). |

### 4.2 `f_REF_Macro_BCB` (Relatório de Estabilidade Financeira - Semestral)
| Atributo | Tipo de Dado | Descrição |
| :--- | :--- | :--- |
| `data_semestre` | `date` | Fim do semestre de referência. |
| `segmento` | `string` | `SNCC` ou `SFN`. |
| `taxa_perda_esperada_estimada` | `Decimal(6,4)` | Taxa média de perda esperada modelada pelo Bacen. |
| `indice_cobertura_perda_esperada` | `Decimal(6,4)` | Razão entre provisão constituída e perda esperada estimada. |
| `custo_credito_12m_percentual` | `Decimal(6,4)` | Custo de crédito médio semestral em 12 meses. |
