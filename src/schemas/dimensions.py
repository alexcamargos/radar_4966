"""Esquemas formais Pydantic V2 para as tabelas de dimensão.

Define as estruturas tabulares de calendário, associados e linhas de crédito,
garantindo tipagem estrita e validação dos dados de entrada.
"""

from datetime import date
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class TipoPessoaEnum(StrEnum):
    """Classificação cadastral do cooperado (PF ou PJ).

    Attributes:
        PF: Pessoa Física.
        PJ: Pessoa Jurídica.
    """

    PF = "PF"
    PJ = "PJ"


class SegmentoCooperadoEnum(StrEnum):
    """Segmentação econômica do associado na cooperativa de crédito.

    Attributes:
        AGRO: Cooperados vinculados a atividades agropecuárias.
        COMERCIAL: Empresas e empreendedores comerciais e de serviços.
        VAREJO: Cooperados com foco em consumo ou microempresas.
        SERVIDOR_PUBLICO: Associados com vínculo estável no serviço público.
        OUTROS: Demais categorias de associados.
    """

    AGRO = "Agro"
    COMERCIAL = "Comercial"
    VAREJO = "Varejo"
    SERVIDOR_PUBLICO = "Servidor Publico"
    OUTROS = "Outros"


class GrupoModalidadeBacenEnum(StrEnum):
    """Agrupamento regulatório de modalidades de crédito conforme Bacen.

    Attributes:
        CREDITO_RURAL: Operações de custeio, investimento e comercialização rural.
        CAPITAL_DE_GIRO: Financiamentos para fluxo de caixa empresarial.
        CONSUMO: Crédito pessoal, cartões e veículos.
        HABITACIONAL: Financiamento imobiliário e habitação cooperativa.
    """

    CREDITO_RURAL = "Credito Rural"
    CAPITAL_DE_GIRO = "Capital de Giro"
    CONSUMO = "Consumo"
    HABITACIONAL = "Habitacional"


class TipoGarantiaEnum(StrEnum):
    """Classificação da garantia predominante da operação de crédito.

    Attributes:
        FIDEJUSSORIA: Avalista ou fiador.
        ALIENACAO_FIDUCIARIA: Veículos, imóveis ou bens dados em garantia fiduciária.
        PENHOR_AGRICOLA: Grãos, safras futuras ou maquinário agrícola.
        LIMPA: Operação desprovida de garantia real ou pessoal formal.
    """

    FIDEJUSSORIA = "Fidejussoria"
    ALIENACAO_FIDUCIARIA = "Alienacao Fiduciaria"
    PENHOR_AGRICOLA = "Penhor Agricola"
    LIMPA = "Limpa"


class DimCalendarioSchema(BaseModel):
    """Schema para a dimensão temporal mensal da cooperativa.

    Attributes:
        data: Chave temporal no último dia de cada mês (PK).
        ano: Ano de referência no formato AAAA.
        mes_ano: Mês e ano abreviados (ex.: 'Jan/2024').
        trimestre: Trimestre civil no formato '1T' a '4T'.
    """

    model_config = ConfigDict(strict=True)

    data: date = Field(..., description="Chave temporal no último dia de cada mês (PK)")
    ano: int = Field(..., ge=2000, le=2100, description="Ano no formato AAAA")
    mes_ano: str = Field(..., pattern=r"^(Jan|Fev|Mar|Abr|Mai|Jun|Jul|Ago|Set|Out|Nov|Dez)/\d{4}$")
    trimestre: str = Field(..., pattern=r"^[1-4]T$")


class DimAssociadoSchema(BaseModel):
    """Schema para a dimensão de associados da cooperativa.

    Attributes:
        id_associado: Identificador unívoco anonimizado do cooperado (PK).
        tipo_pessoa: Classificação entre Pessoa Física ou Jurídica.
        segmento_cooperado: Segmento econômico de relacionamento.
        data_admissao: Data de ingresso na sociedade cooperativa.
        rating_interno_comportamental: Score interno de risco de 1 (melhor) a 10 (pior).
    """

    model_config = ConfigDict(strict=True)

    id_associado: int = Field(..., ge=1, description="Identificador unívoco anonimizado (PK)")
    tipo_pessoa: TipoPessoaEnum
    segmento_cooperado: SegmentoCooperadoEnum
    data_admissao: date
    rating_interno_comportamental: int = Field(
        ...,
        ge=1,
        le=10,
        description="Score interno de 1 (melhor) a 10 (pior)",
    )


class DimLinhaCreditoSchema(BaseModel):
    """Schema para a dimensão de modalidades e produtos de crédito.

    Attributes:
        id_linha: Código identificador interno da modalidade de crédito (PK).
        nome_linha: Descrição comercial e contábil do produto.
        grupo_modalidade: Agrupamento normativo Bacen.
        tipo_garantia_predominante: Tipo predominante de garantia vinculada.
    """

    model_config = ConfigDict(strict=True)

    id_linha: int = Field(..., ge=1, description="Código interno da modalidade (PK)")
    nome_linha: str = Field(..., min_length=3, max_length=100)
    grupo_modalidade: GrupoModalidadeBacenEnum
    tipo_garantia_predominante: TipoGarantiaEnum
