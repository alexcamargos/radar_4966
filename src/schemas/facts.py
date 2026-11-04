"""Esquemas formais Pydantic V2 para tabelas de fatos internos e externos.

Implementa os modelos de validação para a carteira de operações mensais,
balancete/DRE gerencial, indicadores agregados do IF.data e REF do Bacen.
"""

from datetime import date
from decimal import Decimal
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class SegmentoIFDataEnum(StrEnum):
    """Segmentos de análise no portal IF.data do Banco Central.

    Attributes:
        COOPERATIVAS_SINGULARES: Cooperativas de crédito singulares.
        SNCC_CONSOLIDADO: Sistema Nacional de Crédito Cooperativo agregado.
        SFN_TOTAL: Sistema Financeiro Nacional consolidado.
        SICOOB_CREDIJEQUITINHONHA: Cooperativa de Crédito Credijequitinhonha Ltda. (Sicoob).
    """

    COOPERATIVAS_SINGULARES = "Cooperativas Singulares"
    SNCC_CONSOLIDADO = "SNCC Consolidado"
    SFN_TOTAL = "SFN Total"
    SICOOB_CREDIJEQUITINHONHA = "Sicoob Credijequitinhonha"


class SegmentoREFEnum(StrEnum):
    """Segmentos reportados no Relatório de Estabilidade Financeira (REF) do Bacen.

    Attributes:
        SNCC: Sistema Nacional de Crédito Cooperativo.
        SFN: Sistema Financeiro Nacional.
    """

    SNCC = "SNCC"
    SFN = "SFN"


class FatoCarteiraMensalSchema(BaseModel):
    """Schema da carteira analítica individual por operação de crédito.

    Attributes:
        data_fechamento: Último dia do mês contábil da competência (FK).
        id_contrato: Identificador unívoco do contrato de crédito.
        id_associado: Chave de relacionamento com a dimensão cooperado.
        id_linha: Chave de relacionamento com a linha de crédito.
        data_concessao: Data de contratação e liberação dos recursos.
        saldo_devedor_contabil: Saldo contábil da dívida em precisão fixa.
        dias_atraso: Quantidade de dias em atraso (Days Past Due).
        saldo_vencido_over90: Saldo vencido com atraso superior a 90 dias.
        indicador_renegociacao: Indicador binário de renegociação por estresse (1 ou 0).
        indicador_ativo_problematico: Indicador binário de Ativo Problemático (1 ou 0).
        estagio_contabil: Estágio de risco conforme Resolução CMN 4.966 (1, 2 ou 3).
        probabilidade_default_pd: Probabilidade de inadimplemento calculada.
        loss_given_default_lgd: Percentual de perda dado o descumprimento.
        saldo_provisao_constituida: Volume monetário de provisão provisionada.
    """

    model_config = ConfigDict(strict=True)

    data_fechamento: date = Field(..., description="Último dia do mês contábil (FK)")
    id_contrato: int = Field(..., ge=1, description="Identificador do contrato (PK Composta)")
    id_associado: int = Field(..., ge=1, description="FK para d_Associado")
    id_linha: int = Field(..., ge=1, description="FK para d_LinhaCredito")
    data_concessao: date = Field(..., description="Data da contratação/liberação da operação")
    saldo_devedor_contabil: Decimal = Field(
        ...,
        max_digits=18,
        decimal_places=2,
        ge=Decimal("0.00"),
    )
    dias_atraso: int = Field(..., ge=0, description="Dias de atraso (DPD - Days Past Due)")
    saldo_vencido_over90: Decimal = Field(
        ...,
        max_digits=18,
        decimal_places=2,
        ge=Decimal("0.00"),
    )
    indicador_renegociacao: int = Field(
        ...,
        ge=0,
        le=1,
        description="1 se renegociado por estresse financeiro, 0 cc",
    )
    indicador_ativo_problematico: int = Field(
        ...,
        ge=0,
        le=1,
        description="1 se AP conforme Res. 4.966, 0 cc",
    )
    estagio_contabil: int = Field(..., ge=1, le=3, description="Estágio Res. 4.966 (1, 2 ou 3)")
    probabilidade_default_pd: Decimal = Field(
        ...,
        max_digits=6,
        decimal_places=4,
        ge=Decimal("0.0000"),
        le=Decimal("1.0000"),
    )
    loss_given_default_lgd: Decimal = Field(
        ...,
        max_digits=6,
        decimal_places=4,
        ge=Decimal("0.0000"),
        le=Decimal("1.0000"),
    )
    saldo_provisao_constituida: Decimal = Field(
        ...,
        max_digits=18,
        decimal_places=2,
        ge=Decimal("0.00"),
    )


class FatoDREGerencialSchema(BaseModel):
    """Schema do balancete e DRE gerencial mensal da cooperativa singular.

    Attributes:
        data_fechamento: Data do fechamento contábil mensal (PK).
        despesa_pdd_mes: Despesa bruta de provisão para créditos de liquidação duvidosa.
        recuperacao_credito_mes: Receitas auferidas com recuperação de créditos baixados.
        despesa_liquida_pdd_mes: Despesa líquida de provisão (PDD líquida).
        saldo_carteira_total: Saldo contábil total da carteira classificada.
        sobras_liquidas_exercicio: Resultado financeiro acumulado da cooperativa.
        patrimonio_referencia_pr: Patrimônio de Referência para fins de capital.
        rwa_risco_credito: Ativos ponderados pelo risco de crédito.
    """

    model_config = ConfigDict(strict=True)

    data_fechamento: date = Field(..., description="Data do fechamento contábil mensal (PK)")
    despesa_pdd_mes: Decimal = Field(..., max_digits=18, decimal_places=2, ge=Decimal("0.00"))
    recuperacao_credito_mes: Decimal = Field(
        ...,
        max_digits=18,
        decimal_places=2,
        ge=Decimal("0.00"),
    )
    despesa_liquida_pdd_mes: Decimal = Field(..., max_digits=18, decimal_places=2)
    saldo_carteira_total: Decimal = Field(
        ...,
        max_digits=18,
        decimal_places=2,
        ge=Decimal("0.00"),
    )
    sobras_liquidas_exercicio: Decimal = Field(..., max_digits=18, decimal_places=2)
    patrimonio_referencia_pr: Decimal = Field(
        ...,
        max_digits=18,
        decimal_places=2,
        ge=Decimal("0.00"),
    )
    rwa_risco_credito: Decimal = Field(..., max_digits=18, decimal_places=2, ge=Decimal("0.00"))


class FatoIFDataSNCCSchema(BaseModel):
    """Schema para dados agregados do portal IF.data do Banco Central.

    Attributes:
        data_trimestre: Data do término do trimestre civil de referência.
        segmento_analise: Categoria de consolidação institucional.
        carteira_total_bacen: Saldo da carteira informada no balancete Bacen.
        provisao_total_bacen: Estoque contábil de provisão agregada.
        ativo_problematico_bacen: Saldo agregado enquadrado como Ativo Problemático.
        ap_over90_bacen: Parcela do Ativo Problemático com atraso acima de 90 dias.
        percentual_ap_ifdata: Razão percentual de AP sobre a carteira.
        percentual_provisao_ifdata: Razão percentual de provisão sobre a carteira.
    """

    model_config = ConfigDict(strict=True)

    data_trimestre: date = Field(..., description="Fim do trimestre de referência")
    segmento_analise: SegmentoIFDataEnum
    carteira_total_bacen: Decimal = Field(
        ...,
        max_digits=18,
        decimal_places=2,
        ge=Decimal("0.00"),
    )
    provisao_total_bacen: Decimal = Field(
        ...,
        max_digits=18,
        decimal_places=2,
        ge=Decimal("0.00"),
    )
    ativo_problematico_bacen: Decimal = Field(
        ...,
        max_digits=18,
        decimal_places=2,
        ge=Decimal("0.00"),
    )
    ap_over90_bacen: Decimal = Field(..., max_digits=18, decimal_places=2, ge=Decimal("0.00"))
    percentual_ap_ifdata: Decimal = Field(
        ...,
        max_digits=6,
        decimal_places=4,
        ge=Decimal("0.0000"),
        le=Decimal("1.0000"),
    )
    percentual_provisao_ifdata: Decimal = Field(
        ...,
        max_digits=6,
        decimal_places=4,
        ge=Decimal("0.0000"),
        le=Decimal("1.0000"),
    )


class FatoREFMacroBCBSchema(BaseModel):
    """Schema para dados do Relatório de Estabilidade Financeira (REF) do Bacen.

    Attributes:
        data_semestre: Data final do semestre de referência do relatório.
        segmento: Segmento macroprudencial avaliado (SNCC ou SFN).
        taxa_perda_esperada_estimada: Taxa média de perda esperada modelada pelo Bacen.
        indice_cobertura_perda_esperada: Relação entre provisão e perda esperada.
        custo_credito_12m_percentual: Custo do crédito acumulado nos últimos 12 meses.
    """

    model_config = ConfigDict(strict=True)

    data_semestre: date = Field(..., description="Fim do semestre de referência")
    segmento: SegmentoREFEnum
    taxa_perda_esperada_estimada: Decimal = Field(
        ...,
        max_digits=6,
        decimal_places=4,
        ge=Decimal("0.0000"),
        le=Decimal("1.0000"),
    )
    indice_cobertura_perda_esperada: Decimal = Field(
        ...,
        max_digits=6,
        decimal_places=4,
        ge=Decimal("0.0000"),
    )
    custo_credito_12m_percentual: Decimal = Field(
        ...,
        max_digits=6,
        decimal_places=4,
        ge=Decimal("0.0000"),
        le=Decimal("1.0000"),
    )


class PontoSerieQuebraSNCCSchema(BaseModel):
    """Ponto mensal da série de Ativo Problemático do SNCC com quebra estrutural.

    Attributes:
        mes_ano: Competência formatada em mês/ano (ex.: 'dez/22', 'jan/25').
        data_competencia: Data correspondente ao fechamento mensal.
        taxa_ap_sncc: Percentual do Ativo Problemático sobre a carteira total.
        regime_normativo: Regime contábil de apuração ('Res. 2.682' ou 'Res. 4.966').
        marco_quebra: Indicador booleano de transição da norma (True para jan/25).
        destaque_rotulo: Rótulo textual destacado nos marcos principais do gráfico.
    """

    model_config = ConfigDict(strict=True)

    mes_ano: str = Field(..., description="Competência no formato mês/ano")
    data_competencia: date = Field(..., description="Data contábil mensal")
    taxa_ap_sncc: Decimal = Field(
        ...,
        max_digits=5,
        decimal_places=2,
        ge=Decimal("0.00"),
        le=Decimal("100.00"),
        description="Taxa de AP em percentual (ex: 4.07 para 4,07%)",
    )
    regime_normativo: str = Field(..., description="Norma regulatória de referência")
    marco_quebra: bool = Field(
        default=False,
        description="Indica se é o ponto de corte da mudança regulatória em Jan/2025",
    )
    destaque_rotulo: str | None = Field(
        default=None,
        description="Texto do valor destacado nas datas-chave (ex.: '4,07%')",
    )


class CustoProvisaoBenchmarkSchema(BaseModel):
    """Métrica de Custo de Provisão acumulado em 12 meses (Cost of Risk - CoR).

    Attributes:
        periodo_referencia: Descrição do período de referência (ex: '12 meses até dez/24').
        custo_provisao_pct: Percentual anualizado do custo de provisão em 12 meses.
        regime_normativo: Classificação do regime normativo do ciclo.
        descricao: Resumo analítico do comportamento do indicador.
    """

    model_config = ConfigDict(strict=True)

    periodo_referencia: str = Field(..., description="Identificador do horizonte temporal")
    custo_provisao_pct: Decimal = Field(
        ...,
        max_digits=5,
        decimal_places=2,
        ge=Decimal("0.00"),
        le=Decimal("100.00"),
        description="Percentual de custo de crédito (ex.: 4.20 para 4,2%)",
    )
    regime_normativo: str = Field(..., description="Regime contábil aplicável")
    descricao: str = Field(..., description="Contexto analítico do indicador")


class EstudoQuebra4966SNCCSchema(BaseModel):
    """Estudo regulatório de impacto e quebra estrutural da Resolução CMN 4.966 no SNCC.

    Attributes:
        titulo: Título da análise executiva.
        subtitulo: Subtítulo descritivo com a tese central.
        serie_mensal_ap: Lista ordenada cronologicamente dos pontos mensais de AP.
        custos_provisao_periodos: Lista com os 3 períodos de CoR 12M do REF Bacen.
        frase_sintese: Declaração executiva de conclusão sobre risco de carteira.
        nota_metodologica: Esclarecimento técnico sobre a descontinuidade em jan/25.
        fonte: Citação oficial do Banco Central do Brasil.
    """

    model_config = ConfigDict(strict=True)

    titulo: str = Field(..., description="Título da investigação executiva")
    subtitulo: str = Field(..., description="Tese da taxa de subida anual prévia")
    serie_mensal_ap: list[PontoSerieQuebraSNCCSchema] = Field(
        ..., description="Série temporal mensal de AP"
    )
    custos_provisao_periodos: list[CustoProvisaoBenchmarkSchema] = Field(
        ..., description="Cards de benchmark de custo de provisão em 12 meses"
    )
    frase_sintese: str = Field(..., description="Conclusão executiva de síntese")
    nota_metodologica: str = Field(..., description="Detalhes sobre a quebra de série em jan/25")
    fonte: str = Field(..., description="Fonte primária oficial dos dados")
