"""Testes da camada analítica em DuckDB e exportador de dados para o dashboard.

Valida métricas canônicas de CoR 12M, Gap de Cobertura, distribuição por Estágios,
decomposição de AP e geração do arquivo JSON do painel executivo.
"""

import json
from decimal import Decimal
from pathlib import Path

from src.analytics.data_exporter import exportar_dashboard_data
from src.analytics.metrics import MotorAnaliticoDuckDB
from src.ingestion.synthetic_generator import SyntheticDataGenerator


def test_motor_analitico_kpis_fechamento() -> None:
    """Verifica apuração correta dos KPIs no fechamento da competência."""
    gen = SyntheticDataGenerator(seed=42)
    base = gen.gerar_base_completa()

    motor = MotorAnaliticoDuckDB()
    motor.carregar_dados(
        calendario=base["d_Calendario"],
        associados=base["d_Associado"],
        linhas=base["d_LinhaCredito"],
        carteira=base["f_Carteira_Mensal"],
        dre=base["f_DRE_Gerencial"],
    )

    data_base = base["d_Calendario"][-1].data
    kpis = motor.calcular_kpis_fechamento(data_base)

    assert kpis["data_base"] == data_base
    assert kpis["carteira_ativa"] > Decimal("0.00")
    assert kpis["saldo_ativo_problematico"] > Decimal("0.00")
    assert kpis["taxa_ativo_problematico_pct"] > Decimal("0.00")
    assert kpis["taxa_provisao_pct"] > Decimal("0.00")
    assert "gap_cobertura_pct" in kpis
    assert kpis["taxa_inadimplencia_over90_pct"] > Decimal("0.00")


def test_motor_analitico_serie_historica_e_cruzamento() -> None:
    """Verifica o histórico mensal de 78 meses e detecção do cruzamento Prov < AP."""
    gen = SyntheticDataGenerator(seed=42)
    base = gen.gerar_base_completa()

    motor = MotorAnaliticoDuckDB()
    motor.carregar_dados(
        calendario=base["d_Calendario"],
        associados=base["d_Associado"],
        linhas=base["d_LinhaCredito"],
        carteira=base["f_Carteira_Mensal"],
        dre=base["f_DRE_Gerencial"],
    )

    serie = motor.calcular_serie_historica_mensal()
    assert len(serie) == 78
    assert all("taxa_ap" in s and "taxa_provisao" in s for s in serie)
    # Deve conter chave de alerta de cruzamento
    assert any("cruzamento_alerta" in s for s in serie)


def test_motor_analitico_cor_12m_janela_movel() -> None:
    """Valida o cálculo do Cost of Risk (CoR 12M%) com janela móvel de 12 meses."""
    gen = SyntheticDataGenerator(seed=42)
    base = gen.gerar_base_completa()

    motor = MotorAnaliticoDuckDB()
    motor.carregar_dados(
        calendario=base["d_Calendario"],
        associados=base["d_Associado"],
        linhas=base["d_LinhaCredito"],
        carteira=base["f_Carteira_Mensal"],
        dre=base["f_DRE_Gerencial"],
    )

    cor_lista = motor.calcular_custo_credito_movel_12m()
    assert len(cor_lista) == 78
    # Nos últimos meses, despesa acumulada e CoR devem ser estritamente positivos
    ultimo_cor = cor_lista[-1]
    assert ultimo_cor["despesa_pdd_12m"] > Decimal("0.00")
    assert ultimo_cor["media_carteira_12m"] > Decimal("0.00")
    assert ultimo_cor["percentual_cor_12m"] > Decimal("0.00")
    # Meses iniciais (<12 meses) devem ter taxa anualizada calculada proporcionalmente
    primeiro_cor = cor_lista[0]
    assert primeiro_cor["percentual_cor_12m"] > Decimal("0.00")


def test_motor_analitico_cruzamento_transicao_real() -> None:
    """Verifica que o alerta de cruzamento só dispara em transição real Prov < AP (não no mês 0)."""
    gen = SyntheticDataGenerator(seed=42)
    base = gen.gerar_base_completa()

    motor = MotorAnaliticoDuckDB()
    motor.carregar_dados(
        calendario=base["d_Calendario"],
        associados=base["d_Associado"],
        linhas=base["d_LinhaCredito"],
        carteira=base["f_Carteira_Mensal"],
        dre=base["f_DRE_Gerencial"],
    )

    serie = motor.calcular_serie_historica_mensal()
    # No primeiro mês, a cooperativa não deve disparar cruzamento espúrio
    assert not serie[0]["cruzamento_alerta"]
    assert serie[0]["gap_cobertura"] >= Decimal("0.00")

    # Deve existir exatamente 1 ponto de inflexão de cruzamento ao longo da série histórica
    pontos_cruzamento = [s for s in serie if s["cruzamento_alerta"]]
    assert len(pontos_cruzamento) == 1
    pt = pontos_cruzamento[0]
    assert pt["taxa_provisao"] < pt["taxa_ap"]


def test_motor_analitico_decomposicao_ap_terminologia_4966() -> None:
    """Verifica se a decomposição do AP adota a terminologia estrita da Res. 4.966."""
    gen = SyntheticDataGenerator(seed=42)
    base = gen.gerar_base_completa()

    motor = MotorAnaliticoDuckDB()
    motor.carregar_dados(
        calendario=base["d_Calendario"],
        associados=base["d_Associado"],
        linhas=base["d_LinhaCredito"],
        carteira=base["f_Carteira_Mensal"],
        dre=base["f_DRE_Gerencial"],
    )

    data_base = base["d_Calendario"][-1].data
    dec = motor.calcular_decomposicao_ap(data_base)

    assert "saldo_over90" in dec
    assert "saldo_renegociacao" in dec
    assert "saldo_deterioracao_insolvencia" in dec
    assert "percentual_deterioracao_insolvencia" in dec
    assert "saldo_outros_preventivos" in dec  # retrocompatibilidade
    soma_fatias = (
        dec["saldo_over90"]
        + dec["saldo_renegociacao"]
        + dec["saldo_deterioracao_insolvencia"]
    )
    assert soma_fatias == dec["total_ativo_problematico"]


def test_exportar_dashboard_data(tmp_path: Path) -> None:
    """Valida a compilação completa do JSON do dashboard em diretório temporário.

    Args:
        tmp_path: Fixture do pytest com diretório isolado de teste.
    """
    arquivo_teste = tmp_path / "dashboard_data.json"
    dados = exportar_dashboard_data(caminho_saida=arquivo_teste, seed=42)

    assert arquivo_teste.exists()
    assert "metadata" in dados
    assert "kpis_topo" in dados
    assert "serie_temporal_mensal" in dados
    assert "benchmarking_ifdata" in dados
    assert "benchmarking_ref" in dados
    assert "matriz_safras_vintages" in dados
    assert "matriz_safras_anuais" in dados
    assert "simulador_capital_base" in dados

    with open(arquivo_teste, encoding="utf-8") as f:
        carregado = json.load(f)
    assert carregado["metadata"]["total_competencias"] == 78
    assert carregado["metadata"]["data_inicio"] == "2020-01-31"
    assert carregado["metadata"]["competencia_mais_recente"] == "2026-06-30"
