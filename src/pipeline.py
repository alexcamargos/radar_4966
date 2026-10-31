"""Orquestrador do pipeline de dados em camadas (CCDS v2 / Medallion).

Implementa a segregação física estrita e o fluxo unidirecional:
1. Ingestão Bruta (Bronze / Raw): data/raw/ com manifestos de integridade SHA-256.
2. Camada Intermediária (Silver / Interim): data/interim/ em Apache Parquet validado.
3. Camada Analítica (Gold / Processed): data/processed/ com marts Parquet e DuckDB.
"""

import argparse
import hashlib
import json
import shutil
import sys
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

import duckdb
import pyarrow as pa
import pyarrow.parquet as pq
from pydantic import TypeAdapter

import src.config as cfg
from src.analytics.data_exporter import converter_serializavel, exportar_dashboard_data
from src.analytics.metrics import MotorAnaliticoDuckDB
from src.ingestion.ifdata_client import IFDataClient
from src.ingestion.ref_client import REFClient
from src.ingestion.synthetic_generator import SyntheticDataGenerator
from src.schemas.dimensions import (
    DimAssociadoSchema,
    DimCalendarioSchema,
    DimLinhaCreditoSchema,
)
from src.schemas.facts import (
    FatoCarteiraMensalSchema,
    FatoDREGerencialSchema,
    FatoIFDataSNCCSchema,
    FatoREFMacroBCBSchema,
)
from src.staging.classifier_4966 import MotorClassificador4966


def calcular_hash_sha256(caminho_arquivo: Path) -> str:
    """Calcula o hash criptográfico SHA-256 de um arquivo em disco.

    Args:
        caminho_arquivo: Objeto Path do arquivo a ser auditado.

    Returns:
        String com a representação hexadecimal do hash SHA-256.

    Raises:
        FileNotFoundError: Se o arquivo especificado não existir no sistema de arquivos.
    """
    if not caminho_arquivo.exists():
        raise FileNotFoundError(f"Arquivo para cálculo de hash não encontrado: {caminho_arquivo}")

    hasher = hashlib.sha256()
    with open(caminho_arquivo, "rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    return hasher.hexdigest()


def ingest_raw(
    seed: int = cfg.DEFAULT_SEED,
    diretorio_raiz_raw: Path | None = None,
) -> dict[str, Any]:
    """Executa a etapa de ingestão bruta (Bronze / Raw) e grava os dados com hash SHA-256.

    Gera ou obtém os dados brutos da cooperativa singular e do Banco Central (IF.data e REF),
    materializando-os em formato texto estruturado (JSON/JSONL) de forma append-only,
    culminando na geração do manifesto criptográfico de integridade.

    Args:
        seed: Semente pseudoaleatória para reprodutibilidade dos dados da singular.
        diretorio_raiz_raw: Diretório raiz customizado da camada raw. Se None, usa RAW_DATA_DIR.

    Returns:
        Dicionário com o resumo de arquivos gerados e metadados do manifesto SHA-256.

    Raises:
        OSError: Se houver falha de escrita no sistema de arquivos.
    """
    raiz_raw = diretorio_raiz_raw or cfg.RAW_DATA_DIR
    dir_singular = raiz_raw / "singular"
    dir_ifdata = raiz_raw / "bacen" / "ifdata"
    dir_ref = raiz_raw / "bacen" / "ref"

    for d in (dir_singular, dir_ifdata, dir_ref):
        d.mkdir(parents=True, exist_ok=True)

    # 1. Geração determinística da cooperativa singular
    generator = SyntheticDataGenerator(seed=seed)
    base = generator.gerar_base_completa()

    arq_carteira = dir_singular / "carteira_mensal.jsonl"
    with open(arq_carteira, "w", encoding="utf-8") as f:
        for c in base["f_Carteira_Mensal"]:
            f.write(c.model_dump_json() + "\n")

    arq_dre = dir_singular / "dre_gerencial.json"
    with open(arq_dre, "w", encoding="utf-8") as f:
        dre_dicts = [json.loads(d.model_dump_json()) for d in base["f_DRE_Gerencial"]]
        f.write(json.dumps(dre_dicts, indent=2))

    arq_associados = dir_singular / "associados.json"
    with open(arq_associados, "w", encoding="utf-8") as f:
        assoc_dicts = [json.loads(a.model_dump_json()) for a in base["d_Associado"]]
        f.write(json.dumps(assoc_dicts, indent=2))

    arq_linhas = dir_singular / "linhas_credito.json"
    with open(arq_linhas, "w", encoding="utf-8") as f:
        linhas_dicts = [json.loads(li.model_dump_json()) for li in base["d_LinhaCredito"]]
        f.write(json.dumps(linhas_dicts, indent=2))

    arq_calendario = dir_singular / "calendario.json"
    with open(arq_calendario, "w", encoding="utf-8") as f:
        cal_dicts = [json.loads(cal.model_dump_json()) for cal in base["d_Calendario"]]
        f.write(json.dumps(cal_dicts, indent=2))

    # 2. Ingestão das séries históricas públicas do Banco Central
    ifdata_cli = IFDataClient()
    dados_ifdata = ifdata_cli.obter_dados_trimestrais()
    arq_ifdata = dir_ifdata / "ifdata_trimestral.json"
    with open(arq_ifdata, "w", encoding="utf-8") as f:
        ifdata_dicts = [json.loads(item.model_dump_json()) for item in dados_ifdata]
        f.write(json.dumps(ifdata_dicts, indent=2))

    ref_cli = REFClient()
    dados_ref = ref_cli.obter_dados_semestrais()
    arq_ref = dir_ref / "ref_semestral.json"
    with open(arq_ref, "w", encoding="utf-8") as f:
        ref_dicts = [json.loads(item.model_dump_json()) for item in dados_ref]
        f.write(json.dumps(ref_dicts, indent=2))

    # 3. Construção do manifesto SHA-256 para rastreabilidade e auditoria
    arquivos_alvo = [
        (arq_carteira, len(base["f_Carteira_Mensal"])),
        (arq_dre, len(base["f_DRE_Gerencial"])),
        (arq_associados, len(base["d_Associado"])),
        (arq_linhas, len(base["d_LinhaCredito"])),
        (arq_calendario, len(base["d_Calendario"])),
        (arq_ifdata, len(dados_ifdata)),
        (arq_ref, len(dados_ref)),
    ]

    manifesto_itens: list[dict[str, Any]] = []
    for caminho, qtd in arquivos_alvo:
        hash_calc = calcular_hash_sha256(caminho)
        tamanho = caminho.stat().st_size
        rel_path = str(caminho.relative_to(raiz_raw)).replace("\\", "/")
        manifesto_itens.append(
            {
                "caminho_relativo": rel_path,
                "sha256": hash_calc,
                "tamanho_bytes": tamanho,
                "quantidade_registros": qtd,
            }
        )

    manifesto = {
        "versao_manifesto": "1.0",
        "algoritmo": "SHA-256",
        "timestamp_coleta": datetime.now(UTC).isoformat(),
        "seed_deterministica": seed,
        "arquivos": manifesto_itens,
    }

    caminho_manifesto = raiz_raw / "manifest_sha256.json"
    with open(caminho_manifesto, "w", encoding="utf-8") as f:
        f.write(json.dumps(manifesto, indent=2))

    return manifesto


def process_interim(
    diretorio_origem_raw: Path | None = None,
    diretorio_destino_interim: Path | None = None,
    validar_integridade: bool = True,
) -> dict[str, Any]:
    """Executa a transformação da camada intermediária (Silver / Interim) em Apache Parquet.

    Lê exclusivamente da camada Raw, valida contratos formais via Pydantic V2,
    aplica regras de enquadramento da Resolução 4.966 e persiste conjuntos limpos
    e tipados em arquivos colunares Parquet.

    Args:
        diretorio_origem_raw: Raiz dos dados brutos. Se None, usa RAW_DATA_DIR.
        diretorio_destino_interim: Raiz da camada interim. Se None, usa INTERIM_DATA_DIR.
        validar_integridade: Se True, audita os hashes SHA-256 contra o manifesto antes da carga.

    Returns:
        Dicionário com o sumário das tabelas estruturadas salvas em Parquet.

    Raises:
        FileNotFoundError: Se algum arquivo de entrada obrigatório não existir.
        ValueError: Se houver falha de validação de integridade ou violação de contrato.
    """
    raiz_raw = diretorio_origem_raw or cfg.RAW_DATA_DIR
    dir_interim = diretorio_destino_interim or cfg.INTERIM_DATA_DIR
    dir_interim.mkdir(parents=True, exist_ok=True)

    # 1. Auditoria de integridade criptográfica
    caminho_manifesto = raiz_raw / "manifest_sha256.json"
    if validar_integridade and caminho_manifesto.exists():
        with open(caminho_manifesto, encoding="utf-8") as f:
            manifesto = json.load(f)
        for item in manifesto.get("arquivos", []):
            arq_path = raiz_raw / item["caminho_relativo"]
            hash_atual = calcular_hash_sha256(arq_path)
            if hash_atual != item["sha256"]:
                raise ValueError(
                    f"Integridade violada para '{item['caminho_relativo']}': "
                    f"esperado {item['sha256']}, obtido {hash_atual}."
                )

    # 2. Leitura, validação estrita e conversão em lote
    # A. Calendário
    arq_cal = raiz_raw / "singular" / "calendario.json"
    with open(arq_cal, encoding="utf-8") as f:
        calendario_validados = TypeAdapter(list[DimCalendarioSchema]).validate_json(f.read())
    tbl_cal = pa.Table.from_pylist([c.model_dump() for c in calendario_validados])
    pq.write_table(tbl_cal, dir_interim / "calendario_staging.parquet")

    # B. Associados
    arq_assoc = raiz_raw / "singular" / "associados.json"
    with open(arq_assoc, encoding="utf-8") as f:
        associados_validados = TypeAdapter(list[DimAssociadoSchema]).validate_json(f.read())
    tbl_assoc = pa.Table.from_pylist([a.model_dump() for a in associados_validados])
    pq.write_table(tbl_assoc, dir_interim / "associados_staging.parquet")

    # C. Linhas de Crédito
    arq_linhas = raiz_raw / "singular" / "linhas_credito.json"
    with open(arq_linhas, encoding="utf-8") as f:
        linhas_validadas = TypeAdapter(list[DimLinhaCreditoSchema]).validate_json(f.read())
    tbl_linhas = pa.Table.from_pylist([li.model_dump() for li in linhas_validadas])
    pq.write_table(tbl_linhas, dir_interim / "linhas_credito_staging.parquet")

    # D. Carteira Mensal (JSONL) + Validação Regulatória 4.966
    arq_carteira = raiz_raw / "singular" / "carteira_mensal.jsonl"
    carteira_validadas: list[FatoCarteiraMensalSchema] = []
    with open(arq_carteira, encoding="utf-8") as f:
        for linha in f:
            if linha.strip():
                contrato = FatoCarteiraMensalSchema.model_validate_json(linha)
                estagio_calc, ap_calc = MotorClassificador4966.classificar_operacao(
                    dias_atraso=contrato.dias_atraso,
                    indicador_renegociacao=contrato.indicador_renegociacao,
                    rating_comportamental_atual=10 if contrato.estagio_contabil == 3 else 3,
                )
                if (contrato.dias_atraso > 90 or contrato.indicador_renegociacao == 1) and (
                    contrato.estagio_contabil != 3 or contrato.indicador_ativo_problematico != 1
                ):
                    msg_err = (
                        f"Contrato {contrato.id_contrato} viola regras regulatórias "
                        f"do Estágio 3 (calculado estagio={estagio_calc}, ap={ap_calc})."
                    )
                    raise ValueError(msg_err)
                carteira_validadas.append(contrato)

    tbl_carteira = pa.Table.from_pylist([c.model_dump() for c in carteira_validadas])
    pq.write_table(tbl_carteira, dir_interim / "carteira_staging.parquet")

    # E. DRE Gerencial
    arq_dre = raiz_raw / "singular" / "dre_gerencial.json"
    with open(arq_dre, encoding="utf-8") as f:
        dre_validadas = TypeAdapter(list[FatoDREGerencialSchema]).validate_json(f.read())
    tbl_dre = pa.Table.from_pylist([d.model_dump() for d in dre_validadas])
    pq.write_table(tbl_dre, dir_interim / "dre_staging.parquet")

    # F. IF.data Bacen
    arq_ifdata = raiz_raw / "bacen" / "ifdata" / "ifdata_trimestral.json"
    with open(arq_ifdata, encoding="utf-8") as f:
        ifdata_validados = TypeAdapter(list[FatoIFDataSNCCSchema]).validate_json(f.read())
    tbl_ifdata = pa.Table.from_pylist([item.model_dump() for item in ifdata_validados])
    pq.write_table(tbl_ifdata, dir_interim / "ifdata_staging.parquet")

    # G. REF Macro Bacen
    arq_ref = raiz_raw / "bacen" / "ref" / "ref_semestral.json"
    with open(arq_ref, encoding="utf-8") as f:
        ref_validados = TypeAdapter(list[FatoREFMacroBCBSchema]).validate_json(f.read())
    tbl_ref = pa.Table.from_pylist([item.model_dump() for item in ref_validados])
    pq.write_table(tbl_ref, dir_interim / "ref_staging.parquet")

    return {
        "status": "sucesso",
        "tabelas_processadas": {
            "calendario": len(calendario_validados),
            "associados": len(associados_validados),
            "linhas_credito": len(linhas_validadas),
            "carteira_mensal": len(carteira_validadas),
            "dre_gerencial": len(dre_validadas),
            "ifdata": len(ifdata_validados),
            "ref": len(ref_validados),
        },
    }


def build_processed(
    diretorio_origem_interim: Path | None = None,
    diretorio_destino_processed: Path | None = None,
    caminho_duckdb: Path | None = None,
    exportar_dashboard: bool = True,
) -> dict[str, Any]:
    """Compila a camada analítica (Gold / Processed) com marts Parquet, DuckDB e JSON executivo.

    Lê exclusivamente os dados da camada interim, consolida o catálogo DuckDB persistido,
    gera os marts de consumo analítico em Parquet e compila o dataset final do dashboard.

    Args:
        diretorio_origem_interim: Raiz da camada interim. Se None, usa INTERIM_DATA_DIR.
        diretorio_destino_processed: Raiz da camada processed. Se None, usa PROCESSED_DATA_DIR.
        caminho_duckdb: Caminho do arquivo de banco DuckDB. Se None, usa PROCESSED_DUCKDB_PATH.
        exportar_dashboard: Se True, compila e sincroniza o dashboard_data.json.

    Returns:
        Dicionário com o sumário de marts criados e metadados analíticos apurados.

    Raises:
        FileNotFoundError: Se a pasta interim ou os arquivos parquet não existirem.
    """
    dir_interim = diretorio_origem_interim or cfg.INTERIM_DATA_DIR
    dir_processed = diretorio_destino_processed or cfg.PROCESSED_DATA_DIR
    dir_marts = dir_processed / "marts"
    dir_marts.mkdir(parents=True, exist_ok=True)

    db_path = caminho_duckdb or cfg.PROCESSED_DUCKDB_PATH
    db_path.parent.mkdir(parents=True, exist_ok=True)

    # 1. Conexão DuckDB e carga colunar de Parquet
    con = duckdb.connect(database=str(db_path))
    motor = MotorAnaliticoDuckDB(con=con)
    motor.carregar_de_parquet(dir_interim)

    # Carga das tabelas do Bacen no catálogo analítico
    arq_ifdata = (dir_interim / "ifdata_staging.parquet").resolve().as_posix()
    arq_ref = (dir_interim / "ref_staging.parquet").resolve().as_posix()
    con.execute(
        f"CREATE OR REPLACE TABLE f_IFData_SNCC AS SELECT * FROM read_parquet('{arq_ifdata}')"
    )
    con.execute(
        f"CREATE OR REPLACE TABLE f_REF_Macro_BCB AS SELECT * FROM read_parquet('{arq_ref}')"
    )

    # 2. Materialização dos Marts Analíticos em Parquet
    marts_sql = {
        "f_carteira_mensal": "SELECT * FROM f_Carteira_Mensal",
        "f_dre_gerencial": "SELECT * FROM f_DRE_Gerencial",
        "f_ifdata_sncc": "SELECT * FROM f_IFData_SNCC",
        "f_ref_macro_bcb": "SELECT * FROM f_REF_Macro_BCB",
    }
    for mart_nome, sql in marts_sql.items():
        destino_parquet = (dir_marts / f"{mart_nome}.parquet").resolve().as_posix()
        con.execute(f"COPY ({sql}) TO '{destino_parquet}' (FORMAT PARQUET)")

    # Mart de Matriz de Safras (Vintages MOB)
    vintages_sql = """
    SELECT
        strftime(data_concessao, '%Y-%m') AS safra,
        ((year(data_fechamento) - year(data_concessao)) * 12 +
         (month(data_fechamento) - month(data_concessao))) AS mob,
        SUM(saldo_devedor_contabil) AS saldo_total,
        SUM(CASE WHEN indicador_ativo_problematico = 1 THEN saldo_devedor_contabil ELSE 0 END)
            AS saldo_ap,
        ROUND(
            SUM(CASE WHEN indicador_ativo_problematico = 1 THEN saldo_devedor_contabil ELSE 0 END) /
            NULLIF(SUM(saldo_devedor_contabil), 0) * 100,
            2
        ) AS taxa_ap_pct
    FROM f_Carteira_Mensal
    WHERE ((year(data_fechamento) - year(data_concessao)) * 12 +
           (month(data_fechamento) - month(data_concessao))) IN (1, 3, 6, 12, 24)
    GROUP BY safra, mob
    ORDER BY safra, mob
    """
    destino_vintages = (dir_marts / "vintages_mob.parquet").resolve().as_posix()
    con.execute(f"COPY ({vintages_sql}) TO '{destino_vintages}' (FORMAT PARQUET)")

    # Mart de Métricas Temporais Agregadas
    serie_mensal = motor.calcular_serie_historica_mensal()
    cor_12m = motor.calcular_custo_credito_movel_12m()
    mapa_cor = {c["data_fechamento"]: c["percentual_cor_12m"] for c in cor_12m}
    for item in serie_mensal:
        dt = item["data_fechamento"]
        item["percentual_cor_12m"] = mapa_cor.get(dt, Decimal("0.00"))
    tbl_serie = pa.Table.from_pylist([converter_serializavel(s) for s in serie_mensal])
    pq.write_table(tbl_serie, dir_marts / "metricas_consolidadas.parquet")

    # 3. Compilação do JSON do Dashboard C-Level
    resultado_dashboard: dict[str, Any] = {}
    if exportar_dashboard:
        caminho_json_processed = dir_processed / "dashboard_data.json"
        resultado_dashboard = exportar_dashboard_data(
            caminho_saida=caminho_json_processed,
            seed=cfg.DEFAULT_SEED,
        )
        cfg.DASHBOARD_DATA_DIR.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(caminho_json_processed, cfg.DASHBOARD_DATA_PATH)

    con.close()

    marts_nomes = (
        [f"{m}.parquet" for m in marts_sql]
        + ["vintages_mob.parquet", "metricas_consolidadas.parquet"]
    )
    return {
        "status": "sucesso",
        "marts_gerados": marts_nomes,
        "duckdb_banco": str(db_path),
        "dashboard_exportado": exportar_dashboard,
        "kpis_fechamento": resultado_dashboard.get("kpis_fechamento", {}),
    }


def run_full_pipeline(seed: int = cfg.DEFAULT_SEED) -> dict[str, Any]:
    """Executa o ciclo analítico completo de ponta a ponta nas 3 camadas Medallion.

    Args:
        seed: Semente pseudoaleatória do gerador determinístico.

    Returns:
        Dicionário com o sumário completo de execução das 3 camadas de dados.
    """
    cfg.garantir_diretorios()
    res_raw = ingest_raw(seed=seed)
    res_interim = process_interim(validar_integridade=True)
    res_processed = build_processed(exportar_dashboard=True)

    return {
        "status": "concluido",
        "camada_raw": res_raw,
        "camada_interim": res_interim,
        "camada_processed": res_processed,
    }


def main() -> None:
    """Ponto de entrada CLI para acionamento do pipeline de dados via terminal."""
    parser = argparse.ArgumentParser(
        description="Pipeline Analítico de Risco de Crédito Resolução CMN 4.966 (CCDS v2)"
    )
    parser.add_argument(
        "--stage",
        choices=["all", "raw", "interim", "processed"],
        default="all",
        help="Etapa do pipeline a ser executada (padrão: all).",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=cfg.DEFAULT_SEED,
        help="Semente determinística do gerador sintético (padrão: 42).",
    )

    args = parser.parse_args()

    try:
        cfg.garantir_diretorios()
        if args.stage == "raw":
            res = ingest_raw(seed=args.seed)
            print(f"[OK] Ingestão Raw concluída. {len(res['arquivos'])} arquivos gerados.")
        elif args.stage == "interim":
            res = process_interim(validar_integridade=True)
            print(f"[OK] Camada Interim concluída. Tabelas: {res['tabelas_processadas']}")
        elif args.stage == "processed":
            res = build_processed(exportar_dashboard=True)
            print(f"[OK] Camada Processed concluída. Marts: {res['marts_gerados']}")
        elif args.stage == "all":
            res = run_full_pipeline(seed=args.seed)
            print("[OK] Pipeline completo executado com sucesso (Raw -> Interim -> Processed).")
    except Exception as exc:
        print(f"[ERRO] Falha na execução do pipeline: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
