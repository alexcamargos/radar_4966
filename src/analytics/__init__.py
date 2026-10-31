"""Módulo de agregação analítica, cálculo de métricas em DuckDB e exportação.

Fornece queries canônicas para CoR 12M, Vintages, conciliação contábil e
compilação do dataset executivo para o dashboard C-Level.
"""

from src.analytics.data_exporter import exportar_dashboard_data
from src.analytics.metrics import MotorAnaliticoDuckDB

__all__ = [
    "MotorAnaliticoDuckDB",
    "exportar_dashboard_data",
]
