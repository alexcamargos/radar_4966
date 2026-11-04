"""Módulo de contratos e validações Pydantic V2 para tabelas do modelo analítico.

Exporta classes de dimensões e fatos da plataforma de risco de crédito.
"""

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

__all__ = [
    "CustoProvisaoBenchmarkSchema",
    "DimAssociadoSchema",
    "DimCalendarioSchema",
    "DimLinhaCreditoSchema",
    "EstudoQuebra4966SNCCSchema",
    "FatoCarteiraMensalSchema",
    "FatoDREGerencialSchema",
    "FatoIFDataSNCCSchema",
    "FatoREFMacroBCBSchema",
    "GrupoModalidadeBacenEnum",
    "PontoSerieQuebraSNCCSchema",
    "SegmentoCooperadoEnum",
    "SegmentoIFDataEnum",
    "SegmentoREFEnum",
    "TipoGarantiaEnum",
    "TipoPessoaEnum",
]
