"""Módulo de ingestão e geração de dados da plataforma Radar 4966.

Disponibiliza clientes para extração do Bacen (IF.data e REF) e gerador sintético
determinístico com conciliação contábil estrita.
"""

from src.ingestion.ifdata_client import IFDataClient
from src.ingestion.ref_client import REFClient
from src.ingestion.synthetic_generator import SyntheticDataGenerator

__all__ = [
    "IFDataClient",
    "REFClient",
    "SyntheticDataGenerator",
]
