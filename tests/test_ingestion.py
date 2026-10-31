"""Testes unitários e de integração para o pipeline de ingestão e geração sintética.

Verifica a determinística do gerador (seed=42), conciliação matemática estrita com DRE,
presença de cenários limítrofes da Resolução CMN 4.966 e robustez dos clientes Bacen.
"""

from datetime import date
from decimal import Decimal

import pytest
from pytest_mock import MockerFixture

from src.ingestion.ifdata_client import IFDataClient
from src.ingestion.ref_client import REFClient
from src.ingestion.synthetic_generator import SyntheticDataGenerator
from src.schemas.facts import SegmentoIFDataEnum, SegmentoREFEnum


def test_synthetic_generator_calendario_24_meses() -> None:
    """Verifica geração correta de 24 competências mensais entre 2024 e 2025."""
    generator = SyntheticDataGenerator(seed=42)
    cal = generator.gerar_dim_calendario(ano_inicio=2024, anos_duracao=2)
    assert len(cal) == 24
    assert cal[0].mes_ano == "Jan/2024"
    assert cal[-1].mes_ano == "Dez/2025"
    assert cal[0].trimestre == "1T"
    assert cal[-1].trimestre == "4T"


def test_synthetic_generator_reprodutibilidade_deterministica() -> None:
    """Garante que a mesma semente gere exatamente os mesmos saldos e dados."""
    gen1 = SyntheticDataGenerator(seed=42)
    base1 = gen1.gerar_base_completa()

    gen2 = SyntheticDataGenerator(seed=42)
    base2 = gen2.gerar_base_completa()

    assert len(base1["f_Carteira_Mensal"]) == len(base2["f_Carteira_Mensal"])
    contrato1 = base1["f_Carteira_Mensal"][0]
    contrato2 = base2["f_Carteira_Mensal"][0]
    assert contrato1.saldo_devedor_contabil == contrato2.saldo_devedor_contabil
    assert contrato1.saldo_provisao_constituida == contrato2.saldo_provisao_constituida


def test_synthetic_generator_conciliacao_estrita_carteira_dre() -> None:
    """Certifica a conciliação exata ao centavo entre a carteira e o balancete DRE."""
    generator = SyntheticDataGenerator(seed=42)
    base = generator.gerar_base_completa()

    carteira = base["f_Carteira_Mensal"]
    dre_lista = base["f_DRE_Gerencial"]

    mapa_dre = {d.data_fechamento: d.saldo_carteira_total for d in dre_lista}

    saldos_por_data: dict[date, Decimal] = {}
    for c in carteira:
        saldos_por_data[c.data_fechamento] = (
            saldos_por_data.get(c.data_fechamento, Decimal("0.00")) + c.saldo_devedor_contabil
        )

    for data_fechamento, soma_saldo in saldos_por_data.items():
        assert data_fechamento in mapa_dre
        # Conciliação estrita auditável ao centavo
        assert soma_saldo == mapa_dre[data_fechamento]


def test_synthetic_generator_casos_limitrofes_presentes() -> None:
    """Assegura a presença mandatória de casos limítrofes regulatórios na carteira."""
    generator = SyntheticDataGenerator(seed=42)
    base = generator.gerar_base_completa()
    carteira = base["f_Carteira_Mensal"]

    # Caso 1: Atraso de 35 dias (Estágio 2 / SICR)
    c_35 = [c for c in carteira if c.dias_atraso == 35 and c.estagio_contabil == 2]
    assert len(c_35) >= 24

    # Caso 2: Renegociação com 0 dias de atraso (Estágio 3 / AP)
    c_reneg = [
        c
        for c in carteira
        if c.indicador_renegociacao == 1 and c.dias_atraso == 0 and c.estagio_contabil == 3
    ]
    assert len(c_reneg) >= 24
    assert all(c.indicador_ativo_problematico == 1 for c in c_reneg)

    # Caso 3: Atraso de 95 dias (Estágio 3 e Over90)
    c_over90 = [
        c for c in carteira if c.dias_atraso == 95 and c.saldo_vencido_over90 > Decimal("0.00")
    ]
    assert len(c_over90) >= 24
    assert all(c.estagio_contabil == 3 for c in c_over90)
    assert all(c.indicador_ativo_problematico == 1 for c in c_over90)


def test_ifdata_client_fallback_padrao() -> None:
    """Testa consulta ao IF.data via contingência offline segura."""
    client = IFDataClient(timeout=2.0)
    dados = client.obter_dados_ifdata(use_fallback=True)

    assert len(dados) == 24  # 8 trimestres x 3 segmentos
    segmentos = {d.segmento_analise for d in dados}
    assert SegmentoIFDataEnum.COOPERATIVAS_SINGULARES in segmentos
    assert SegmentoIFDataEnum.SNCC_CONSOLIDADO in segmentos
    assert SegmentoIFDataEnum.SFN_TOTAL in segmentos


def test_ifdata_client_filtro_trimestre() -> None:
    """Verifica filtro por trimestre específico no cliente IF.data."""
    client = IFDataClient()
    alvo = date(2025, 9, 30)
    dados = client.obter_dados_ifdata(data_trimestre=alvo)

    assert len(dados) == 3
    assert all(d.data_trimestre == alvo for d in dados)


def test_ref_client_fallback_padrao() -> None:
    """Testa consulta ao REF Bacen via contingência offline segura."""
    client = REFClient(timeout=2.0)
    dados = client.obter_dados_ref(use_fallback=True)

    assert len(dados) == 8  # 4 semestres x 2 segmentos
    segmentos = {d.segmento for d in dados}
    assert SegmentoREFEnum.SNCC in segmentos
    assert SegmentoREFEnum.SFN in segmentos


def test_ifdata_client_erro_sem_fallback(mocker: MockerFixture) -> None:
    """Verifica levantamento de erro quando fallback é desligado e API falha.

    Args:
        mocker: Fixture do pytest-mock para interceptação de requisições.
    """
    client = IFDataClient()
    mocker.patch.object(client, "_consultar_api_online", side_effect=Exception("Timeout no Bacen"))

    with pytest.raises(RuntimeError) as exc_info:
        client.obter_dados_ifdata(use_fallback=False)
    assert "Erro ao consultar IF.data" in str(exc_info.value)
