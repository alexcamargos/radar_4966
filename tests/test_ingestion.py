"""Testes unitários automatizados para o módulo de ingestão e geração sintética.

Valida os conectores do Banco Central (IF.data e REF), o gerador determinístico,
a integridade das dimensões, a presença dos casos limítrofes normativos da Res. 4.966
e a conciliação contábil exata centavo a centavo com a DRE.
"""

from datetime import date
from decimal import Decimal

from pytest_mock import MockerFixture

from src.ingestion.ifdata_client import IFDataClient
from src.ingestion.ref_client import REFClient
from src.ingestion.synthetic_generator import SyntheticDataGenerator
from src.schemas.facts import SegmentoIFDataEnum, SegmentoREFEnum


def test_ifdata_client_obter_dados_trimestrais_fallback() -> None:
    """Verifica que o IFDataClient retorna a série histórica de fallback completa (2020 a 2026)."""
    cliente = IFDataClient()
    dados = cliente.obter_dados_trimestrais()

    # 26 trimestres x 4 segmentos (Singulares, SNCC, SFN e Credijequitinhonha)
    assert len(dados) == 104
    segmentos = {item.segmento_analise for item in dados}
    assert SegmentoIFDataEnum.COOPERATIVAS_SINGULARES in segmentos
    assert SegmentoIFDataEnum.SNCC_CONSOLIDADO in segmentos
    assert SegmentoIFDataEnum.SFN_TOTAL in segmentos
    assert SegmentoIFDataEnum.SICOOB_CREDIJEQUITINHONHA in segmentos

    # Validação de tipos decimais
    for item in dados:
        assert isinstance(item.carteira_total_bacen, Decimal)
        assert item.carteira_total_bacen > Decimal("0.00")
        assert item.percentual_ap_ifdata > Decimal("0.00")


def test_ifdata_client_filtro_data() -> None:
    """Verifica que o filtro por data_trimestre restringe a consulta ao trimestre informado."""
    cliente = IFDataClient()
    data_filtro = date(2025, 9, 30)
    dados = cliente.obter_dados_trimestrais(data_trimestre=data_filtro)

    assert len(dados) == 4  # 4 segmentos do mesmo trimestre
    for item in dados:
        assert item.data_trimestre == data_filtro


def test_ifdata_client_obter_dados_credijequitinhonha() -> None:
    """Verifica a extração das séries exclusivas do Sicoob Credijequitinhonha no IF.data."""
    cliente = IFDataClient()
    dados_singular = cliente.obter_dados_credijequitinhonha()

    assert len(dados_singular) == 26  # 26 trimestres de 2020 a 2026
    for item in dados_singular:
        assert item.segmento_analise == SegmentoIFDataEnum.SICOOB_CREDIJEQUITINHONHA
        assert item.carteira_total_bacen > Decimal("200000000.00")
        assert item.provisao_total_bacen > Decimal("5000000.00")
        assert Decimal("0.0300") <= item.percentual_ap_ifdata <= Decimal("0.0600")

    # Filtro pontual por competência trimestral
    data_filtro = date(2026, 6, 30)
    dado_recente = cliente.obter_dados_credijequitinhonha(data_trimestre=data_filtro)
    assert len(dado_recente) == 1
    assert dado_recente[0].data_trimestre == data_filtro


def test_ifdata_client_com_mock_http(mocker: MockerFixture) -> None:
    """Verifica que falhas de rede no IFDataClient acionam o fallback sem lançar exceção.

    Args:
        mocker: Fixture nativa do pytest-mock.
    """
    mocker.patch(
        "src.ingestion.ifdata_client.IFDataClient._requisitar_api_remota",
        side_effect=ConnectionError("Bacen timeout simulado"),
    )
    cliente = IFDataClient()
    dados = cliente.obter_dados_trimestrais()
    assert len(dados) == 104


def test_ref_client_obter_dados_semestrais_fallback() -> None:
    """Verifica que o REFClient retorna indicadores macroprudenciais de referência."""
    cliente = REFClient()
    dados = cliente.obter_dados_semestrais()

    assert len(dados) == 26  # 13 semestres x 2 segmentos (SNCC e SFN)
    segmentos = {item.segmento for item in dados}
    assert SegmentoREFEnum.SNCC in segmentos
    assert SegmentoREFEnum.SFN in segmentos

    for item in dados:
        assert item.indice_cobertura_perda_esperada > Decimal("0.90")
        assert item.taxa_perda_esperada_estimada > Decimal("0.00")


def test_ref_client_filtro_data() -> None:
    """Verifica filtro por data_semestre no cliente REF."""
    cliente = REFClient()
    data_filtro = date(2025, 6, 30)
    dados = cliente.obter_dados_semestrais(data_semestre=data_filtro)

    assert len(dados) == 2  # SNCC e SFN
    for item in dados:
        assert item.data_semestre == data_filtro


def test_ref_client_com_mock_http(mocker: MockerFixture) -> None:
    """Verifica resiliência do REFClient com simulação de erro de transporte HTTP.

    Args:
        mocker: Fixture nativa do pytest-mock.
    """
    mocker.patch(
        "src.ingestion.ref_client.REFClient._requisitar_api_remota",
        side_effect=TimeoutError("Erro de comunicação com o Bacen"),
    )
    cliente = REFClient()
    dados = cliente.obter_dados_semestrais()
    assert len(dados) == 26


def test_synthetic_generator_calendario_24m() -> None:
    """Valida a geração de 24 competências na dimensão calendário."""
    gerador = SyntheticDataGenerator(seed=42)
    cal = gerador.gerar_calendario_24m()

    assert len(cal) == 24
    assert cal[0].data == date(2024, 1, 31)
    assert cal[-1].data == date(2025, 12, 31)
    assert cal[0].mes_ano == "Jan/2024"
    assert cal[-1].mes_ano == "Dez/2025"


def test_synthetic_generator_calendario_historico_78m() -> None:
    """Valida a geração de 78 meses (5 anos pré-4.966 de 2020 a 2024 até 06/2026)."""
    gerador = SyntheticDataGenerator(seed=42)
    cal = gerador.gerar_calendario(ano_inicio=2020, ano_fim=2026, mes_fim=6)

    assert len(cal) == 78
    assert cal[0].data == date(2020, 1, 31)
    assert cal[-1].data == date(2026, 6, 30)
    assert cal[0].mes_ano == "Jan/2020"
    assert cal[-1].mes_ano == "Jun/2026"


def test_synthetic_generator_dimensoes() -> None:
    """Valida a consistência das dimensões de associados e linhas de crédito."""
    gerador = SyntheticDataGenerator(seed=42)
    linhas = gerador.gerar_linhas_credito()
    associados = gerador.gerar_associados(quantidade=50)

    assert len(linhas) >= 7
    assert len(associados) == 50
    for assoc in associados:
        assert 1 <= assoc.rating_interno_comportamental <= 10


def test_synthetic_generator_dataset_completo_conciliacao() -> None:
    """Audita a conciliação matemática estrita centavo a centavo entre Carteira e DRE."""
    gerador = SyntheticDataGenerator(seed=42)
    dataset = gerador.gerar_dataset_completo()

    assert len(dataset.calendario) == 78  # 2020-01 a 2026-06
    assert len(dataset.dre_gerencial) == 78
    assert len(dataset.carteira_mensal) > 0

    # Agrupa por competência e audita a igualdade contábil
    competencias = {cal.data for cal in dataset.calendario}
    assert len(competencias) == 78

    for comp in competencias:
        contratos_mes = [c for c in dataset.carteira_mensal if c.data_fechamento == comp]
        dre_mes = next((d for d in dataset.dre_gerencial if d.data_fechamento == comp), None)

        assert dre_mes is not None, f"DRE não encontrada para a competência {comp}"

        soma_saldo_carteira = sum(
            (c.saldo_devedor_contabil for c in contratos_mes), Decimal("0.00")
        )
        msg_erro = (
            f"Divergência contábil em {comp}: {soma_saldo_carteira} != "
            f"{dre_mes.saldo_carteira_total}"
        )
        assert soma_saldo_carteira == dre_mes.saldo_carteira_total, msg_erro


def test_synthetic_generator_casos_limitrofes_obrigatorios() -> None:
    """Assegura a presença dos 3 casos limítrofes normativos da Resolução CMN 4.966."""
    gerador = SyntheticDataGenerator(seed=42)
    dataset = gerador.gerar_dataset_completo()

    # Competência para validação
    comp_teste = date(2025, 12, 31)
    contratos_mes = [c for c in dataset.carteira_mensal if c.data_fechamento == comp_teste]

    # Caso 1: Atraso de 35 dias com rebaixamento de rating -> Estágio 2 (SICR)
    c1 = next((c for c in contratos_mes if c.id_contrato == 1), None)
    assert c1 is not None
    assert c1.dias_atraso == 35
    assert c1.estagio_contabil == 2
    assert c1.indicador_ativo_problematico == 0

    # Caso 2: Operação renegociada com 0 dias de atraso -> Estágio 3 / AP (forbearance)
    c2 = next((c for c in contratos_mes if c.id_contrato == 2), None)
    assert c2 is not None
    assert c2.dias_atraso == 0
    assert c2.indicador_renegociacao == 1
    assert c2.estagio_contabil == 3
    assert c2.indicador_ativo_problematico == 1

    # Caso 3: Operação com 95 dias de atraso -> Estágio 3 e Over90
    c3 = next((c for c in contratos_mes if c.id_contrato == 3), None)
    assert c3 is not None
    assert c3.dias_atraso == 95
    assert c3.saldo_vencido_over90 > Decimal("0.00")
    assert c3.estagio_contabil == 3
    assert c3.indicador_ativo_problematico == 1


def test_synthetic_generator_reprodutibilidade() -> None:
    """Verifica que o gerador é estritamente determinístico quando utiliza a mesma semente."""
    gen1 = SyntheticDataGenerator(seed=42)
    gen2 = SyntheticDataGenerator(seed=42)

    ds1 = gen1.gerar_dataset_completo()
    ds2 = gen2.gerar_dataset_completo()

    assert len(ds1.carteira_mensal) == len(ds2.carteira_mensal)
    assert ds1.dre_gerencial[0].saldo_carteira_total == ds2.dre_gerencial[0].saldo_carteira_total
    assert (
        ds1.carteira_mensal[0].saldo_devedor_contabil
        == ds2.carteira_mensal[0].saldo_devedor_contabil
    )


def test_synthetic_generator_consistencia_temporal() -> None:
    """Verifica ausência de anacronismo temporal e consistência física dos dias de atraso."""
    gen = SyntheticDataGenerator(seed=42)
    ds = gen.gerar_dataset_completo()

    for c in ds.carteira_mensal:
        # Nenhum contrato pode ter data de concessão futura à data de fechamento contábil
        assert c.data_concessao <= c.data_fechamento, (
            f"Anacronismo temporal no contrato {c.id_contrato}: "
            f"concessão {c.data_concessao} > fechamento {c.data_fechamento}"
        )
        idade_dias = (c.data_fechamento - c.data_concessao).days
        # Dias de atraso nunca podem exceder a idade biológica do contrato desde a concessão
        assert c.dias_atraso <= idade_dias, (
            f"Inconsistência de atraso no contrato {c.id_contrato}: "
            f"atraso {c.dias_atraso}d > idade {idade_dias}d"
        )


def test_synthetic_generator_pd_estagio_3() -> None:
    """Verifica que contratos em default / Estágio 3 possuem PD calculada em 100% (1.0000)."""
    gen = SyntheticDataGenerator(seed=42)
    ds = gen.gerar_dataset_completo()

    contratos_e3 = [c for c in ds.carteira_mensal if c.estagio_contabil == 3]
    assert len(contratos_e3) > 0
    for c in contratos_e3:
        assert c.probabilidade_default_pd == Decimal("1.0000"), (
            f"Contrato {c.id_contrato} em Estágio 3 com PD incorreta: {c.probabilidade_default_pd}"
        )
        assert c.indicador_ativo_problematico == 1
