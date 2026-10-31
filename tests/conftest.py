"""Fixtures compartilhadas para a suíte de testes com pytest.

Fornece instâncias de dados base, clientes e configurações comuns.
"""

from datetime import date
from decimal import Decimal

import pytest

from src.schemas.dimensions import SegmentoCooperadoEnum, TipoPessoaEnum


@pytest.fixture
def data_base_padrao() -> date:
    """Retorna data base padrão para testes mensais.

    Returns:
        Data referente ao encerramento da competência contábil de teste.
    """
    return date(2025, 12, 31)


@pytest.fixture
def dados_associado_validos() -> dict:
    """Retorna dicionário com atributos válidos de cooperado.

    Returns:
        Dicionário com valores compatíveis com DimAssociadoSchema.
    """
    return {
        "id_associado": 1001,
        "tipo_pessoa": TipoPessoaEnum.PF,
        "segmento_cooperado": SegmentoCooperadoEnum.AGRO,
        "data_admissao": date(2020, 1, 15),
        "rating_interno_comportamental": 3,
    }


@pytest.fixture
def dados_contrato_validos(data_base_padrao: date) -> dict:
    """Retorna dicionário com atributos válidos de contrato na carteira.

    Args:
        data_base_padrao: Fixture com data de fechamento padrão.

    Returns:
        Dicionário com valores compatíveis com FatoCarteiraMensalSchema.
    """
    return {
        "data_fechamento": data_base_padrao,
        "id_contrato": 5001,
        "id_associado": 1001,
        "id_linha": 1,
        "data_concessao": date(2024, 6, 10),
        "saldo_devedor_contabil": Decimal("150000.00"),
        "dias_atraso": 0,
        "saldo_vencido_over90": Decimal("0.00"),
        "indicador_renegociacao": 0,
        "indicador_ativo_problematico": 0,
        "estagio_contabil": 1,
        "probabilidade_default_pd": Decimal("0.0125"),
        "loss_given_default_lgd": Decimal("0.4500"),
        "saldo_provisao_constituida": Decimal("843.75"),
    }
