"""Testes de conformidade da arquitetura de dados e organização física em camadas.

Valida a presença das camadas de dados ativas (Raw, Interim e Processed),
presença de documentação de referência (references/), integridade de regras no gitignore
e ausência de diretórios desnecessários ou vazios no repositório.
"""

from pathlib import Path

import src.config as cfg


def test_topologia_camadas_dados_presente() -> None:
    """Verifica se as camadas ativas de dados (Raw, Interim, Processed) foram criadas."""
    diretorios_obrigatorios: list[Path] = [
        cfg.DATA_DIR,
        cfg.RAW_DATA_DIR,
        cfg.RAW_SINGULAR_DIR,
        cfg.RAW_IFDATA_DIR,
        cfg.RAW_REF_DIR,
        cfg.INTERIM_DATA_DIR,
        cfg.PROCESSED_DATA_DIR,
        cfg.PROCESSED_MARTS_DIR,
        cfg.REFERENCES_DIR,
        cfg.DOCS_DIR,
    ]

    for d in diretorios_obrigatorios:
        assert d.exists(), f"Diretório ativo obrigatório '{d}' não encontrado."
        assert d.is_dir(), f"Caminho '{d}' não é um diretório válido."


def test_diretorios_desnecessarios_nao_presentes() -> None:
    """Garante que diretórios vazios ou desnecessários no momento não existam no projeto."""
    diretorios_vedados: list[Path] = [
        cfg.PROJECT_ROOT / "models",
        cfg.PROJECT_ROOT / "notebooks",
        cfg.PROJECT_ROOT / "reports",
        cfg.PROJECT_ROOT / "data" / "external",
        cfg.PROJECT_ROOT / "scratch",
    ]

    for d in diretorios_vedados:
        assert not d.exists(), f"Diretório desnecessário '{d}' não deve ser criado no projeto."


def test_gitkeep_presentes_nas_folhas_de_dados() -> None:
    """Verifica se os marcadores .gitkeep estão posicionados nas pastas ativas de dados."""
    gitkeeps: list[Path] = [
        cfg.RAW_SINGULAR_DIR / ".gitkeep",
        cfg.RAW_IFDATA_DIR / ".gitkeep",
        cfg.RAW_REF_DIR / ".gitkeep",
        cfg.INTERIM_DATA_DIR / ".gitkeep",
        cfg.PROCESSED_MARTS_DIR / ".gitkeep",
        cfg.REFERENCES_DIR / ".gitkeep",
    ]

    for gk in gitkeeps:
        assert gk.exists(), f"Arquivo marcador de persistência '{gk}' não encontrado."


def test_documentacao_referencias_presente() -> None:
    """Verifica a existência dos documentos normativos e dicionários em references/."""
    dicionario = cfg.REFERENCES_DIR / "data_dictionary.md"
    sumario_4966 = cfg.REFERENCES_DIR / "resolucao_4966_summary.md"

    assert dicionario.exists(), "Dicionário de dados não encontrado em references/."
    assert sumario_4966.exists(), "Sumário da Resolução 4.966 não encontrado em references/."

    conteudo_dic = dicionario.read_text(encoding="utf-8")
    assert "f_Carteira_Mensal" in conteudo_dic
    assert "d_Calendario" in conteudo_dic
    assert "f_DRE_Gerencial" in conteudo_dic

    conteudo_sum = sumario_4966.read_text(encoding="utf-8")
    assert "Estágio 1" in conteudo_sum
    assert "Estágio 2" in conteudo_sum
    assert "Estágio 3" in conteudo_sum
    assert "Ativo Problemático" in conteudo_sum


def test_regras_higiene_gitignore() -> None:
    """Valida que o arquivo .gitignore ignora adequadamente artefatos gerados de dados."""
    caminho_gitignore = cfg.PROJECT_ROOT / ".gitignore"
    assert caminho_gitignore.exists(), "Arquivo .gitignore não encontrado na raiz."

    linhas = caminho_gitignore.read_text(encoding="utf-8").splitlines()
    regras = [linha.strip() for linha in linhas if linha.strip() and not linha.startswith("#")]

    assert "data/**" in regras
    assert "!data/**/.gitkeep" in regras
    assert "*.duckdb" in regras
    assert "*.parquet" in regras
