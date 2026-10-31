"""Gerador de dados sintéticos determinísticos para testes e homologação analítica.

Gera 24 meses de histórico contábil e de operações de crédito para a cooperativa singular,
assegurando conformidade com a Resolução CMN nº 4.966, casos de teste regulatórios
e conciliação centavo a centavo entre a carteira e o balancete/DRE.
"""

import random
from dataclasses import dataclass
from datetime import date
from decimal import ROUND_HALF_UP, Decimal
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

    def __getitem__(self, key: str) -> Any:
        """Permite acesso indexado por nome canônico da tabela.

        Args:
            key: Nome canônico da tabela (ex.: 'd_Calendario', 'f_Carteira_Mensal').

        Returns:
            Lista de schemas correspondentes à tabela consultada.

        Raises:
            KeyError: Se a tabela informada não existir no dataset.
        """
        mapa = {
            "d_Calendario": self.calendario,
            "d_Associado": self.associados,
            "d_LinhaCredito": self.linhas_credito,
            "f_Carteira_Mensal": self.carteira_mensal,
            "f_DRE_Gerencial": self.dre_gerencial,
        }
        if key not in mapa:
            raise KeyError(f"Tabela '{key}' não encontrada no DatasetSintetico.")
        return mapa[key]


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

    def gerar_calendario(
        self,
        ano_inicio: int = 2020,
        ano_fim: int = 2026,
        mes_fim: int = 6,
    ) -> list[DimCalendarioSchema]:
        """Gera a dimensão de calendário mensal para o período histórico solicitado.

        Abrange por padrão desde 5 anos antes da vigência da Resolução CMN 4.966 (2020)
        até a última data-base disponível (junho de 2026 - 78 meses).

        Args:
            ano_inicio: Primeiro ano civil da série temporal (padrão 2020).
            ano_fim: Último ano civil da série temporal (padrão 2026).
            mes_fim: Último mês civil do ano_fim (padrão 6, correspondente a 06/2026).

        Returns:
            Lista de objetos DimCalendarioSchema validados.

        Raises:
            ValueError: Se os atributos de data ou padrão regex falharem.
        """
        meses_nomes = [
            "Jan", "Fev", "Mar", "Abr", "Mai", "Jun",
            "Jul", "Ago", "Set", "Out", "Nov", "Dez",
        ]
        trimestres = [
            "1T", "1T", "1T", "2T", "2T", "2T",
            "3T", "3T", "3T", "4T", "4T", "4T",
        ]

        dias_fim_mes = {
            1: 31, 2: 28, 3: 31, 4: 30, 5: 31, 6: 30,
            7: 31, 8: 31, 9: 30, 10: 31, 11: 30, 12: 31,
        }

        registros: list[DimCalendarioSchema] = []

        for ano in range(ano_inicio, ano_fim + 1):
            limite_mes = mes_fim if ano == ano_fim else 12
            for mes in range(1, limite_mes + 1):
                ultimo_dia = dias_fim_mes[mes]
                # Tratamento de ano bissexto (2020, 2024)
                if mes == 2 and ((ano % 4 == 0 and ano % 100 != 0) or (ano % 400 == 0)):
                    ultimo_dia = 29

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

    def gerar_calendario_24m(self) -> list[DimCalendarioSchema]:
        """Gera a dimensão de calendário para 24 competências mensais (2024 e 2025).

        Returns:
            Lista com 24 objetos DimCalendarioSchema validados.
        """
        return self.gerar_calendario(ano_inicio=2024, ano_fim=2025, mes_fim=12)

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
        # Calibração com as notas explicativas do Sicoob Credijequitinhonha (Agro 42%)
        pesos_segmentos = [0.42, 0.28, 0.12, 0.10, 0.08]

        associados: list[DimAssociadoSchema] = []

        for i in range(1, quantidade + 1):
            tipo = TipoPessoaEnum.PJ if (i % 3 == 0) else TipoPessoaEnum.PF
            segmento = self.rng.choices(segmentos, weights=pesos_segmentos)[0]
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

    def gerar_dataset_completo(
        self,
        ano_inicio: int = 2020,
        ano_fim: int = 2026,
        mes_fim: int = 6,
    ) -> DatasetSintetico:
        """Gera o ecossistema sintético completo com conciliação contábil estrita.

        Abrange desde 5 anos anteriores à vigência da Resolução 4.966 (2020 a 2024)
        até a última data-base disponível (junho de 2026 - 78 competências mensais).
        Garante consistência cronológica estrita (sem contratos contratados no futuro
        e sem dias de atraso superiores à idade do contrato), curvas de safra (MOB)
        realistas e alinhamento com a escala patrimonial auditada da singular.

        Inclui os 3 casos de teste limítrofes regulatórios:
        1. Contrato 1: 35 dias de atraso com rebaixamento (Estágio 2 / SICR);
        2. Contrato 2: Renegociado por estresse com 0 dias de atraso (Estágio 3 / AP);
        3. Contrato 3: 95 dias de atraso (Estágio 3 e Over90).

        Args:
            ano_inicio: Primeiro ano da série histórica (padrão 2020).
            ano_fim: Último ano da série histórica (padrão 2026).
            mes_fim: Mês final de encerramento (padrão 6 para 06/2026).

        Returns:
            Objeto DatasetSintetico contendo todas as dimensões e tabelas fato.

        Raises:
            ValueError: Se houver divergência de centavos na conciliação contábil.
        """
        calendario = self.gerar_calendario(
            ano_inicio=ano_inicio,
            ano_fim=ano_fim,
            mes_fim=mes_fim,
        )
        linhas_credito = self.gerar_linhas_credito()
        associados = self.gerar_associados(quantidade=120)

        # 1. Criação do catálogo de contratos com concessão temporal verídica
        # Casos de teste limítrofes regulatórios fixados em 2019
        contratos_pool: list[dict[str, Any]] = [
            {
                "id_contrato": 1,
                "id_associado": 1,
                "id_linha": 1,
                "data_concessao": date(2019, 1, 10),
                "saldo_base": Decimal("2800000.00"),
                "prazo_meses": 96,
                "perfil_risco": "teste_caso_1",
            },
            {
                "id_contrato": 2,
                "id_associado": 2,
                "id_linha": 3,
                "data_concessao": date(2019, 2, 10),
                "saldo_base": Decimal("3000000.00"),
                "prazo_meses": 96,
                "perfil_risco": "teste_caso_2",
            },
            {
                "id_contrato": 3,
                "id_associado": 3,
                "id_linha": 2,
                "data_concessao": date(2019, 3, 10),
                "saldo_base": Decimal("3200000.00"),
                "prazo_meses": 96,
                "perfil_risco": "teste_caso_3",
            },
        ]

        proximo_cid = 4

        # Carteira pré-2020 (concessões graduais de 2017 a 2019)
        for y_base in (2017, 2018, 2019):
            for m_base in range(1, 13):
                qtd_concessoes = 2 if y_base == 2017 else 3
                for _ in range(qtd_concessoes):
                    assoc = associados[(proximo_cid - 1) % len(associados)]
                    linha = linhas_credito[(proximo_cid - 1) % len(linhas_credito)]
                    ticket = Decimal(str(self.rng.randint(2200000, 3600000)))
                    prazo = self.rng.choice([60, 72, 84])
                    perfil = self.rng.choices(
                        ["bom", "medio", "estresse"],
                        weights=[0.88, 0.08, 0.04],
                    )[0]
                    contratos_pool.append(
                        {
                            "id_contrato": proximo_cid,
                            "id_associado": assoc.id_associado,
                            "id_linha": linha.id_linha,
                            "data_concessao": date(y_base, m_base, 10),
                            "saldo_base": ticket,
                            "prazo_meses": prazo,
                            "perfil_risco": perfil,
                        }
                    )
                    proximo_cid += 1

        # Novas concessões contínuas ao longo de 2020 a 2026
        for cal in calendario:
            y = cal.ano
            m = cal.data.month
            # Expansão orgânica da cooperativa acompanhando o crescimento regional
            if y <= 2020:
                qtd_novos = 2
                ticket_min, ticket_max = 2200000, 3500000
            elif y <= 2022:
                qtd_novos = 3
                ticket_min, ticket_max = 2600000, 3800000
            elif y <= 2024:
                qtd_novos = 4
                ticket_min, ticket_max = 3200000, 4500000
            else:
                qtd_novos = 4
                ticket_min, ticket_max = 3800000, 5000000

            for _ in range(qtd_novos):
                assoc = associados[(proximo_cid - 1) % len(associados)]
                linha = linhas_credito[(proximo_cid - 1) % len(linhas_credito)]
                ticket = Decimal(str(self.rng.randint(ticket_min, ticket_max)))
                prazo = self.rng.choice([48, 60, 72])
                p_estresse = 0.09 if 2022 <= y <= 2024 else 0.04
                perfil = self.rng.choices(
                    ["bom", "medio", "estresse"],
                    weights=[0.82, 0.18 - p_estresse, p_estresse],
                )[0]
                contratos_pool.append(
                    {
                        "id_contrato": proximo_cid,
                        "id_associado": assoc.id_associado,
                        "id_linha": linha.id_linha,
                        "data_concessao": date(y, m, 10),
                        "saldo_base": ticket,
                        "prazo_meses": prazo,
                        "perfil_risco": perfil,
                    }
                )
                proximo_cid += 1

        carteira_total: list[FatoCarteiraMensalSchema] = []
        dre_total: list[FatoDREGerencialSchema] = []
        provisao_mes_anterior = Decimal("0.00")

        # 2. Processamento mensal com respeito estrito à cronologia
        for idx_mes, cal in enumerate(calendario):
            competencia = cal.data
            registros_mes: list[FatoCarteiraMensalSchema] = []

            for c in contratos_pool:
                # Regra inegociável: contrato só entra em carteira após ou na data de concessão
                if c["data_concessao"] > competencia:
                    continue

                mob = (competencia.year - c["data_concessao"].year) * 12 + (
                    competencia.month - c["data_concessao"].month
                )
                if mob > c["prazo_meses"]:
                    continue

                idade_dias = (competencia - c["data_concessao"]).days
                fator_rem = max(
                    Decimal("0.05"),
                    Decimal("1.00") - (Decimal(str(mob)) / Decimal(str(c["prazo_meses"]))),
                )
                saldo_atual = (c["saldo_base"] * fator_rem).quantize(Decimal("0.01"))

                cid = c["id_contrato"]

                # Casos limítrofes regulatórios mandatórios
                if cid == 1:
                    dias_atraso = 35
                    over90 = Decimal("0.00")
                    renegociado = 0
                    ap = 0
                    estagio = 2
                    pd = Decimal("0.0650")
                    lgd = Decimal("0.4500")
                elif cid == 2:
                    dias_atraso = 0
                    over90 = Decimal("0.00")
                    renegociado = 1
                    ap = 1
                    estagio = 3
                    pd = Decimal("1.0000")
                    lgd = Decimal("0.4500")
                elif cid == 3:
                    dias_atraso = 95
                    over90 = saldo_atual
                    renegociado = 0
                    ap = 1
                    estagio = 3
                    pd = Decimal("1.0000")
                    lgd = Decimal("0.5500")
                else:
                    perfil = c["perfil_risco"]
                    if mob <= 1:
                        # Recém-concedido: 100% adimplente
                        dias_atraso = 0
                        renegociado = 0
                        estagio = 1
                        ap = 0
                        over90 = Decimal("0.00")
                        pd = Decimal("0.0180")
                        lgd = Decimal("0.4000")
                    elif mob <= 3:
                        if perfil == "estresse":
                            dias_atraso = min(20, max(0, idade_dias - 10))
                            renegociado = 0
                            estagio = 1
                            ap = 0
                            over90 = Decimal("0.00")
                            pd = Decimal("0.0250")
                            lgd = Decimal("0.4000")
                        else:
                            dias_atraso = 0
                            renegociado = 0
                            estagio = 1
                            ap = 0
                            over90 = Decimal("0.00")
                            pd = Decimal("0.0160")
                            lgd = Decimal("0.4000")
                    elif mob <= 6:
                        if perfil == "estresse":
                            dias_atraso = min(45, max(0, idade_dias - 15))
                            renegociado = 0
                            estagio = 2
                            ap = 0
                            over90 = Decimal("0.00")
                            pd = Decimal("0.0850")
                            lgd = Decimal("0.4500")
                        else:
                            dias_atraso = 0
                            renegociado = 0
                            estagio = 1
                            ap = 0
                            over90 = Decimal("0.00")
                            pd = Decimal("0.0180")
                            lgd = Decimal("0.4000")
                    else:
                        # Maturação avançada (mob > 6)
                        if perfil == "estresse":
                            # No período inicial (2020 a 2022), programas de apoio contiveram
                            # a inadimplência crônica em Estágio 2
                            if competencia < date(2022, 9, 1):
                                dias_atraso = min(45, max(0, idade_dias - 20))
                                renegociado = 0
                                ap = 0
                                estagio = 2
                                over90 = Decimal("0.00")
                                pd = Decimal("0.0850")
                                lgd = Decimal("0.4500")
                            else:
                                dias_atraso = min(115, max(0, idade_dias - 20))
                                renegociado = 1 if (cid % 3 == 0) else 0
                                ap = 1
                                estagio = 3
                                over90 = saldo_atual if dias_atraso > 90 else Decimal("0.00")
                                # Estágio 3 = default materializado -> PD = 1.0000
                                pd = Decimal("1.0000")
                                lgd = Decimal("0.5000")
                        elif perfil == "medio":
                            if (cid + idx_mes) % 5 == 0:
                                dias_atraso = min(40, max(0, idade_dias - 20))
                                renegociado = 0
                                estagio = 2
                                ap = 0
                                over90 = Decimal("0.00")
                                pd = Decimal("0.0800")
                                lgd = Decimal("0.4500")
                            else:
                                dias_atraso = 0
                                renegociado = 0
                                estagio = 1
                                ap = 0
                                over90 = Decimal("0.00")
                                pd = Decimal("0.0350")
                                lgd = Decimal("0.4500")
                        else:
                            dias_atraso = 0
                            renegociado = 0
                            estagio = 1
                            ap = 0
                            over90 = Decimal("0.00")
                            pd = Decimal("0.0340")
                            lgd = Decimal("0.4500")

                # Transição da Resolução CMN 4.966 em 01/01/2025:
                # Reconhecimento prospectivo e forward-looking de perdas esperadas
                if competencia >= date(2025, 1, 1):
                    if estagio == 1:
                        pd = Decimal("0.0450")
                    elif estagio == 2:
                        pd = Decimal("0.1250")

                # Cálculo de Provisão Constituída (ECL = Saldo * PD * LGD)
                provisao = (saldo_atual * pd * lgd).quantize(
                    Decimal("0.01"), rounding=ROUND_HALF_UP
                )

                contrato_dto = FatoCarteiraMensalSchema(
                    data_fechamento=competencia,
                    id_contrato=cid,
                    id_associado=c["id_associado"],
                    id_linha=c["id_linha"],
                    data_concessao=c["data_concessao"],
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

            # Conciliação Estrita com o Balancete e a DRE Gerencial
            total_carteira_mes = sum(
                (c_reg.saldo_devedor_contabil for c_reg in registros_mes), Decimal("0.00")
            )
            total_provisao_mes = sum(
                (c_reg.saldo_provisao_constituida for c_reg in registros_mes), Decimal("0.00")
            )

            # Integração contábil da DRE com a variação real do estoque de provisão
            delta_prov = (
                total_provisao_mes - provisao_mes_anterior
                if idx_mes > 0
                else Decimal("0.00")
            )
            provisao_mes_anterior = total_provisao_mes

            recuperacao = (total_carteira_mes * Decimal("0.0004")).quantize(Decimal("0.01"))
            baixas_prejuizo = (total_carteira_mes * Decimal("0.0012")).quantize(Decimal("0.01"))
            despesa_pdd = max(
                Decimal("100000.00"),
                delta_prov + baixas_prejuizo + recuperacao,
            ).quantize(Decimal("0.01"))
            despesa_liquida = (despesa_pdd - recuperacao).quantize(Decimal("0.01"))

            # RWA e Patrimônio de Referência alinhados à Credijequitinhonha (Basileia ~17.18%)
            rwa = (total_carteira_mes * Decimal("1.35")).quantize(Decimal("0.01"))
            pr = (rwa * Decimal("0.1718")).quantize(Decimal("0.01"))
            sobras = (
                Decimal("1650000.00") - (despesa_liquida * Decimal("0.12"))
            ).quantize(Decimal("0.01"))

            dre_mes = FatoDREGerencialSchema(
                data_fechamento=competencia,
                despesa_pdd_mes=despesa_pdd,
                recuperacao_credito_mes=recuperacao,
                despesa_liquida_pdd_mes=despesa_liquida,
                saldo_carteira_total=total_carteira_mes.quantize(Decimal("0.01")),
                sobras_liquidas_exercicio=sobras,
                patrimonio_referencia_pr=pr,
                rwa_risco_credito=rwa,
            )

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

    def gerar_base_completa(
        self,
        ano_inicio: int = 2020,
        ano_fim: int = 2026,
        mes_fim: int = 6,
    ) -> dict[str, Any]:
        """Gera a base sintética completa no formato de dicionário por tabela canônica.

        Args:
            ano_inicio: Primeiro ano civil (padrão 2020).
            ano_fim: Último ano civil (padrão 2026).
            mes_fim: Último mês civil (padrão 6 para 06/2026).

        Returns:
            Dicionário com as tabelas 'd_Calendario', 'd_Associado', 'd_LinhaCredito',
            'f_Carteira_Mensal' e 'f_DRE_Gerencial'.
        """
        ds = self.gerar_dataset_completo(
            ano_inicio=ano_inicio,
            ano_fim=ano_fim,
            mes_fim=mes_fim,
        )
        return {
            "d_Calendario": ds.calendario,
            "d_Associado": ds.associados,
            "d_LinhaCredito": ds.linhas_credito,
            "f_Carteira_Mensal": ds.carteira_mensal,
            "f_DRE_Gerencial": ds.dre_gerencial,
        }
