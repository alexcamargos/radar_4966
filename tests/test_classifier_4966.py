"""Testes da modelagem quantitativa e enquadramento da Resolução CMN nº 4.966.

Cobre todos os cenários limítrofes regulatórios de transição de Estágios 1, 2 (SICR)
e 3 (Ativo Problemático), cálculo de Perda Esperada (ECL) e matriz de safras (Vintage).
"""

from datetime import date
from decimal import Decimal

import pytest

from src.schemas.facts import FatoCarteiraMensalSchema
from src.staging.classifier_4966 import MotorClassificador4966


def test_enquadramento_estagio_1_adimplente() -> None:
    """Verifica enquadramento no Estágio 1 para operação regular adimplente."""
    estagio, ap = MotorClassificador4966.classificar_operacao(
        dias_atraso=0,
        indicador_renegociacao=0,
        rating_comportamental_atual=2,
        rating_origem=2,
        pd_atual=Decimal("0.0100"),
        pd_origem=Decimal("0.0100"),
    )
    assert estagio == 1
    assert ap == 0


def test_enquadramento_estagio_1_atraso_baixo() -> None:
    """Verifica enquadramento no Estágio 1 para atraso inferior ou igual a 30 dias."""
    estagio, ap = MotorClassificador4966.classificar_operacao(
        dias_atraso=25,
        indicador_renegociacao=0,
        rating_comportamental_atual=3,
        rating_origem=3,
    )
    assert estagio == 1
    assert ap == 0


def test_enquadramento_estagio_2_sicr_por_atraso() -> None:
    """Verifica migração para Estágio 2 devido a atraso entre 31 e 90 dias."""
    estagio, ap = MotorClassificador4966.classificar_operacao(
        dias_atraso=35,
        indicador_renegociacao=0,
        rating_comportamental_atual=3,
        rating_origem=3,
    )
    assert estagio == 2
    assert ap == 0


def test_enquadramento_estagio_2_sicr_por_rebaixamento_rating() -> None:
    """Verifica migração para Estágio 2 por piora de rating >= 2 níveis com 0 dias de atraso."""
    estagio, ap = MotorClassificador4966.classificar_operacao(
        dias_atraso=0,
        indicador_renegociacao=0,
        rating_comportamental_atual=5,
        rating_origem=3,  # Delta = 2 níveis
    )
    assert estagio == 2
    assert ap == 0


def test_enquadramento_estagio_2_sicr_por_aumento_pd() -> None:
    """Verifica migração para Estágio 2 por aumento relativo de PD >= 250%."""
    estagio, ap = MotorClassificador4966.classificar_operacao(
        dias_atraso=0,
        indicador_renegociacao=0,
        rating_comportamental_atual=3,
        rating_origem=3,
        pd_atual=Decimal("0.0300"),
        pd_origem=Decimal("0.0100"),  # Razão = 3.0 >= 2.5
    )
    assert estagio == 2
    assert ap == 0


def test_enquadramento_estagio_3_over90() -> None:
    """Verifica enquadramento no Estágio 3 e Ativo Problemático por atraso > 90 dias."""
    estagio, ap = MotorClassificador4966.classificar_operacao(
        dias_atraso=91,
        indicador_renegociacao=0,
        rating_comportamental_atual=6,
    )
    assert estagio == 3
    assert ap == 1


def test_enquadramento_estagio_3_renegociacao_forbearance() -> None:
    """Verifica enquadramento no Estágio 3 por renegociação mesmo sem dias de atraso."""
    estagio, ap = MotorClassificador4966.classificar_operacao(
        dias_atraso=0,
        indicador_renegociacao=1,
        rating_comportamental_atual=4,
    )
    assert estagio == 3
    assert ap == 1


def test_enquadramento_estagio_3_rating_pior_possivel() -> None:
    """Verifica enquadramento no Estágio 3 quando o rating interno atinge o nível 10."""
    estagio, ap = MotorClassificador4966.classificar_operacao(
        dias_atraso=10,
        indicador_renegociacao=0,
        rating_comportamental_atual=10,
    )
    assert estagio == 3
    assert ap == 1


def test_enquadramento_estagio_3_indicio_perda() -> None:
    """Verifica enquadramento no Estágio 3 com indício objetivo de perda ou insolvência."""
    estagio, ap = MotorClassificador4966.classificar_operacao(
        dias_atraso=0,
        indicador_renegociacao=0,
        rating_comportamental_atual=3,
        indicio_objetivo_perda=True,
    )
    assert estagio == 3
    assert ap == 1


def test_calculo_perda_esperada_ecl() -> None:
    """Valida a precisão monetária do cálculo de ECL regulatório."""
    saldo = Decimal("100000.00")
    pd = Decimal("0.0250")
    lgd = Decimal("0.4500")

    prov = MotorClassificador4966.calcular_perda_esperada(
        saldo_devedor_contabil=saldo,
        estagio_contabil=1,
        probabilidade_default_pd=pd,
        loss_given_default_lgd=lgd,
    )
    # 100000 * 0.025 * 0.45 = 1125.00
    assert prov == Decimal("1125.00")


def test_classificar_operacao_validacoes_limites() -> None:
    """Garante rejeição de parâmetros inválidos na classificação."""
    with pytest.raises(ValueError):
        MotorClassificador4966.classificar_operacao(
            dias_atraso=-1,
            indicador_renegociacao=0,
            rating_comportamental_atual=3,
        )

    with pytest.raises(ValueError):
        MotorClassificador4966.classificar_operacao(
            dias_atraso=0,
            indicador_renegociacao=0,
            rating_comportamental_atual=11,
        )


def test_classificar_carteira_em_lote(dados_contrato_validos: dict) -> None:
    """Verifica aplicação das regras em lote para contratos da carteira.

    Args:
        dados_contrato_validos: Fixture com contrato base.
    """
    c1 = FatoCarteiraMensalSchema(**dados_contrato_validos)
    dados2 = dados_contrato_validos.copy()
    dados2["id_contrato"] = 5002
    dados2["dias_atraso"] = 95
    c2 = FatoCarteiraMensalSchema(**dados2)

    resultado = MotorClassificador4966.classificar_carteira([c1, c2])
    assert len(resultado) == 2
    assert resultado[0].estagio_contabil == 1
    assert resultado[0].indicador_ativo_problematico == 0
    assert resultado[1].estagio_contabil == 3
    assert resultado[1].indicador_ativo_problematico == 1
    assert resultado[1].saldo_vencido_over90 == c2.saldo_devedor_contabil


def test_matriz_safras_vintage() -> None:
    """Valida o cálculo de agregação de safras e MOB (Months on Book)."""
    c_safra = FatoCarteiraMensalSchema(
        data_fechamento=date(2024, 7, 31),
        id_contrato=8001,
        id_associado=1,
        id_linha=1,
        data_concessao=date(2024, 1, 10),  # MOB = 6
        saldo_devedor_contabil=Decimal("100000.00"),
        dias_atraso=95,
        saldo_vencido_over90=Decimal("100000.00"),
        indicador_renegociacao=0,
        indicador_ativo_problematico=1,
        estagio_contabil=3,
        probabilidade_default_pd=Decimal("0.4000"),
        loss_given_default_lgd=Decimal("0.6000"),
        saldo_provisao_constituida=Decimal("24000.00"),
    )

    linhas = MotorClassificador4966.calcular_matriz_safras([c_safra], mobs_alvo=[1, 3, 6, 12])
    assert len(linhas) == 1
    assert linhas[0]["safra"] == "2024-01"
    assert linhas[0]["mob"] == 6
    assert linhas[0]["saldo_total"] == Decimal("100000.00")
    assert linhas[0]["saldo_ativo_problematico"] == Decimal("100000.00")
    assert linhas[0]["taxa_ativo_problematico"] == Decimal("1.0000")


def test_matriz_safras_anuais() -> None:
    """Valida o cálculo da matriz de safras agregada por ano de concessão."""
    c_safra1 = FatoCarteiraMensalSchema(
        data_fechamento=date(2024, 7, 31),
        id_contrato=8001,
        id_associado=1,
        id_linha=1,
        data_concessao=date(2024, 1, 15),
        saldo_devedor_contabil=Decimal("100000.00"),
        dias_atraso=95,
        saldo_vencido_over90=Decimal("100000.00"),
        indicador_renegociacao=0,
        indicador_ativo_problematico=1,
        estagio_contabil=3,
        probabilidade_default_pd=Decimal("1.0000"),
        loss_given_default_lgd=Decimal("0.6000"),
        saldo_provisao_constituida=Decimal("60000.00"),
    )
    c_safra2 = FatoCarteiraMensalSchema(
        data_fechamento=date(2024, 7, 31),
        id_contrato=8002,
        id_associado=2,
        id_linha=1,
        data_concessao=date(2024, 4, 15),
        saldo_devedor_contabil=Decimal("100000.00"),
        dias_atraso=0,
        saldo_vencido_over90=Decimal("0.00"),
        indicador_renegociacao=0,
        indicador_ativo_problematico=0,
        estagio_contabil=1,
        probabilidade_default_pd=Decimal("0.0200"),
        loss_given_default_lgd=Decimal("0.4000"),
        saldo_provisao_constituida=Decimal("800.00"),
    )

    linhas_anuais = MotorClassificador4966.calcular_matriz_safras_anuais(
        [c_safra1, c_safra2], mobs_alvo=[3, 6]
    )
    # c_safra1 está no MOB 6 (Jan -> Jul = 6 meses)
    # c_safra2 está no MOB 3 (Abr -> Jul = 3 meses)
    assert len(linhas_anuais) == 2
    assert all(item["safra"] == "Safra 2024" for item in linhas_anuais)
    mob3 = next(item for item in linhas_anuais if item["mob"] == 3)
    mob6 = next(item for item in linhas_anuais if item["mob"] == 6)
    assert mob3["taxa_ativo_problematico"] == Decimal("0.0000")
    assert mob6["taxa_ativo_problematico"] == Decimal("1.0000")
