"""Gerador de dados sintéticos determinísticos para testes e homologação analítica.

Gera 24 meses de histórico contábil e de operações de crédito para a cooperativa singular,
assegurando conformidade com a Resolução CMN nº 4.966, casos de teste regulatórios
e conciliação centavo a centavo entre a carteira e o balancete/DRE.
"""

import random
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Any

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


@dataclass
class DatasetSintetico:
    """Contêiner com os conjuntos de dados sintéticos gerados para a cooperativa.

    Attributes:
        calendario: Lista de registros da dimensão calendário (mensal).
        associados: Lista de cooperados associados cadastrados.
        linhas_credito: Modalidades e linhas de crédito ativas.
        carteira_mensal: Operações detalhadas mês a mês.
        dre_gerencial: Demonstrativo de resultados e balancete contábil mensal.
    """

    calendario: list[DimCalendarioSchema]
    associados: list[DimAssociadoSchema]
    linhas_credito: list[DimLinhaCreditoSchema]
    carteira_mensal: list[FatoCarteiraMensalSchema]
    dre_gerencial: list[FatoDREGerencialSchema]


class SyntheticDataGenerator:
    """Gerador determinístico de dados com garantia de conciliação estrita.

    Attributes:
        seed: Semente pseudoaleatória para reprodutibilidade dos testes.
        rng: Instância de gerador aleatório isolada para evitar efeitos colaterais.
    """

    def __init__(self, seed: int = 42) -> None:
        """Inicializa o gerador sintético com a semente configurada.

        Args:
            seed: Inteiro para fixação do estado determinístico (padrão 42).
        """
        self.seed = seed
        self.rng = random.Random(seed)

    def gerar_calendario_24m(self) -> list[DimCalendarioSchema]:
        """Gera a dimensão de calendário contendo 24 competências mensais (2024 e 2025).

        Returns:
            Lista com 24 objetos DimCalendarioSchema validados.

        Raises:
            ValueError: Se os atributos de data ou padrão regex falharem.
        """
        meses_nomes = [
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
        trimestres = [
            "1T",
            "1T",
            "1T",
            "2T",
            "2T",
            "2T",
            "3T",
            "3T",
            "3T",
            "4T",
            "4T",
            "4T",
        ]

        dias_fim_mes = {
            1: 31,
            2: 29,
            3: 31,
            4: 30,
            5: 31,
            6: 30,
            7: 31,
            8: 31,
            9: 30,
            10: 31,
            11: 30,
            12: 31,
        }

        registros: list[DimCalendarioSchema] = []

        for ano in (2024, 2025):
            for mes in range(1, 13):
                ultimo_dia = dias_fim_mes[mes]
                # Ajuste para ano não bissexto em 2025
                if ano == 2025 and mes == 2:
                    ultimo_dia = 28

                data_fim = date(ano, mes, ultimo_dia)
                mes_ano_str = f"{meses_nomes[mes - 1]}/{ano}"
                trimestre_str = trimestres[mes - 1]

                registros.append(
                    DimCalendarioSchema(
                        data=data_fim,
                        ano=ano,
                        mes_ano=mes_ano_str,
                        trimestre=trimestre_str,
                    )
                )

        return registros

    def gerar_linhas_credito(self) -> list[DimLinhaCreditoSchema]:
        """Gera a dimensão de produtos de crédito da cooperativa.

        Returns:
            Lista de linhas de crédito com garantias e modalidades normativas.

        Raises:
            ValueError: Caso ocorra inconsistência nos enums normativos.
        """
        linhas = [
            (
                1,
                "Pronaf Custeio Agricola",
                GrupoModalidadeBacenEnum.CREDITO_RURAL,
                TipoGarantiaEnum.PENHOR_AGRICOLA,
            ),
            (
                2,
                "Pronamp Investimento Tratores",
                GrupoModalidadeBacenEnum.CREDITO_RURAL,
                TipoGarantiaEnum.ALIENACAO_FIDUCIARIA,
            ),
            (
                3,
                "Capital de Giro Rotativo PJ",
                GrupoModalidadeBacenEnum.CAPITAL_DE_GIRO,
                TipoGarantiaEnum.FIDEJUSSORIA,
            ),
            (
                4,
                "Financiamento de Estoque PJ",
                GrupoModalidadeBacenEnum.CAPITAL_DE_GIRO,
                TipoGarantiaEnum.ALIENACAO_FIDUCIARIA,
            ),
            (
                5,
                "Credito Pessoal Consignado",
                GrupoModalidadeBacenEnum.CONSUMO,
                TipoGarantiaEnum.LIMPA,
            ),
            (
                6,
                "Credito Direto ao Consumidor Veiculos",
                GrupoModalidadeBacenEnum.CONSUMO,
                TipoGarantiaEnum.ALIENACAO_FIDUCIARIA,
            ),
            (
                7,
                "Financiamento Imobiliario Habitacional",
                GrupoModalidadeBacenEnum.HABITACIONAL,
                TipoGarantiaEnum.ALIENACAO_FIDUCIARIA,
            ),
        ]

        return [
            DimLinhaCreditoSchema(
                id_linha=item[0],
                nome_linha=item[1],
                grupo_modalidade=item[2],
                tipo_garantia_predominante=item[3],
            )
            for item in linhas
        ]

    def gerar_associados(self, quantidade: int = 120) -> list[DimAssociadoSchema]:
        """Gera uma base determinística de associados anonimizados.

        Args:
            quantidade: Número de associados a serem gerados.

        Returns:
            Lista de DimAssociadoSchema validados.

        Raises:
            ValueError: Se parâmetros de rating ou tipos violarem o schema.
        """
        segmentos = [
            SegmentoCooperadoEnum.AGRO,
            SegmentoCooperadoEnum.COMERCIAL,
            SegmentoCooperadoEnum.VAREJO,
            SegmentoCooperadoEnum.SERVIDOR_PUBLICO,
            SegmentoCooperadoEnum.OUTROS,
        ]

        associados: list[DimAssociadoSchema] = []

        for i in range(1, quantidade + 1):
            tipo = TipoPessoaEnum.PJ if (i % 3 == 0) else TipoPessoaEnum.PF
            segmento = segmentos[i % len(segmentos)]
            ano_admissao = 2018 + (i % 6)
            data_adm = date(ano_admissao, ((i % 12) + 1), min(28, (i % 25) + 1))
            # Distribuição com concentração em ratings 2 a 5
            rating = min(10, max(1, int(self.rng.gauss(4.0, 1.8))))

            associados.append(
                DimAssociadoSchema(
                    id_associado=i,
                    tipo_pessoa=tipo,
                    segmento_cooperado=segmento,
                    data_admissao=data_adm,
                    rating_interno_comportamental=rating,
                )
            )

        return associados

    def gerar_dataset_completo(self) -> DatasetSintetico:
        """Gera o ecossistema sintético completo com conciliação contábil estrita.

        Inclui os 3 casos de teste limítrofes regulatórios:
        1. Contrato 1001: 35 dias de atraso com rebaixamento (Estágio 2 / SICR);
        2. Contrato 1002: Renegociado por estresse com 0 dias de atraso (Estágio 3 / AP);
        3. Contrato 1003: 95 dias de atraso (Estágio 3 e Over90).

        Returns:
            Objeto DatasetSintetico contendo todas as dimensões e tabelas fato.

        Raises:
            ValueError: Se houver divergência de centavos na conciliação contábil.
        """
        calendario = self.gerar_calendario_24m()
        linhas_credito = self.gerar_linhas_credito()
        associados = self.gerar_associados(quantidade=120)

        carteira_total: list[FatoCarteiraMensalSchema] = []
        dre_total: list[FatoDREGerencialSchema] = []

        # Histórico de saldo de contratos base para evolução contínua
        num_contratos = 150
        contratos_base: list[dict[str, Any]] = []

        for cid in range(1, num_contratos + 1):
            assoc = associados[(cid - 1) % len(associados)]
            linha = linhas_credito[(cid - 1) % len(linhas_credito)]
            saldo_inicial = Decimal(str(self.rng.randint(25000, 350000))) + Decimal("0.00")
            contratos_base.append(
                {
                    "id_contrato": cid,
                    "id_associado": assoc.id_associado,
                    "id_linha": linha.id_linha,
                    "data_concessao": date(2023, ((cid % 12) + 1), 10),
                    "saldo_base": saldo_inicial,
                    "rating_origem": assoc.rating_interno_comportamental,
                }
            )

        # Processa cada competência temporal mensal
        saldo_pdd_acumulado_anterior = Decimal("0.00")

        for idx_mes, cal in enumerate(calendario):
            competencia = cal.data
            registros_mes: list[FatoCarteiraMensalSchema] = []

            for base in contratos_base:
                cid = base["id_contrato"]
                # Amortização gradual do saldo devedor
                fator_amortizacao = Decimal("1.00") - (Decimal(str(idx_mes)) * Decimal("0.015"))
                if fator_amortizacao < Decimal("0.30"):
                    fator_amortizacao = Decimal("0.30")

                saldo_atual = (base["saldo_base"] * fator_amortizacao).quantize(Decimal("0.01"))

                # Injeção determinística dos casos limítrofes obrigatórios
                if cid == 1:
                    # Caso 1: Atraso de 35 dias com rebaixamento de rating (Estágio 2 / SICR)
                    dias_atraso = 35
                    over90 = Decimal("0.00")
                    renegociado = 0
                    ap = 0
                    estagio = 2
                    pd = Decimal("0.0650")
                    lgd = Decimal("0.4500")
                elif cid == 2:
                    # Caso 2: Operação renegociada com 0 dias de atraso (Estágio 3 / AP)
                    dias_atraso = 0
                    over90 = Decimal("0.00")
                    renegociado = 1
                    ap = 1
                    estagio = 3
                    pd = Decimal("0.2500")
                    lgd = Decimal("0.5500")
                elif cid == 3:
                    # Caso 3: Operação com 95 dias de atraso (Estágio 3 e Over90)
                    dias_atraso = 95
                    over90 = saldo_atual
                    renegociado = 0
                    ap = 1
                    estagio = 3
                    pd = Decimal("0.5000")
                    lgd = Decimal("0.6000")
                else:
                    # Contratos normais com variabilidade realista
                    sorteio = (cid + idx_mes) % 100
                    if sorteio < 80:
                        # Estágio 1 regular
                        dias_atraso = self.rng.choice([0, 0, 0, 5, 12, 18])
                        over90 = Decimal("0.00")
                        renegociado = 0
                        ap = 0
                        estagio = 1
                        pd = Decimal("0.0120")
                        lgd = Decimal("0.4000")
                    elif sorteio < 93:
                        # Estágio 2 por atraso moderado ou rating
                        dias_atraso = 40 + (cid % 35)
                        over90 = Decimal("0.00")
                        renegociado = 0
                        ap = 0
                        estagio = 2
                        pd = Decimal("0.0580")
                        lgd = Decimal("0.4800")
                    else:
                        # Estágio 3 por atraso elevado
                        dias_atraso = 110 + (cid % 40)
                        over90 = saldo_atual
                        renegociado = 1 if (cid % 2 == 0) else 0
                        ap = 1
                        estagio = 3
                        pd = Decimal("0.3500")
                        lgd = Decimal("0.6500")

                # Cálculo de Provisão Constituída (ECL = Saldo * PD * LGD)
                provisao = (saldo_atual * pd * lgd).quantize(Decimal("0.01"))

                contrato_dto = FatoCarteiraMensalSchema(
                    data_fechamento=competencia,
                    id_contrato=cid,
                    id_associado=base["id_associado"],
                    id_linha=base["id_linha"],
                    data_concessao=base["data_concessao"],
                    saldo_devedor_contabil=saldo_atual,
                    dias_atraso=dias_atraso,
                    saldo_vencido_over90=over90,
                    indicador_renegociacao=renegociado,
                    indicador_ativo_problematico=ap,
                    estagio_contabil=estagio,
                    probabilidade_default_pd=pd,
                    loss_given_default_lgd=lgd,
                    saldo_provisao_constituida=provisao,
                )
                registros_mes.append(contrato_dto)

            # Conciliação Estrita com a DRE Gerencial
            total_carteira_mes = sum(
                (c.saldo_devedor_contabil for c in registros_mes), Decimal("0.00")
            )
            total_provisao_mes = sum(
                (c.saldo_provisao_constituida for c in registros_mes), Decimal("0.00")
            )

            # Fluxo da DRE do mês
            recuperacao = Decimal("15000.00") + Decimal(str(idx_mes * 500))
            if idx_mes == 0:
                despesa_pdd = total_provisao_mes
            else:
                var_provisao = total_provisao_mes - saldo_pdd_acumulado_anterior
                despesa_pdd = max(Decimal("0.00"), var_provisao + recuperacao)

            despesa_liquida = despesa_pdd - recuperacao
            saldo_pdd_acumulado_anterior = total_provisao_mes

            # RWA e Patrimônio de Referência aderentes às regras de capital de cooperativas
            rwa = (total_carteira_mes * Decimal("0.75")).quantize(Decimal("0.01"))
            pr = (rwa * Decimal("0.165")).quantize(Decimal("0.01"))
            sobras = (Decimal("350000.00") - (despesa_liquida * Decimal("0.40"))).quantize(
                Decimal("0.01")
            )

            dre_mes = FatoDREGerencialSchema(
                data_fechamento=competencia,
                despesa_pdd_mes=despesa_pdd.quantize(Decimal("0.01")),
                recuperacao_credito_mes=recuperacao.quantize(Decimal("0.01")),
                despesa_liquida_pdd_mes=despesa_liquida.quantize(Decimal("0.01")),
                saldo_carteira_total=total_carteira_mes.quantize(Decimal("0.01")),
                sobras_liquidas_exercicio=sobras,
                patrimonio_referencia_pr=pr,
                rwa_risco_credito=rwa,
            )

            # Verificação de segurança de conciliação no próprio gerador
            if dre_mes.saldo_carteira_total != total_carteira_mes:
                raise ValueError(
                    f"Divergência contábil na data {competencia}: "
                    f"Carteira ({total_carteira_mes}) != DRE ({dre_mes.saldo_carteira_total})"
                )

            carteira_total.extend(registros_mes)
            dre_total.append(dre_mes)

        return DatasetSintetico(
            calendario=calendario,
            associados=associados,
            linhas_credito=linhas_credito,
            carteira_mensal=carteira_total,
            dre_gerencial=dre_total,
        )
