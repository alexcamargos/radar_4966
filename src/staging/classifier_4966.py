"""Motor determinístico de classificação e enquadramento da Resolução CMN nº 4.966.

Implementa regras de transição de Estágios 1, 2 (SICR) e 3 (Ativo Problemático),
mensuração de Perda Esperada (ECL) e geração de matriz de safras (Vintage Analysis).
"""

from collections import defaultdict
from decimal import ROUND_HALF_UP, Decimal
from typing import Any

from src.schemas.facts import FatoCarteiraMensalSchema


class MotorClassificador4966:
    """Classificador regulatório e quantitativo conforme Resolução CMN 4.966.

    Aplica critérios objetivos para segregação da carteira em Estágios 1, 2 e 3,
    determinação de Ativo Problemático (AP) e cálculo de ECL (Expected Credit Loss).
    """

    @staticmethod
    def classificar_operacao(
        dias_atraso: int,
        indicador_renegociacao: int,
        rating_comportamental_atual: int,
        rating_origem: int | None = None,
        pd_atual: Decimal | None = None,
        pd_origem: Decimal | None = None,
        indicio_objetivo_perda: bool = False,
    ) -> tuple[int, int]:
        """Classifica uma operação individual em seu respectivo Estágio e status de AP.

        Regras de Negócio Determinísticas:
        - Estágio 3 (Ativo Problemático):
            * dias_atraso > 90 OU
            * indicador_renegociacao == 1 OU
            * rating_comportamental_atual == 10 OU
            * indicio_objetivo_perda == True
        - Estágio 2 (Aumento Significativo de Risco - SICR):
            * 31 <= dias_atraso <= 90 OU
            * (rating_origem is not None e rating_comportamental_atual - rating_origem >= 2) OU
            * (pd_origem is not None e pd_atual is not None e pd_origem > 0 e
               pd_atual / pd_origem >= Decimal("2.5"))
        - Estágio 1 (Risco Inicial):
            * Demais operações adimplentes ou com atraso <= 30 dias sem SICR.

        Args:
            dias_atraso: Quantidade de dias em atraso no pagamento (DPD).
            indicador_renegociacao: 1 se renegociada por estresse financeiro, 0 cc.
            rating_comportamental_atual: Rating interno atual (escala 1 a 10).
            rating_origem: Rating interno apurado no momento da concessão da operação.
            pd_atual: Probabilidade de default atual estimada.
            pd_origem: Probabilidade de default inicial na concessão.
            indicio_objetivo_perda: Booleano indicando insolvência, falência ou perda.

        Returns:
            Tupla contendo (estagio_contabil, indicador_ativo_problematico).

        Raises:
            ValueError: Se dias_atraso < 0 ou rating_comportamental_atual fora de 1..10.
        """
        if dias_atraso < 0:
            raise ValueError("dias_atraso não pode ser negativo.")
        if not (1 <= rating_comportamental_atual <= 10):
            raise ValueError("rating_comportamental_atual deve estar no intervalo de 1 a 10.")

        # 1. Regra de Estágio 3 (Ativo Problemático)
        if (
            dias_atraso > 90
            or indicador_renegociacao == 1
            or rating_comportamental_atual == 10
            or indicio_objetivo_perda
        ):
            return 3, 1

        # 2. Regra de Estágio 2 (SICR)
        sicr_atraso = 31 <= dias_atraso <= 90

        sicr_rating = False
        if rating_origem is not None:
            sicr_rating = (rating_comportamental_atual - rating_origem) >= 2

        sicr_pd = False
        if pd_atual is not None and pd_origem is not None and pd_origem > Decimal("0.0000"):
            razao_pd = pd_atual / pd_origem
            sicr_pd = razao_pd >= Decimal("2.5")

        if sicr_atraso or sicr_rating or sicr_pd:
            return 2, 0

        # 3. Estágio 1
        return 1, 0

    @staticmethod
    def calcular_perda_esperada(
        saldo_devedor_contabil: Decimal,
        estagio_contabil: int,
        probabilidade_default_pd: Decimal,
        loss_given_default_lgd: Decimal,
    ) -> Decimal:
        """Calcula o valor monetário da provisão de Perda Esperada (ECL).

        Fórmulas:
        - Estágio 1: Saldo * PD_12M * LGD
        - Estágio 2 e 3: Saldo * PD_Lifetime * LGD

        Args:
            saldo_devedor_contabil: Saldo contábil da dívida.
            estagio_contabil: Estágio enquadrado (1, 2 ou 3).
            probabilidade_default_pd: Probabilidade de default (12M para Est. 1, Lifetime cc).
            loss_given_default_lgd: Severidade da perda estimada.

        Returns:
            Valor de provisão provisionada com arredondamento monetário (duas casas decimais).

        Raises:
            ValueError: Se estagio_contabil não estiver entre 1 e 3.
        """
        if estagio_contabil not in (1, 2, 3):
            raise ValueError("estagio_contabil deve ser 1, 2 ou 3.")

        ecl = saldo_devedor_contabil * probabilidade_default_pd * loss_given_default_lgd
        return ecl.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    @classmethod
    def classificar_carteira(
        cls,
        carteira: list[FatoCarteiraMensalSchema],
        rating_origem_map: dict[int, int] | None = None,
        pd_origem_map: dict[int, Decimal] | None = None,
        rating_atual_map: dict[int, int] | None = None,
    ) -> list[FatoCarteiraMensalSchema]:
        """Aplica o enquadramento em massa para uma lista de operações de carteira.

        Args:
            carteira: Lista de contratos conforme FatoCarteiraMensalSchema.
            rating_origem_map: Dicionário mapeando id_contrato para rating de concessão.
            pd_origem_map: Dicionário mapeando id_contrato para PD de concessão.
            rating_atual_map: Dicionário mapeando id_contrato para rating comportamental atual.

        Returns:
            Lista de contratos com estágio, AP e saldo de provisão reclassificados.
        """
        resultado: list[FatoCarteiraMensalSchema] = []
        rating_map = rating_origem_map or {}
        pd_map = pd_origem_map or {}
        r_atual_map = rating_atual_map or {}

        for c in carteira:
            r_origem = rating_map.get(c.id_contrato)
            p_origem = pd_map.get(c.id_contrato)
            r_atual = r_atual_map.get(
                c.id_contrato, 10 if c.estagio_contabil == 3 else 3
            )

            estagio, ap = cls.classificar_operacao(
                dias_atraso=c.dias_atraso,
                indicador_renegociacao=c.indicador_renegociacao,
                rating_comportamental_atual=r_atual,
                rating_origem=r_origem,
                pd_atual=c.probabilidade_default_pd,
                pd_origem=p_origem,
            )

            # Para Estágio 3 (default), a probabilidade de default é 1.0000 (100%)
            pd_calculo = (
                Decimal("1.0000") if estagio == 3 else c.probabilidade_default_pd
            )

            # Provisão esperada calculada
            prov = cls.calcular_perda_esperada(
                saldo_devedor_contabil=c.saldo_devedor_contabil,
                estagio_contabil=estagio,
                probabilidade_default_pd=pd_calculo,
                loss_given_default_lgd=c.loss_given_default_lgd,
            )

            # Se for over90, preenche saldo vencido
            over90 = c.saldo_devedor_contabil if c.dias_atraso > 90 else Decimal("0.00")

            dados_dict = c.model_dump()
            dados_dict["estagio_contabil"] = estagio
            dados_dict["indicador_ativo_problematico"] = ap
            dados_dict["probabilidade_default_pd"] = pd_calculo
            dados_dict["saldo_provisao_constituida"] = prov
            dados_dict["saldo_vencido_over90"] = over90

            resultado.append(FatoCarteiraMensalSchema(**dados_dict))

        return resultado

    @staticmethod
    def calcular_matriz_safras(
        carteira: list[FatoCarteiraMensalSchema],
        mobs_alvo: list[int] | None = None,
    ) -> list[dict[str, Any]]:
        """Calcula a matriz de safras por maturação (Vintage Analysis / MOB).

        Mensura o volume concedido e a evolução da taxa de Ativo Problemático ao longo dos
        meses decorridos desde a concessão (Months on Book - MOB: 1, 3, 6, 12, 24).
        Descarta registros inconsistentes onde a data de fechamento anteceda a concessão.

        Args:
            carteira: Lista de contratos da carteira ao longo do tempo.
            mobs_alvo: Lista de MOBs avaliados (padrão [1, 3, 6, 12, 24]).

        Returns:
            Lista de dicionários agregados por safra de concessão e MOB.
        """
        mobs = mobs_alvo or [1, 3, 6, 12, 24]

        # Agrupamento (safra, mob) -> saldos
        agrupado: dict[tuple[str, int], dict[str, Decimal]] = defaultdict(
            lambda: {
                "saldo_total": Decimal("0.00"),
                "saldo_ap": Decimal("0.00"),
            }
        )

        for c in carteira:
            # Salvaguarda cronológica estrita
            if c.data_fechamento < c.data_concessao:
                continue

            safra_str = f"{c.data_concessao.year:04d}-{c.data_concessao.month:02d}"
            # Cálculo de MOB: diferença em meses entre data_fechamento e data_concessao
            mob = (c.data_fechamento.year - c.data_concessao.year) * 12 + (
                c.data_fechamento.month - c.data_concessao.month
            )

            if mob in mobs and mob >= 0:
                chave = (safra_str, mob)
                agrupado[chave]["saldo_total"] += c.saldo_devedor_contabil
                if c.indicador_ativo_problematico == 1:
                    agrupado[chave]["saldo_ap"] += c.saldo_devedor_contabil

        linhas_vintage: list[dict[str, Any]] = []
        for (safra, mob), valores in sorted(agrupado.items()):
            saldo_tot = valores["saldo_total"]
            saldo_ap = valores["saldo_ap"]
            taxa_ap = Decimal("0.0000")
            if saldo_tot > Decimal("0.00"):
                taxa_ap = (saldo_ap / saldo_tot).quantize(
                    Decimal("0.0001"), rounding=ROUND_HALF_UP
                )

            linhas_vintage.append(
                {
                    "safra": safra,
                    "mob": mob,
                    "saldo_total": saldo_tot,
                    "saldo_ativo_problematico": saldo_ap,
                    "taxa_ativo_problematico": taxa_ap,
                }
            )

        return linhas_vintage

    @staticmethod
    def calcular_matriz_safras_anuais(
        carteira: list[FatoCarteiraMensalSchema],
        mobs_alvo: list[int] | None = None,
    ) -> list[dict[str, Any]]:
        """Calcula a matriz de safras por maturação agrupada por ano civil de concessão.

        Consolida todas as concessões de cada ano (Safra YYYY) para proporcionar
        visão executiva estatisticamente robusta da evolução de risco por MOB.

        Args:
            carteira: Lista de contratos da carteira ao longo do tempo.
            mobs_alvo: Lista de MOBs avaliados (padrão [1, 3, 6, 12, 24]).

        Returns:
            Lista de dicionários agregados por safra anual (Safra YYYY) e MOB.
        """
        mobs = mobs_alvo or [1, 3, 6, 12, 24]

        agrupado: dict[tuple[str, int], dict[str, Decimal]] = defaultdict(
            lambda: {
                "saldo_total": Decimal("0.00"),
                "saldo_ap": Decimal("0.00"),
            }
        )

        for c in carteira:
            if c.data_fechamento < c.data_concessao:
                continue

            safra_ano = f"Safra {c.data_concessao.year}"
            mob = (c.data_fechamento.year - c.data_concessao.year) * 12 + (
                c.data_fechamento.month - c.data_concessao.month
            )

            if mob in mobs and mob >= 0:
                chave = (safra_ano, mob)
                agrupado[chave]["saldo_total"] += c.saldo_devedor_contabil
                if c.indicador_ativo_problematico == 1:
                    agrupado[chave]["saldo_ap"] += c.saldo_devedor_contabil

        linhas_anuais: list[dict[str, Any]] = []
        for (safra, mob), valores in sorted(agrupado.items()):
            saldo_tot = valores["saldo_total"]
            saldo_ap = valores["saldo_ap"]
            taxa_ap = Decimal("0.0000")
            if saldo_tot > Decimal("0.00"):
                taxa_ap = (saldo_ap / saldo_tot).quantize(
                    Decimal("0.0001"), rounding=ROUND_HALF_UP
                )

            linhas_anuais.append(
                {
                    "safra": safra,
                    "mob": mob,
                    "saldo_total": saldo_tot,
                    "saldo_ativo_problematico": saldo_ap,
                    "taxa_ativo_problematico": taxa_ap,
                }
            )

        return linhas_anuais
