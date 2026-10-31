"""Configuração centralizada de caminhos, governança e parâmetros do projeto.

Define a organização física dos dados em camadas (Medallion: Raw, Interim e Processed)
conforme os princípios do Cookiecutter Data Science (CCDS v2), mantendo estritamente
os diretórios ativos e necessários para o ciclo de vida analítico do projeto.
"""

from datetime import date
from pathlib import Path

# Raiz do projeto
PROJECT_ROOT: Path = Path(__file__).resolve().parent.parent

# Topologia de dados em camadas (Medallion / CCDS v2)
DATA_DIR: Path = PROJECT_ROOT / "data"
RAW_DATA_DIR: Path = DATA_DIR / "raw"
RAW_SINGULAR_DIR: Path = RAW_DATA_DIR / "singular"
RAW_BACEN_DIR: Path = RAW_DATA_DIR / "bacen"
RAW_IFDATA_DIR: Path = RAW_BACEN_DIR / "ifdata"
RAW_REF_DIR: Path = RAW_BACEN_DIR / "ref"
RAW_MANIFEST_PATH: Path = RAW_DATA_DIR / "manifest_sha256.json"

INTERIM_DATA_DIR: Path = DATA_DIR / "interim"

PROCESSED_DATA_DIR: Path = DATA_DIR / "processed"
PROCESSED_MARTS_DIR: Path = PROCESSED_DATA_DIR / "marts"
PROCESSED_DUCKDB_PATH: Path = PROCESSED_DATA_DIR / "radar_4966.duckdb"
PROCESSED_DASHBOARD_DATA_PATH: Path = PROCESSED_DATA_DIR / "dashboard_data.json"

# Referências normativas e documentação
REFERENCES_DIR: Path = PROJECT_ROOT / "references"
DOCS_DIR: Path = PROJECT_ROOT / "docs"

# Diretório do dashboard nativo web
DASHBOARD_DIR: Path = PROJECT_ROOT / "src" / "dashboard"
DASHBOARD_DATA_DIR: Path = DASHBOARD_DIR / "data"
DASHBOARD_DATA_PATH: Path = DASHBOARD_DATA_DIR / "dashboard_data.json"

# Parâmetros de governança e regulação
DEFAULT_SEED: int = 42
DATA_MARCO_4966: date = date(2025, 1, 1)


def garantir_diretorios() -> list[Path]:
    """Cria fisicamente os diretórios ativos necessários para o ciclo de dados do projeto.

    Assegura que as pastas das três camadas de dados (raw, interim, processed),
    o diretório de referências normativas e o destino dos dados do dashboard
    estejam criados no sistema de arquivos.

    Returns:
        Lista com todos os objetos Path dos diretórios assegurados no sistema.

    Raises:
        OSError: Se houver falha de permissão na criação de algum dos diretórios.
    """
    diretorios: list[Path] = [
        DATA_DIR,
        RAW_DATA_DIR,
        RAW_SINGULAR_DIR,
        RAW_BACEN_DIR,
        RAW_IFDATA_DIR,
        RAW_REF_DIR,
        INTERIM_DATA_DIR,
        PROCESSED_DATA_DIR,
        PROCESSED_MARTS_DIR,
        REFERENCES_DIR,
        DOCS_DIR,
        DASHBOARD_DATA_DIR,
    ]

    for d in diretorios:
        d.mkdir(parents=True, exist_ok=True)

    return diretorios
