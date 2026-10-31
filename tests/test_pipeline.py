"""Testes unitários e de integração do pipeline de dados em camadas (CCDS v2 / Medallion).

Valida cálculo de hashes SHA-256, detecção de violação de integridade, ingestão bruta,
materialização colunar da camada interim e compilação dos marts analíticos no DuckDB.
"""

from pathlib import Path

import pytest

from src.pipeline import (
    build_processed,
    calcular_hash_sha256,
    ingest_raw,
    process_interim,
    run_full_pipeline,
)


def test_calcular_hash_sha256(tmp_path: Path) -> None:
    """Verifica o cálculo determinístico de hash SHA-256 em arquivo temporário."""
    arquivo_teste = tmp_path / "teste.txt"
    arquivo_teste.write_text("Radar 4966 - Cooperativas de Credito", encoding="utf-8")

    hash_resultado = calcular_hash_sha256(arquivo_teste)
    assert isinstance(hash_resultado, str)
    assert len(hash_resultado) == 64

    # Repetir para certificar determinismo
    assert calcular_hash_sha256(arquivo_teste) == hash_resultado


def test_calcular_hash_arquivo_inexistente(tmp_path: Path) -> None:
    """Verifica que calcular_hash_sha256 levanta FileNotFoundError para caminho inexistente."""
    arquivo_fantasma = tmp_path / "inexistente.txt"
    with pytest.raises(FileNotFoundError, match="não encontrado"):
        calcular_hash_sha256(arquivo_fantasma)


def test_ingest_raw_em_diretorio_isolado(tmp_path: Path) -> None:
    """Valida a execução da camada bruta (Raw) em ambiente isolado."""
    dir_raw = tmp_path / "data" / "raw"
    manifesto = ingest_raw(seed=42, diretorio_raiz_raw=dir_raw)

    assert manifesto["versao_manifesto"] == "1.0"
    assert manifesto["algoritmo"] == "SHA-256"
    assert len(manifesto["arquivos"]) == 7

    caminho_manifesto = dir_raw / "manifest_sha256.json"
    assert caminho_manifesto.exists()

    # Validação dos arquivos brutos gerados
    assert (dir_raw / "singular" / "carteira_mensal.jsonl").exists()
    assert (dir_raw / "singular" / "dre_gerencial.json").exists()
    assert (dir_raw / "singular" / "associados.json").exists()
    assert (dir_raw / "singular" / "linhas_credito.json").exists()
    assert (dir_raw / "singular" / "calendario.json").exists()
    assert (dir_raw / "bacen" / "ifdata" / "ifdata_trimestral.json").exists()
    assert (dir_raw / "bacen" / "ref" / "ref_semestral.json").exists()


def test_process_interim_em_diretorio_isolado(tmp_path: Path) -> None:
    """Valida a transformação da camada Raw para Interim em formato Parquet."""
    dir_raw = tmp_path / "data" / "raw"
    dir_interim = tmp_path / "data" / "interim"

    ingest_raw(seed=42, diretorio_raiz_raw=dir_raw)
    res_interim = process_interim(
        diretorio_origem_raw=dir_raw,
        diretorio_destino_interim=dir_interim,
        validar_integridade=True,
    )

    assert res_interim["status"] == "sucesso"
    assert res_interim["tabelas_processadas"]["carteira_mensal"] > 0

    # Certificar materialização dos arquivos Parquet
    arquivos_esperados = [
        "calendario_staging.parquet",
        "associados_staging.parquet",
        "linhas_credito_staging.parquet",
        "carteira_staging.parquet",
        "dre_staging.parquet",
        "ifdata_staging.parquet",
        "ref_staging.parquet",
    ]
    for arq in arquivos_esperados:
        caminho_parquet = dir_interim / arq
        assert caminho_parquet.exists(), f"Arquivo '{arq}' não gerado na camada interim."
        assert caminho_parquet.stat().st_size > 0


def test_process_interim_deteccao_adulteracao_hash(tmp_path: Path) -> None:
    """Verifica que adulterações físicas em dados brutos disparam ValueError de integridade."""
    dir_raw = tmp_path / "data" / "raw"
    dir_interim = tmp_path / "data" / "interim"

    ingest_raw(seed=42, diretorio_raiz_raw=dir_raw)

    # Adulterar intencionalmente um arquivo bruto após o manifesto ter sido calculado
    arq_carteira = dir_raw / "singular" / "carteira_mensal.jsonl"
    with open(arq_carteira, "a", encoding="utf-8") as f:
        f.write("linha_corrompida_invalida\n")

    with pytest.raises(ValueError, match="Integridade violada"):
        process_interim(
            diretorio_origem_raw=dir_raw,
            diretorio_destino_interim=dir_interim,
            validar_integridade=True,
        )


def test_build_processed_em_diretorio_isolado(tmp_path: Path) -> None:
    """Valida a compilação dos marts analíticos em Parquet e catálogo DuckDB."""
    dir_raw = tmp_path / "data" / "raw"
    dir_interim = tmp_path / "data" / "interim"
    dir_processed = tmp_path / "data" / "processed"
    duckdb_banco = dir_processed / "teste_radar.duckdb"

    ingest_raw(seed=42, diretorio_raiz_raw=dir_raw)
    process_interim(
        diretorio_origem_raw=dir_raw,
        diretorio_destino_interim=dir_interim,
    )
    res_processed = build_processed(
        diretorio_origem_interim=dir_interim,
        diretorio_destino_processed=dir_processed,
        caminho_duckdb=duckdb_banco,
        exportar_dashboard=True,
    )

    assert res_processed["status"] == "sucesso"
    assert duckdb_banco.exists()
    assert (dir_processed / "dashboard_data.json").exists()

    marts_dir = dir_processed / "marts"
    assert (marts_dir / "f_carteira_mensal.parquet").exists()
    assert (marts_dir / "f_dre_gerencial.parquet").exists()
    assert (marts_dir / "f_ifdata_sncc.parquet").exists()
    assert (marts_dir / "f_ref_macro_bcb.parquet").exists()
    assert (marts_dir / "vintages_mob.parquet").exists()
    assert (marts_dir / "metricas_consolidadas.parquet").exists()


def test_run_full_pipeline_integrado() -> None:
    """Verifica a orquestração do ciclo analítico completo ponta a ponta."""
    res = run_full_pipeline(seed=42)

    assert res["status"] == "concluido"
    assert "camada_raw" in res
    assert "camada_interim" in res
    assert "camada_processed" in res
