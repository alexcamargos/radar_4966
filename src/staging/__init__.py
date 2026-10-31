"""Módulo de classificação regulatória da Resolução CMN 4.966.

Implementa motor de enquadramento em Estágios (1, 2 e 3), detecção de Ativo Problemático,
cálculo de Perda Esperada (ECL) e análise de safras por MOB (Vintage Analysis).
"""

from src.staging.classifier_4966 import MotorClassificador4966

__all__ = [
    "MotorClassificador4966",
]
