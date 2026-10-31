"""Testes de auditoria e conciliação contábil estrita da cooperativa singular.

Garante que não haja divergência de centavos entre o somatório individual
dos contratos da carteira analítica e as linhas correspondentes do balancete DRE.
"""

from decimal import Decimal

from src.analytics.metrics import MotorAnaliticoDuckDB
from src.ingestion.synthetic_generator import SyntheticDataGenerator


def test_conciliacao_auditoria_zero_divergencias() -> None:
    """Verifica que o motor analítico DuckDB reporte zero divergências de centavos."""
    generator = SyntheticDataGenerator(seed=42)
    base = generator.gerar_base_completa()

    motor = MotorAnaliticoDuckDB()
    motor.carregar_dados(
        calendario=base["d_Calendario"],
        associados=base["d_Associado"],
        linhas=base["d_LinhaCredito"],
        carteira=base["f_Carteira_Mensal"],
        dre=base["f_DRE_Gerencial"],
    )

    divergencias = motor.auditar_conciliacao_carteira_balancete()
    # A auditoria deve retornar lista vazia (zero divergências contábeis)
    assert len(divergencias) == 0, f"Divergências encontradas no balancete: {divergencias}"


def test_conciliacao_saldos_individuais_positivos() -> None:
    """Verifica que todos os saldos contábeis e de provisão são maiores ou iguais a zero."""
    generator = SyntheticDataGenerator(seed=42)
    base = generator.gerar_base_completa()

    for contrato in base["f_Carteira_Mensal"]:
        assert contrato.saldo_devedor_contabil >= Decimal("0.00")
        assert contrato.saldo_provisao_constituida >= Decimal("0.00")
        assert contrato.saldo_vencido_over90 >= Decimal("0.00")

    for dre_mes in base["f_DRE_Gerencial"]:
        assert dre_mes.saldo_carteira_total > Decimal("0.00")
        assert dre_mes.patrimonio_referencia_pr > Decimal("0.00")
        assert dre_mes.rwa_risco_credito > Decimal("0.00")
