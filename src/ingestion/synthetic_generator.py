"""Gerador de dados sintéticos determinísticos para risco de crédito e provisão.

Produz massa de dados para 24 competências mensais com semente aleatória fixa (seed=42),
garantindo conciliação matemática estrita com o balancete e inclusão de casos limítrofes
da Resolução CMN nº 4.966.
"""

import random
from calendar import monthrange
from datetime import date
from decimal import ROUND_HALF_UP, Decimal
from typing import Any, ClassVar

from src.schemas.dimensions import (
    DimAssociadoSchema,
    DimCalendarioSchema,
    DimLinhaCreditoSchema,
    GrupoModalidadeBacenEnum,
    SegmentoCooperadoEnum,
    TipoGarantiaEnum,
    TipoPessoaEnum,
)
from src.schemas.facts import FatoCarteiraMensalSchema, FatoDREGerencialSchema


class SyntheticDataGenerator:
    """Gerador determinístico do ecossistema analítico da singular cooperativa.

    Attributes:
        seed: Semente numérica inteira para garantia de reprodutibilidade auditável.
    """

    MESES_SIGLAS: ClassVar[list[str]] = [
        "Jan",
        "Fev",
        "Mar",
        "Abr",
        "Mai",
        "Jun",
        "Jul",
        "Ago",
        "Set",
        "Out",
        "Nov",
        "Dez",
    ]

    def __init__(self, seed: int = 42) -> None:
        """Inicializa o gerador configurando a semente determinística.

        Args:
            seed: Semente de números pseudoaleatórios (padrão 42).
        """
        self.seed = seed
        random.seed(self.seed)

    def gerar_dim_calendario(
        self,
        ano_inicio: int = 2024,
        anos_duracao: int = 2,
    ) -> list[DimCalendarioSchema]:
        """Gera a dimensão de calendário mensal para os anos especificados.

        Args:
            ano_inicio: Ano de partida da série histórica (ex.: 2024).
            anos_duracao: Quantidade de anos completos a gerar (padrão 2 = 24 meses).

        Returns:
            Lista de instâncias DimCalendarioSchema com o último dia de cada mês.

        Raises:
            ValueError: Se anos_duracao for menor que 1.
        """
        if anos_duracao < 1:
            raise ValueError("anos_duracao deve ser maior ou igual a 1.")

        calendario: list[DimCalendarioSchema] = []
        for ano in range(ano_inicio, ano_inicio + anos_duracao):
            for mes in range(1, 13):
                ultimo_dia = monthrange(ano, mes)[1]
                data_mes = date(ano, mes, ultimo_dia)
                trimestre_num = ((mes - 1) // 3) + 1
                calendario.append(
                    DimCalendarioSchema(
                        data=data_mes,
                        ano=ano,
                        mes_ano=f"{self.MESES_SIGLAS[mes - 1]}/{ano}",
                        trimestre=f"{trimestre_num}T",
                    )
                )
        return calendario

    def gerar_dim_linhas_credito(self) -> list[DimLinhaCreditoSchema]:
        """Gera as modalidades de crédito canônicas da cooperativa singular.

        Returns:
            Lista de modalidades mapeadas para os grupos normativos do Bacen.
        """
        return [
            DimLinhaCreditoSchema(
                id_linha=1,
                nome_linha="Pronaf Custeio Agro",
                grupo_modalidade=GrupoModalidadeBacenEnum.CREDITO_RURAL,
                tipo_garantia_predominante=TipoGarantiaEnum.PENHOR_AGRICOLA,
            ),
            DimLinhaCreditoSchema(
                id_linha=2,
                nome_linha="Pronamp Investimento",
                grupo_modalidade=GrupoModalidadeBacenEnum.CREDITO_RURAL,
                tipo_garantia_predominante=TipoGarantiaEnum.ALIENACAO_FIDUCIARIA,
            ),
            DimLinhaCreditoSchema(
                id_linha=3,
                nome_linha="Capital de Giro Empresas",
                grupo_modalidade=GrupoModalidadeBacenEnum.CAPITAL_DE_GIRO,
                tipo_garantia_predominante=TipoGarantiaEnum.FIDEJUSSORIA,
            ),
            DimLinhaCreditoSchema(
                id_linha=4,
                nome_linha="Credito Pessoal Consignado",
                grupo_modalidade=GrupoModalidadeBacenEnum.CONSUMO,
                tipo_garantia_predominante=TipoGarantiaEnum.LIMPA,
            ),
            DimLinhaCreditoSchema(
                id_linha=5,
                nome_linha="Financiamento Habitacional",
                grupo_modalidade=GrupoModalidadeBacenEnum.HABITACIONAL,
                tipo_garantia_predominante=TipoGarantiaEnum.ALIENACAO_FIDUCIARIA,
            ),
        ]

    def gerar_dim_associados(self, total_associados: int = 120) -> list[DimAssociadoSchema]:
        """Gera a base de associados anonimizada da cooperativa.

        Args:
            total_associados: Quantidade total de cooperados sintéticos a criar.

        Returns:
            Lista de associados conforme DimAssociadoSchema.

        Raises:
            ValueError: Se total_associados for menor que 10.
        """
        if total_associados < 10:
            raise ValueError("total_associados deve ser de no mínimo 10.")

        segmentos = [
            SegmentoCooperadoEnum.AGRO,
            SegmentoCooperadoEnum.COMERCIAL,
            SegmentoCooperadoEnum.VAREJO,
            SegmentoCooperadoEnum.SERVIDOR_PUBLICO,
            SegmentoCooperadoEnum.OUTROS,
        ]

        associados: list[DimAssociadoSchema] = []
        for i in range(1, total_associados + 1):
            tipo = TipoPessoaEnum.PJ if (i % 4 == 0) else TipoPessoaEnum.PF
            seg = segmentos[i % len(segmentos)]
            # Data de admissão retroativa determinística
            data_adm = date(2018 + (i % 5), (i % 12) + 1, (i % 25) + 1)
            # Ratings entre 1 e 8 para associados comuns
            rating = (i % 7) + 1

            associados.append(
                DimAssociadoSchema(
                    id_associado=i,
                    tipo_pessoa=tipo,
                    segmento_cooperado=seg,
                    data_admissao=data_adm,
                    rating_interno_comportamental=rating,
                )
            )
        return associados

    def gerar_carteira_e_dre_mensal(
        self,
        calendario: list[DimCalendarioSchema],
        associados: list[DimAssociadoSchema],
        linhas: list[DimLinhaCreditoSchema],
    ) -> tuple[list[FatoCarteiraMensalSchema], list[FatoDREGerencialSchema]]:
        """Gera a evolução mensal da carteira de contratos e respectivo balancete/DRE.

        Garante conciliação contábil estrita e presença obrigatória de casos de borda:
        1. Atraso de 35 dias com migração de rating (teste de Estágio 2 / SICR);
        2. Operação renegociada com 0 dias de atraso (teste de Estágio 3 / AP);
        3. Operação com 95 dias de atraso (teste de Estágio 3 e Over90).

        Args:
            calendario: Lista de competências mensais.
            associados: Lista de associados para vínculo das operações.
            linhas: Linhas de crédito disponíveis.

        Returns:
            Tupla contendo a lista completa de operações mensais e a lista de registros da DRE.
        """
        carteira_total: list[FatoCarteiraMensalSchema] = []
        dre_total: list[FatoDREGerencialSchema] = []

        total_contratos_padrao = 80

        for mes_idx, cal in enumerate(calendario):
            data_fechamento = cal.data
            contratos_do_mes: list[FatoCarteiraMensalSchema] = []

            # 1. Caso Limítrofe 1: Atraso de 35 dias (Estágio 2 / SICR)
            contratos_do_mes.append(
                FatoCarteiraMensalSchema(
                    data_fechamento=data_fechamento,
                    id_contrato=9001,
                    id_associado=associados[0].id_associado,
                    id_linha=linhas[2].id_linha,  # Capital de Giro
                    data_concessao=date(2023, 5, 10),
                    saldo_devedor_contabil=Decimal("120000.00"),
                    dias_atraso=35,
                    saldo_vencido_over90=Decimal("0.00"),
                    indicador_renegociacao=0,
                    indicador_ativo_problematico=0,
                    estagio_contabil=2,
                    probabilidade_default_pd=Decimal("0.0450"),
                    loss_given_default_lgd=Decimal("0.5000"),
                    saldo_provisao_constituida=Decimal("2700.00"),
                )
            )

            # 2. Caso Limítrofe 2: Renegociação com 0 dias de atraso (Estágio 3 / AP)
            contratos_do_mes.append(
                FatoCarteiraMensalSchema(
                    data_fechamento=data_fechamento,
                    id_contrato=9002,
                    id_associado=associados[1].id_associado,
                    id_linha=linhas[0].id_linha,  # Pronaf Custeio
                    data_concessao=date(2023, 8, 15),
                    saldo_devedor_contabil=Decimal("85000.00"),
                    dias_atraso=0,
                    saldo_vencido_over90=Decimal("0.00"),
                    indicador_renegociacao=1,
                    indicador_ativo_problematico=1,
                    estagio_contabil=3,
                    probabilidade_default_pd=Decimal("0.2800"),
                    loss_given_default_lgd=Decimal("0.6000"),
                    saldo_provisao_constituida=Decimal("14280.00"),
                )
            )

            # 3. Caso Limítrofe 3: Atraso de 95 dias (Estágio 3 e Over90)
            contratos_do_mes.append(
                FatoCarteiraMensalSchema(
                    data_fechamento=data_fechamento,
                    id_contrato=9003,
                    id_associado=associados[2].id_associado,
                    id_linha=linhas[3].id_linha,  # Crédito Pessoal
                    data_concessao=date(2023, 11, 20),
                    saldo_devedor_contabil=Decimal("35000.00"),
                    dias_atraso=95,
                    saldo_vencido_over90=Decimal("35000.00"),
                    indicador_renegociacao=0,
                    indicador_ativo_problematico=1,
                    estagio_contabil=3,
                    probabilidade_default_pd=Decimal("0.4500"),
                    loss_given_default_lgd=Decimal("0.7000"),
                    saldo_provisao_constituida=Decimal("11025.00"),
                )
            )

            # 4. Contratos Regulares da Carteira
            for idx in range(1, total_contratos_padrao + 1):
                assoc = associados[idx % len(associados)]
                linha = linhas[idx % len(linhas)]
                id_contrato = 1000 + idx

                # Variação suave de saldo e atrasos para enriquecer séries temporais
                saldo_base = Decimal(str(30000 + (idx * 2500) + (mes_idx * 300)))
                saldo = saldo_base.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

                # Distribuição controlada de atrasos e estágios
                if idx % 15 == 0:
                    dias = 40
                    estagio = 2
                    ap = 0
                    reneg = 0
                    over90 = Decimal("0.00")
                    pd = Decimal("0.0520")
                    lgd = Decimal("0.5000")
                elif idx % 28 == 0:
                    dias = 110
                    estagio = 3
                    ap = 1
                    reneg = 0
                    over90 = saldo
                    pd = Decimal("0.5000")
                    lgd = Decimal("0.6500")
                else:
                    dias = 0
                    estagio = 1
                    ap = 0
                    reneg = 0
                    over90 = Decimal("0.00")
                    pd = Decimal("0.0110")
                    lgd = Decimal("0.4000")

                provisao = (saldo * pd * lgd).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

                contratos_do_mes.append(
                    FatoCarteiraMensalSchema(
                        data_fechamento=data_fechamento,
                        id_contrato=id_contrato,
                        id_associado=assoc.id_associado,
                        id_linha=linha.id_linha,
                        data_concessao=date(2023, 1, 15),
                        saldo_devedor_contabil=saldo,
                        dias_atraso=dias,
                        saldo_vencido_over90=over90,
                        indicador_renegociacao=reneg,
                        indicador_ativo_problematico=ap,
                        estagio_contabil=estagio,
                        probabilidade_default_pd=pd,
                        loss_given_default_lgd=lgd,
                        saldo_provisao_constituida=provisao,
                    )
                )

            # CONCILIAÇÃO ESTRITA: Balancete / DRE
            saldo_carteira_mes = sum(
                (c.saldo_devedor_contabil for c in contratos_do_mes),
                Decimal("0.00"),
            ).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

            provisao_carteira_mes = sum(
                (c.saldo_provisao_constituida for c in contratos_do_mes),
                Decimal("0.00"),
            ).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

            despesa_pdd = (provisao_carteira_mes * Decimal("0.09")).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            )
            recuperacao = (despesa_pdd * Decimal("0.12")).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            )
            despesa_liquida = despesa_pdd - recuperacao

            pr = (saldo_carteira_mes * Decimal("0.17")).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            )
            rwa = (saldo_carteira_mes * Decimal("0.72")).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            )
            lucro_mensal = saldo_carteira_mes * Decimal("0.035") + Decimal(str(mes_idx * 2500))
            sobras = lucro_mensal.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

            dre_total.append(
                FatoDREGerencialSchema(
                    data_fechamento=data_fechamento,
                    despesa_pdd_mes=despesa_pdd,
                    recuperacao_credito_mes=recuperacao,
                    despesa_liquida_pdd_mes=despesa_liquida,
                    saldo_carteira_total=saldo_carteira_mes,
                    sobras_liquidas_exercicio=sobras,
                    patrimonio_referencia_pr=pr,
                    rwa_risco_credito=rwa,
                )
            )

            carteira_total.extend(contratos_do_mes)

        return carteira_total, dre_total

    def gerar_base_completa(
        self,
    ) -> dict[str, list[Any]]:
        """Gera e retorna todas as tabelas sintéticas conciliadas.

        Returns:
            Dicionário contendo as coleções estruturadas:
                - 'd_Calendario': lista de DimCalendarioSchema
                - 'd_Associado': lista de DimAssociadoSchema
                - 'd_LinhaCredito': lista de DimLinhaCreditoSchema
                - 'f_Carteira_Mensal': lista de FatoCarteiraMensalSchema
                - 'f_DRE_Gerencial': lista de FatoDREGerencialSchema
        """
        cal = self.gerar_dim_calendario(ano_inicio=2024, anos_duracao=2)
        linhas = self.gerar_dim_linhas_credito()
        associados = self.gerar_dim_associados(total_associados=100)
        carteira, dre = self.gerar_carteira_e_dre_mensal(cal, associados, linhas)

        return {
            "d_Calendario": cal,
            "d_Associado": associados,
            "d_LinhaCredito": linhas,
            "f_Carteira_Mensal": carteira,
            "f_DRE_Gerencial": dre,
        }
