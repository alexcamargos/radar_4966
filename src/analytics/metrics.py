"""Motor de cálculo analítico e conciliação contábil em DuckDB / SQL.

Implementa as consultas analíticas canônicas especificadas no PRD:
Carteira Ativa, Saldo de AP, Taxa de Provisão, Gap de Cobertura,
% Over90 no AP, Cost of Risk (CoR 12M móvel) e auditoria contábil de centavos.
"""

from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Any

import duckdb
import pyarrow as pa

from src.schemas.dimensions import (
    DimAssociadoSchema,
    DimCalendarioSchema,
    DimLinhaCreditoSchema,
)
from src.schemas.facts import FatoCarteiraMensalSchema, FatoDREGerencialSchema


class MotorAnaliticoDuckDB:
    """Encapsula as análises e consultas de inteligência em risco de crédito.

    Utiliza conexão in-memory do DuckDB com tipagem estrita para processamento
    analítico das tabelas fato e dimensões.
    """

    def __init__(self, con: duckdb.DuckDBPyConnection | None = None) -> None:
        """Inicializa a conexão in-memory com o DuckDB.

        Args:
            con: Conexão DuckDB opcional existente. Se None, cria uma nova em memória.
        """
        self.con = con or duckdb.connect(database=":memory:")

    def carregar_dados(
        self,
        calendario: list[DimCalendarioSchema],
        associados: list[DimAssociadoSchema],
        linhas: list[DimLinhaCreditoSchema],
        carteira: list[FatoCarteiraMensalSchema],
        dre: list[FatoDREGerencialSchema],
    ) -> None:
        """Carrega e registra as tabelas estruturadas no catálogo do DuckDB.

        Args:
            calendario: Lista de instâncias da dimensão calendário.
            associados: Lista de cooperados.
            linhas: Linhas e modalidades de crédito.
            carteira: Histórico mensal de contratos.
            dre: Balancete e demonstrativo gerencial mensal.
        """
        # Conversão em PyArrow Tables para ingestão analítica colunar sem perda de precisão
        tbl_cal = pa.Table.from_pylist([c.model_dump() for c in calendario])
        tbl_assoc = pa.Table.from_pylist([a.model_dump() for a in associados])
        tbl_linhas = pa.Table.from_pylist([li.model_dump() for li in linhas])
        tbl_cart = pa.Table.from_pylist([ca.model_dump() for ca in carteira])
        tbl_dre = pa.Table.from_pylist([d.model_dump() for d in dre])

        self.con.register("tmp_cal", tbl_cal)
        self.con.register("tmp_assoc", tbl_assoc)
        self.con.register("tmp_linhas", tbl_linhas)
        self.con.register("tmp_cart", tbl_cart)
        self.con.register("tmp_dre", tbl_dre)

        self.con.execute("CREATE OR REPLACE TABLE d_Calendario AS SELECT * FROM tmp_cal")
        self.con.execute("CREATE OR REPLACE TABLE d_Associado AS SELECT * FROM tmp_assoc")
        self.con.execute("CREATE OR REPLACE TABLE d_LinhaCredito AS SELECT * FROM tmp_linhas")
        self.con.execute("CREATE OR REPLACE TABLE f_Carteira_Mensal AS SELECT * FROM tmp_cart")
        self.con.execute("CREATE OR REPLACE TABLE f_DRE_Gerencial AS SELECT * FROM tmp_dre")

    def carregar_de_parquet(self, diretorio_interim: Path | str) -> None:
        """Carrega e registra as tabelas intermediárias em formato Parquet no catálogo do DuckDB.

        Args:
            diretorio_interim: Caminho para o diretório interim contendo os arquivos parquet.

        Raises:
            FileNotFoundError: Se algum arquivo parquet obrigatório não for encontrado.
        """
        p = Path(diretorio_interim)
        arquivos = {
            "d_Calendario": p / "calendario_staging.parquet",
            "d_Associado": p / "associados_staging.parquet",
            "d_LinhaCredito": p / "linhas_credito_staging.parquet",
            "f_Carteira_Mensal": p / "carteira_staging.parquet",
            "f_DRE_Gerencial": p / "dre_staging.parquet",
        }
        for tabela, arq in arquivos.items():
            if not arq.exists():
                raise FileNotFoundError(f"Arquivo parquet obrigatório '{arq}' não encontrado.")
            caminho_sql = arq.resolve().as_posix()
            self.con.execute(
                f"CREATE OR REPLACE TABLE {tabela} AS SELECT * FROM read_parquet('{caminho_sql}')"
            )

    def calcular_kpis_fechamento(self, data_base: date) -> dict[str, Any]:
        """Calcula os KPIs executivos sintéticos da cooperativa na data-base informada.

        Args:
            data_base: Data da competência avaliada.

        Returns:
            Dicionário contendo os indicadores: carteira_ativa, saldo_ap, taxa_ap_pct,
            taxa_prov_pct, gap_cobertura_pct, taxa_over90_pct, over90_no_ap_pct e
            indice_cobertura_ecl.

        Raises:
            ValueError: Se não houver registros para a data_base solicitada.
        """
        sql = """
        SELECT
            COALESCE(SUM(saldo_devedor_contabil), 0.0) AS carteira_ativa,
            COALESCE(SUM(CASE WHEN indicador_ativo_problematico = 1
                THEN saldo_devedor_contabil ELSE 0 END), 0.0) AS saldo_ap,
            COALESCE(SUM(saldo_provisao_constituida), 0.0) AS saldo_provisao,
            COALESCE(SUM(CASE WHEN dias_atraso > 90
                THEN saldo_devedor_contabil ELSE 0 END), 0.0) AS saldo_over90,
            COALESCE(
                SUM(saldo_devedor_contabil * probabilidade_default_pd * loss_given_default_lgd),
                0.0,
            ) AS soma_ecl_estimada
        FROM f_Carteira_Mensal
        WHERE data_fechamento = ?
        """
        res = self.con.execute(sql, [data_base]).fetchone()
        if not res or res[0] == 0.0:
            raise ValueError(f"Nenhum registro encontrado para a competência {data_base}.")

        carteira_ativa = Decimal(str(round(res[0], 2)))
        saldo_ap = Decimal(str(round(res[1], 2)))
        saldo_prov = Decimal(str(round(res[2], 2)))
        saldo_over90 = Decimal(str(round(res[3], 2)))
        ecl_estimada = Decimal(str(round(res[4], 2)))

        taxa_ap = Decimal("0.00")
        taxa_prov = Decimal("0.00")
        taxa_over90 = Decimal("0.00")
        over90_no_ap = Decimal("0.00")
        cobertura_ecl = Decimal("0.0000")

        if carteira_ativa > Decimal("0.00"):
            taxa_ap = round((saldo_ap / carteira_ativa) * Decimal("100.00"), 2)
            taxa_prov = round((saldo_prov / carteira_ativa) * Decimal("100.00"), 2)
            taxa_over90 = round((saldo_over90 / carteira_ativa) * Decimal("100.00"), 2)

        gap_cobertura = taxa_prov - taxa_ap

        if saldo_ap > Decimal("0.00"):
            over90_no_ap = round((saldo_over90 / saldo_ap) * Decimal("100.00"), 2)

        if ecl_estimada > Decimal("0.00"):
            cobertura_ecl = round(saldo_prov / ecl_estimada, 4)

        return {
            "data_base": data_base,
            "carteira_ativa": carteira_ativa,
            "saldo_ativo_problematico": saldo_ap,
            "saldo_provisao_constituida": saldo_prov,
            "saldo_over90": saldo_over90,
            "taxa_ativo_problematico_pct": taxa_ap,
            "taxa_provisao_pct": taxa_prov,
            "gap_cobertura_pct": gap_cobertura,
            "taxa_inadimplencia_over90_pct": taxa_over90,
            "percentual_over90_no_ap_pct": over90_no_ap,
            "indice_cobertura_ecl": cobertura_ecl,
        }

    def calcular_serie_historica_mensal(self) -> list[dict[str, Any]]:
        """Calcula a evolução temporal das taxas de AP e provisão mês a mês.

        Identifica dinamicamente a data exata do cruzamento onde Prov% cruzou abaixo de AP%.

        Returns:
            Lista de dicionários ordenados com as séries mensais e flag de cruzamento.
        """
        sql = """
        SELECT
            data_fechamento,
            ROUND(SUM(CASE WHEN indicador_ativo_problematico = 1
                THEN saldo_devedor_contabil ELSE 0 END) /
                NULLIF(SUM(saldo_devedor_contabil), 0) * 100, 2) AS taxa_ap,
            ROUND(SUM(saldo_provisao_constituida) /
                NULLIF(SUM(saldo_devedor_contabil), 0) * 100, 2) AS taxa_prov,
            SUM(saldo_devedor_contabil) AS saldo_carteira
        FROM f_Carteira_Mensal
        GROUP BY data_fechamento
        ORDER BY data_fechamento
        """
        rows = self.con.execute(sql).fetchall()

        serie: list[dict[str, Any]] = []
        cruzou_abaixo_encontrado = False

        for r in rows:
            dt = r[0]
            t_ap = Decimal(str(r[1]))
            t_prov = Decimal(str(r[2]))
            saldo = Decimal(str(round(r[3], 2)))

            # Ponto exato onde provisão cruza abaixo da taxa de AP
            marcador_cruzamento = False
            if not cruzou_abaixo_encontrado and t_prov < t_ap:
                marcador_cruzamento = True
                cruzou_abaixo_encontrado = True

            serie.append(
                {
                    "data_fechamento": dt,
                    "taxa_ap": t_ap,
                    "taxa_provisao": t_prov,
                    "saldo_carteira": saldo,
                    "gap_cobertura": t_prov - t_ap,
                    "cruzamento_alerta": marcador_cruzamento,
                }
            )

        return serie

    def calcular_distribuicao_estagios(self, data_base: date) -> list[dict[str, Any]]:
        """Gera a distribuição de saldos e proporção por Estágio na data-base.

        Args:
            data_base: Competência de apuração.

        Returns:
            Lista com saldos e percentuais dos Estágios 1, 2 e 3.
        """
        sql = """
        SELECT
            estagio_contabil,
            SUM(saldo_devedor_contabil) AS saldo_estagio,
            ROUND(SUM(saldo_devedor_contabil) /
                NULLIF((SELECT SUM(saldo_devedor_contabil)
                        FROM f_Carteira_Mensal
                        WHERE data_fechamento = ?), 0) * 100, 2) AS percentual_estagio
        FROM f_Carteira_Mensal
        WHERE data_fechamento = ?
        GROUP BY estagio_contabil
        ORDER BY estagio_contabil
        """
        rows = self.con.execute(sql, [data_base, data_base]).fetchall()
        return [
            {
                "estagio": r[0],
                "saldo_estagio": Decimal(str(round(r[1], 2))),
                "percentual_estagio": Decimal(str(r[2])),
            }
            for r in rows
        ]

    def calcular_decomposicao_ap(self, data_base: date) -> dict[str, Any]:
        """Calcula a quebra da origem do Ativo Problemático na data-base.

        Categorias:
        1. Atraso Prolongado (> 90 dias)
        2. Renegociação por Estresse Financeiro (Forbearance)
        3. Deterioração de Rating e Alertas Preventivos (SICR / Rating 10)

        Args:
            data_base: Competência contábil de apuração.

        Returns:
            Dicionário categorizando saldos e percentuais sobre o total do AP.
        """
        sql = """
        SELECT
            SUM(CASE WHEN dias_atraso > 90 THEN saldo_devedor_contabil ELSE 0 END) AS over90,
            SUM(CASE WHEN indicador_renegociacao = 1 AND dias_atraso <= 90
                THEN saldo_devedor_contabil ELSE 0 END) AS renegociacao,
            SUM(CASE WHEN dias_atraso <= 90 AND indicador_renegociacao = 0 AND
                indicador_ativo_problematico = 1
                THEN saldo_devedor_contabil ELSE 0 END) AS outros_sicr,
            SUM(CASE WHEN indicador_ativo_problematico = 1
                THEN saldo_devedor_contabil ELSE 0 END) AS total_ap
        FROM f_Carteira_Mensal
        WHERE data_fechamento = ?
        """
        res = self.con.execute(sql, [data_base]).fetchone()
        if not res:
            return {
                "over90": Decimal("0.00"),
                "renegociacao": Decimal("0.00"),
                "outros": Decimal("0.00"),
            }

        over90 = Decimal(str(round(res[0] or 0.0, 2)))
        reneg = Decimal(str(round(res[1] or 0.0, 2)))
        outros = Decimal(str(round(res[2] or 0.0, 2)))
        total_ap = Decimal(str(round(res[3] or 0.0, 2)))

        p_over90 = (
            round((over90 / total_ap) * Decimal("100.00"), 2) if total_ap > 0 else Decimal("0.00")
        )
        p_reneg = (
            round((reneg / total_ap) * Decimal("100.00"), 2) if total_ap > 0 else Decimal("0.00")
        )
        p_outros = (
            round((outros / total_ap) * Decimal("100.00"), 2) if total_ap > 0 else Decimal("0.00")
        )

        return {
            "total_ativo_problematico": total_ap,
            "saldo_over90": over90,
            "percentual_over90": p_over90,
            "saldo_renegociacao": reneg,
            "percentual_renegociacao": p_reneg,
            "saldo_outros_preventivos": outros,
            "percentual_outros_preventivos": p_outros,
        }

    def calcular_custo_credito_movel_12m(self) -> list[dict[str, Any]]:
        """Calcula o Custo de Crédito (Cost of Risk - CoR 12M%) em janela móvel.

        Equação regulatória canônica:
        Despesa líquida de provisão acumulada em 12 meses dividida pela carteira média do período.

        Returns:
            Lista com os fechamentos contábeis mensais e os indicadores de CoR 12M.
        """
        sql = """
        WITH dre_acumulado AS (
            SELECT
                data_fechamento,
                despesa_liquida_pdd_mes,
                saldo_carteira_total,
                SUM(despesa_liquida_pdd_mes) OVER (
                    ORDER BY data_fechamento
                    ROWS BETWEEN 11 PRECEDING AND CURRENT ROW
                ) AS despesa_pdd_12m,
                AVG(saldo_carteira_total) OVER (
                    ORDER BY data_fechamento
                    ROWS BETWEEN 11 PRECEDING AND CURRENT ROW
                ) AS media_carteira_12m
            FROM f_DRE_Gerencial
        )
        SELECT
            data_fechamento,
            ROUND(despesa_pdd_12m, 2) AS despesa_pdd_12m,
            ROUND(media_carteira_12m, 2) AS media_carteira_12m,
            ROUND((despesa_pdd_12m / NULLIF(media_carteira_12m, 0)) * 100, 2) AS percentual_cor_12m
        FROM dre_acumulado
        ORDER BY data_fechamento;
        """
        rows = self.con.execute(sql).fetchall()
        return [
            {
                "data_fechamento": r[0],
                "despesa_pdd_12m": Decimal(str(r[1])),
                "media_carteira_12m": Decimal(str(r[2])),
                "percentual_cor_12m": Decimal(str(r[3])),
            }
            for r in rows
        ]

    def calcular_dispersao_por_linha(self, data_base: date) -> list[dict[str, Any]]:
        """Calcula dispersão de crescimento de carteira e provisão por modalidade de crédito.

        Args:
            data_base: Competência de apuração atual.

        Returns:
            Lista com indicadores de volume, provisão e taxa de risco por linha.
        """
        sql = """
        SELECT
            li.id_linha,
            li.nome_linha,
            li.grupo_modalidade,
            SUM(c.saldo_devedor_contabil) AS saldo_linha,
            SUM(c.saldo_provisao_constituida) AS provisao_linha,
            ROUND(SUM(c.saldo_provisao_constituida) /
                NULLIF(SUM(c.saldo_devedor_contabil), 0) * 100, 2) AS taxa_risco_linha
        FROM f_Carteira_Mensal c
        JOIN d_LinhaCredito li ON c.id_linha = li.id_linha
        WHERE c.data_fechamento = ?
        GROUP BY li.id_linha, li.nome_linha, li.grupo_modalidade
        ORDER BY saldo_linha DESC
        """
        rows = self.con.execute(sql, [data_base]).fetchall()
        return [
            {
                "id_linha": r[0],
                "nome_linha": r[1],
                "grupo_modalidade": r[2],
                "saldo_linha": Decimal(str(round(r[3], 2))),
                "provisao_linha": Decimal(str(round(r[4], 2))),
                "taxa_risco_linha": Decimal(str(r[5])),
            }
            for r in rows
        ]

    def auditar_conciliacao_carteira_balancete(self) -> list[dict[str, Any]]:
        """Compara e audita a conciliação ao centavo entre a carteira e o balancete DRE.

        Returns:
            Lista de discrepâncias encontradas por mês. Lista vazia indica conciliação
            100% perfeita.
        """
        sql = """
        WITH carteira_agregada AS (
            SELECT
                data_fechamento,
                ROUND(SUM(saldo_devedor_contabil), 2) AS soma_carteira
            FROM f_Carteira_Mensal
            GROUP BY data_fechamento
        )
        SELECT
            d.data_fechamento,
            d.saldo_carteira_total AS saldo_dre,
            c.soma_carteira AS saldo_carteira,
            ROUND(d.saldo_carteira_total - c.soma_carteira, 2) AS divergencia
        FROM f_DRE_Gerencial d
        JOIN carteira_agregada c ON d.data_fechamento = c.data_fechamento
        WHERE ROUND(d.saldo_carteira_total - c.soma_carteira, 2) != 0.00
        """
        rows = self.con.execute(sql).fetchall()
        return [
            {
                "data_fechamento": r[0],
                "saldo_dre": Decimal(str(r[1])),
                "saldo_carteira": Decimal(str(r[2])),
                "divergencia": Decimal(str(r[3])),
            }
            for r in rows
        ]
