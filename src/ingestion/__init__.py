"""Módulo de ingestão de dados e conectores externos e geradores da plataforma.

Exporta clientes do Banco Central (IF.data e REF) e gerador sintético determinístico.
"""

from src.ingestion.ifdata_client import IFDataClient
from src.ingestion.ref_client import REFClient
from src.ingestion.synthetic_generator import DatasetSintetico, SyntheticDataGenerator

__all__ = [
    "DatasetSintetico",
    "IFDataClient",
    "REFClient",
    "SyntheticDataGenerator",
]
