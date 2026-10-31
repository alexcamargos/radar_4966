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
    FatoCarteiraMensalSchema,
    FatoDREGerencialSchema,
    FatoIFDataSNCCSchema,
    FatoREFMacroBCBSchema,
    SegmentoIFDataEnum,
    SegmentoREFEnum,
)

__all__ = [
    "DimAssociadoSchema",
    "DimCalendarioSchema",
    "DimLinhaCreditoSchema",
    "FatoCarteiraMensalSchema",
    "FatoDREGerencialSchema",
    "FatoIFDataSNCCSchema",
    "FatoREFMacroBCBSchema",
    "GrupoModalidadeBacenEnum",
    "SegmentoCooperadoEnum",
    "SegmentoIFDataEnum",
    "SegmentoREFEnum",
    "TipoGarantiaEnum",
    "TipoPessoaEnum",
]
