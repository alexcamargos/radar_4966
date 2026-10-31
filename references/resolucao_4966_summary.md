# Resumo Executivo: Resolução CMN nº 4.966 / IFRS 9 e Resolução BCB nº 352

## 1. Mudança de Paradigma: Perda Incorrida vs. Perda Esperada

* **Antiga Resolução CMN nº 2.682 (Perda Incorrida):**
  Provisionamento calendarizado baseado em faixas mecânicas de atraso ($15$ a $180$ dias) e níveis de risco de AA a H. A despesa de provisão só era reconhecida ex-post, quando o associado já havia entrado em inadimplência material.
* **Resolução CMN nº 4.966 / IFRS 9 (Perda Esperada - ECL):**
  Reconhecimento contábil prospectivo (*forward-looking*) de perdas esperadas desde o momento da originação do crédito. O custo de provisão antecede a inadimplência efetiva superior a 90 dias, reagindo precocemente ao aumento significativo de risco de crédito (*SICR*).

---

## 2. Enquadramento Determinístico em Estágios

### Estágio 1: Risco Inicial e Sem Degradação Relevante
* **Critério:** Operações adimplentes ou com atraso menor ou igual a 30 dias que não apresentem aumento significativo de risco.
* **Horizonte de Perda Esperada:** Provisão calculada para o horizonte de **12 meses**:
  $$ECL_{12M} = \text{Saldo\_Devedor\_Contabil} \times \text{PD}_{12M} \times \text{LGD}$$

### Estágio 2: Aumento Significativo de Risco de Crédito (SICR)
* **Critério:** Operações não inadimplentes prolongadas, mas que atendam a pelo menos uma das condições:
  1. Atraso entre 31 e 90 dias ($31 \le \text{DPD} \le 90$);
  2. Degradação de rating comportamental interno $\ge 2$ níveis em relação à originação ($\Delta \text{Rating} \ge 2$);
  3. Deterioração de risco com $\frac{\text{PD}_{\text{atual}}}{\text{PD}_{\text{origem}}} \ge 2,5$ ($+250\%$).
* **Horizonte de Perda Esperada:** Provisão calculada para **toda a vida útil remanescente da operação (*Lifetime*)**:
  $$ECL_{\text{Lifetime}} = \text{Saldo\_Devedor\_Contabil} \times \text{PD}_{\text{Lifetime}} \times \text{LGD}$$

### Estágio 3: Ativo Problemático (AP / Default)
* **Critério:** Operações com indício substancial de perda, atendendo a qualquer um dos requisitos:
  1. Atraso superior a 90 dias ($\text{DPD} > 90$);
  2. Operação renegociada/reestruturada por estresse financeiro (*forbearance*);
  3. Rating interno deteriorado no nível máximo ($10$);
  4. Indício objetivo de perda, insolvência civil ou recuperação judicial/falência.
* **Equivalência Regulatória:**
  $$\text{Indicador\_Ativo\_Problematico} = 1 \iff \text{Estagio\_Contabil} = 3$$
* **Horizonte de Perda Esperada:** Provisão calculada para a vida remanescente (*Lifetime*).

---

## 3. Fórmulas Canônicas de Gestão e Monitoramento C-Level

### Custo de Crédito Móvel em 12 Meses (*Cost of Risk* - CoR 12M%)
Mede a eficiência e o custo real de risco absorvido pelo resultado da cooperativa:
$$\text{CoR}_{12M} = \frac{\sum_{t-11}^t \text{Despesa\_Liquida\_PDD}_i}{\frac{1}{12} \sum_{t-11}^t \text{Carteira\_Total}_i} \times 100$$

### Gap de Cobertura de Ativos Problemáticos
Indica se o estoque de provisão constituída é suficiente para cobrir os créditos com estresse severo:
$$\text{Gap} = \text{Taxa\_Provisao}\% - \text{Taxa\_AP}\%$$
* $\text{Gap} < 0$: Provisão inferior ao volume de AP (alerta imediato de subprovisionamento e risco de capital).
* $\text{Gap} \ge 0$: Provisão cobre integralmente o Ativo Problemático.

### Proporção do Over90 no Ativo Problemático
Segmenta a composição do AP entre atraso prolongado e antecipação prudencial:
$$\% \text{Over90 no AP} = \frac{\sum \text{Saldo vencido há mais de 90 dias}}{\sum \text{Saldo do Ativo Problemático}} \times 100$$
