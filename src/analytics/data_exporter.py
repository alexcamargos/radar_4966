"""Exportador estruturado do dataset executivo consolidado para o dashboard web.

Gera e compila métricas de carteira, conciliação contábil, perda esperada,
benchmarking Bacen (IF.data/REF), safras (MOB) e parâmetros para o simulador de capital.
"""

import json
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Any

from src.analytics.metrics import MotorAnaliticoDuckDB
from src.ingestion.ifdata_client import IFDataClient
from src.ingestion.ref_client import REFClient
from src.ingestion.synthetic_generator import SyntheticDataGenerator
from src.staging.classifier_4966 import MotorClassificador4966


def converter_serializavel(obj: Any) -> Any:
    """Converte recursivamente objetos Decimal e date em formatos nativos JSON.

    Args:
        obj: Objeto qualquer a ser convertido.

    Returns:
        Versão serializável compatível com json.dumps (float para Decimal e str para date).
    """
    if isinstance(obj, Decimal):
        return float(obj)
    if isinstance(obj, date):
        return obj.isoformat()
    if isinstance(obj, dict):
        return {k: converter_serializavel(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [converter_serializavel(elem) for elem in obj]
    return obj


def exportar_dashboard_data(
    caminho_saida: Path | str = "src/dashboard/data/dashboard_data.json",
    seed: int = 42,
) -> dict[str, Any]:
    """Compila e grava o arquivo JSON consumido diretamente pelo dashboard nativo.

    Args:
        caminho_saida: Caminho relativo ou absoluto do arquivo JSON de destino.
        seed: Semente determinística do gerador sintético.

    Returns:
        Dicionário compilado com os dados estruturados do dashboard.
    """
    # 1. Geração determinística dos dados sintéticos
    generator = SyntheticDataGenerator(seed=seed)
    base = generator.gerar_base_completa()

    calendario = base["d_Calendario"]
    associados = base["d_Associado"]
    linhas = base["d_LinhaCredito"]
    carteira = base["f_Carteira_Mensal"]
    dre = base["f_DRE_Gerencial"]

    # 2. Carga e processamento analítico no DuckDB
    motor = MotorAnaliticoDuckDB()
    motor.carregar_dados(calendario, associados, linhas, carteira, dre)

    # 3. Data-base mais recente para os KPIs de topo
    data_base_recente = calendario[-1].data

    # 4. Cálculo de KPIs da data-base
    kpis_fechamento = motor.calcular_kpis_fechamento(data_base_recente)

    # 5. Séries históricas temporais
    serie_mensal = motor.calcular_serie_historica_mensal()
    cor_12m = motor.calcular_custo_credito_movel_12m()

    # Mapear CoR 12M na série temporal mensal
    mapa_cor = {c["data_fechamento"]: c["percentual_cor_12m"] for c in cor_12m}
    for item in serie_mensal:
        item["percentual_cor_12m"] = mapa_cor.get(item["data_fechamento"], Decimal("0.00"))

    # 6. Dados de Benchmarking Bacen
    ifdata_cli = IFDataClient()
    dados_ifdata = ifdata_cli.obter_dados_ifdata()

    ref_cli = REFClient()
    dados_ref = ref_cli.obter_dados_ref()

    # 7. Distribuição de Estágios e Decomposição do AP
    dist_estagios = motor.calcular_distribuicao_estagios(data_base_recente)
    decomposicao_ap = motor.calcular_decomposicao_ap(data_base_recente)
    dispersao_linhas = motor.calcular_dispersao_por_linha(data_base_recente)

    # Evolução mensal dos 3 estágios
    evolucao_estagios_mensal: list[dict[str, Any]] = []
    for cal in calendario:
        estagios_mes = motor.calcular_distribuicao_estagios(cal.data)
        mapa_est = {e["estagio"]: e for e in estagios_mes}
        evolucao_estagios_mensal.append(
            {
                "data_fechamento": cal.data,
                "estagio_1_saldo": mapa_est.get(1, {}).get("saldo_estagio", Decimal("0.00")),
                "estagio_2_saldo": mapa_est.get(2, {}).get("saldo_estagio", Decimal("0.00")),
                "estagio_3_saldo": mapa_est.get(3, {}).get("saldo_estagio", Decimal("0.00")),
                "estagio_1_pct": mapa_est.get(1, {}).get("percentual_estagio", Decimal("0.00")),
                "estagio_2_pct": mapa_est.get(2, {}).get("percentual_estagio", Decimal("0.00")),
                "estagio_3_pct": mapa_est.get(3, {}).get("percentual_estagio", Decimal("0.00")),
            }
        )

    # 8. Matriz de Safras (Vintage por MOB)
    vintages = MotorClassificador4966.calcular_matriz_safras(carteira, mobs_alvo=[1, 3, 6, 12, 24])

    # 9. Dados base para o Simulador What-If de Capital
    ultimo_dre = dre[-1]
    ultimo_pr = ultimo_dre.patrimonio_referencia_pr
    ultimo_rwa = ultimo_dre.rwa_risco_credito
    ind_capital = round((ultimo_pr / ultimo_rwa) * Decimal("100.00"), 2)

    capital_base = {
        "sobras_atuais": ultimo_dre.sobras_liquidas_exercicio,
        "patrimonio_referencia": ultimo_pr,
        "rwa_risco_credito": ultimo_rwa,
        "indice_capital_atual_pct": ind_capital,
        "carteira_total": ultimo_dre.saldo_carteira_total,
        "provisao_atual": kpis_fechamento["saldo_provisao_constituida"],
        "ativo_problematico_atual": kpis_fechamento["saldo_ativo_problematico"],
    }

    # 10. Consolidação final
    dataset_final: dict[str, Any] = {
        "metadata": {
            "projeto": "Radar 4966 - Inteligência de Risco e Capital",
            "regulacao": "Resolução CMN nº 4.966 / IFRS 9 e Resolução BCB nº 352",
            "data_geracao": date.today().isoformat(),
            "competencia_mais_recente": data_base_recente.isoformat(),
            "total_competencias": len(calendario),
        },
        "kpis_topo": kpis_fechamento,
        "serie_temporal_mensal": serie_mensal,
        "benchmarking_ifdata": [d.model_dump() for d in dados_ifdata],
        "benchmarking_ref": [r.model_dump() for r in dados_ref],
        "distribuicao_estagios_atual": dist_estagios,
        "evolucao_estagios_mensal": evolucao_estagios_mensal,
        "decomposicao_ap": decomposicao_ap,
        "dispersao_linhas": dispersao_linhas,
        "matriz_safras_vintages": vintages,
        "simulador_capital_base": capital_base,
    }

    caminho = Path(caminho_saida)
    caminho.parent.mkdir(parents=True, exist_ok=True)

    dados_serializaveis = converter_serializavel(dataset_final)
    with open(caminho, "w", encoding="utf-8") as f:
        json.dump(dados_serializaveis, f, indent=2, ensure_ascii=False)

    return dataset_final


if __name__ == "__main__":
    exportar_dashboard_data()
