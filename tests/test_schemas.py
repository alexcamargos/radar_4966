"""Testes unitários automatizados para os esquemas Pydantic V2 de dados.

Valida conformidade das restrições de tipos, limites numéricos,
padrões regex e obrigatoriedade de campos nas tabelas dimensão e fato.
"""

from datetime import date
from decimal import Decimal

import pytest
from pydantic import ValidationError

from src.schemas.dimensions import (
    DimAssociadoSchema,
    DimCalendarioSchema,
    DimLinhaCreditoSchema,
    GrupoModalidadeBacenEnum,
    SegmentoCooperadoEnum,
    TipoGarantiaEnum,
    TipoPessoaEnum,
)
from src.schemas.facts import (
    CustoProvisaoBenchmarkSchema,
    EstudoQuebra4966SNCCSchema,
    FatoCarteiraMensalSchema,
    FatoDREGerencialSchema,
    FatoIFDataSNCCSchema,
    FatoREFMacroBCBSchema,
    PontoSerieQuebraSNCCSchema,
    SegmentoIFDataEnum,
    SegmentoREFEnum,
)


def test_dim_calendario_schema_valido() -> None:
    """Valida a instanciação de DimCalendarioSchema com dados válidos."""
    calendario = DimCalendarioSchema(
        data=date(2025, 1, 31),
        ano=2025,
        mes_ano="Jan/2025",
        trimestre="1T",
    )
    assert calendario.ano == 2025
    assert calendario.mes_ano == "Jan/2025"
    assert calendario.trimestre == "1T"


def test_dim_calendario_schema_mes_ano_invalido() -> None:
    """Garante que padrão mes_ano fora do formato regex dispare ValidationError."""
    with pytest.raises(ValidationError):
        DimCalendarioSchema(
            data=date(2025, 1, 31),
            ano=2025,
            mes_ano="01/2025",  # Padrão incorreto (deve ser Jan/2025)
            trimestre="1T",
        )


def test_dim_associado_schema_valido(dados_associado_validos: dict) -> None:
    """Verifica a correta validação de associado cooperado.

    Args:
        dados_associado_validos: Dicionário fixture com campos válidos.
    """
    associado = DimAssociadoSchema(**dados_associado_validos)
    assert associado.id_associado == 1001
    assert associado.tipo_pessoa == TipoPessoaEnum.PF
    assert associado.segmento_cooperado == SegmentoCooperadoEnum.AGRO


def test_dim_associado_schema_rating_fora_dos_limites(dados_associado_validos: dict) -> None:
    """Verifica que ratings internos fora do intervalo 1 a 10 geram erro.

    Args:
        dados_associado_validos: Dicionário fixture com campos válidos.
    """
    dados_associado_validos["rating_interno_comportamental"] = 11
    with pytest.raises(ValidationError):
        DimAssociadoSchema(**dados_associado_validos)


def test_dim_linha_credito_schema_valido() -> None:
    """Valida criação de linha de crédito com enums normativos."""
    linha = DimLinhaCreditoSchema(
        id_linha=1,
        nome_linha="Pronaf Custeio Agricola",
        grupo_modalidade=GrupoModalidadeBacenEnum.CREDITO_RURAL,
        tipo_garantia_predominante=TipoGarantiaEnum.PENHOR_AGRICOLA,
    )
    assert linha.id_linha == 1
    assert linha.grupo_modalidade == GrupoModalidadeBacenEnum.CREDITO_RURAL


def test_fato_carteira_mensal_valida(dados_contrato_validos: dict) -> None:
    """Verifica contrato de carteira mensal preenchido corretamente.

    Args:
        dados_contrato_validos: Dicionário com atributos de contrato válido.
    """
    carteira = FatoCarteiraMensalSchema(**dados_contrato_validos)
    assert carteira.id_contrato == 5001
    assert carteira.saldo_devedor_contabil == Decimal("150000.00")
    assert carteira.estagio_contabil == 1


def test_fato_carteira_mensal_estagio_invalido(dados_contrato_validos: dict) -> None:
    """Garante que estágio diferente de 1, 2 ou 3 seja rejeitado.

    Args:
        dados_contrato_validos: Dicionário com atributos de contrato válido.
    """
    dados_contrato_validos["estagio_contabil"] = 4
    with pytest.raises(ValidationError):
        FatoCarteiraMensalSchema(**dados_contrato_validos)


def test_fato_dre_gerencial_valida() -> None:
    """Valida a integridade contábil do modelo DRE gerencial."""
    dre = FatoDREGerencialSchema(
        data_fechamento=date(2025, 12, 31),
        despesa_pdd_mes=Decimal("450000.00"),
        recuperacao_credito_mes=Decimal("50000.00"),
        despesa_liquida_pdd_mes=Decimal("400000.00"),
        saldo_carteira_total=Decimal("85000000.00"),
        sobras_liquidas_exercicio=Decimal("4200000.00"),
        patrimonio_referencia_pr=Decimal("18000000.00"),
        rwa_risco_credito=Decimal("65000000.00"),
    )
    assert dre.despesa_liquida_pdd_mes == Decimal("400000.00")


def test_fato_ifdata_sncc_valida() -> None:
    """Valida registros do Bacen IF.data para cooperativas singulares."""
    ifdata = FatoIFDataSNCCSchema(
        data_trimestre=date(2025, 9, 30),
        segmento_analise=SegmentoIFDataEnum.COOPERATIVAS_SINGULARES,
        carteira_total_bacen=Decimal("520000000000.00"),
        provisao_total_bacen=Decimal("26000000000.00"),
        ativo_problematico_bacen=Decimal("31200000000.00"),
        ap_over90_bacen=Decimal("15600000000.00"),
        percentual_ap_ifdata=Decimal("0.0600"),
        percentual_provisao_ifdata=Decimal("0.0500"),
    )
    assert ifdata.segmento_analise == SegmentoIFDataEnum.COOPERATIVAS_SINGULARES


def test_fato_ref_macro_bcb_valida() -> None:
    """Valida indicadores macroprudenciais do Relatório de Estabilidade Financeira."""
    ref = FatoREFMacroBCBSchema(
        data_semestre=date(2025, 6, 30),
        segmento=SegmentoREFEnum.SNCC,
        taxa_perda_esperada_estimada=Decimal("0.0420"),
        indice_cobertura_perda_esperada=Decimal("1.0350"),
        custo_credito_12m_percentual=Decimal("0.0380"),
    )
    assert ref.segmento == SegmentoREFEnum.SNCC
    assert ref.indice_cobertura_perda_esperada == Decimal("1.0350")


def test_ponto_serie_quebra_sncc_schema_valido() -> None:
    """Valida a criação de ponto mensal da série de quebra do SNCC com dados válidos.

    Returns:
        None.
    """
    ponto = PontoSerieQuebraSNCCSchema(
        mes_ano="dez/22",
        data_competencia=date(2022, 12, 31),
        taxa_ap_sncc=Decimal("4.07"),
        regime_normativo="Res. 2.682",
        marco_quebra=False,
        destaque_rotulo="4,07%",
    )
    assert ponto.mes_ano == "dez/22"
    assert ponto.taxa_ap_sncc == Decimal("4.07")
    assert ponto.destaque_rotulo == "4,07%"


def test_custo_provisao_benchmark_schema_valido() -> None:
    """Valida o schema de custo de provisão de benchmark do REF.

    Returns:
        None.
    """
    custo = CustoProvisaoBenchmarkSchema(
        periodo_referencia="12 meses até dez/24",
        custo_provisao_pct=Decimal("4.20"),
        regime_normativo="Res. 2.682",
        descricao="Custo sob a regra de perda incorrida",
    )
    assert custo.custo_provisao_pct == Decimal("4.20")
    assert custo.regime_normativo == "Res. 2.682"


def test_estudo_quebra_4966_sncc_schema_valido() -> None:
    """Valida o schema do estudo consolidado de quebra regulatória da 4.966.

    Returns:
        None.
    """
    ponto = PontoSerieQuebraSNCCSchema(
        mes_ano="jan/25",
        data_competencia=date(2025, 1, 31),
        taxa_ap_sncc=Decimal("5.92"),
        regime_normativo="Res. 4.966",
        marco_quebra=True,
        destaque_rotulo="5,92%",
    )
    custo = CustoProvisaoBenchmarkSchema(
        periodo_referencia="12 meses até dez/25",
        custo_provisao_pct=Decimal("3.50"),
        regime_normativo="Transição 4.966",
        descricao="1º ano sob a regra de perda esperada",
    )
    estudo = EstudoQuebra4966SNCCSchema(
        titulo="A 4.966 é a culpada?",
        subtitulo="O AP do SNCC já subia cerca de 1 p.p. ao ano antes da regra.",
        serie_mensal_ap=[ponto],
        custos_provisao_periodos=[custo],
        frase_sintese="A regra mudou. O risco de crédito continua sendo o risco da carteira.",
        nota_metodologica="A variação de jan/25 mistura a quebra e o movimento do mês.",
        fonte="Banco Central do Brasil, REF out/2026, Anexo Estatístico (gráficos 1.2.2.17 e 1.2.3.5).",
    )
    assert len(estudo.serie_mensal_ap) == 1
    assert estudo.custos_provisao_periodos[0].custo_provisao_pct == Decimal("3.50")
