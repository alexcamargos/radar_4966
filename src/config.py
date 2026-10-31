"""Configuração centralizada de caminhos, governança e parâmetros do projeto.

Define a topologia de diretórios conforme o padrão Cookiecutter Data Science (CCDS v2)
e estabelece referências absolutas para os diretórios das camadas de dados (Medallion:
Raw, Interim, Processed e External), modelos, notebooks, relatórios e referências.
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

EXTERNAL_DATA_DIR: Path = DATA_DIR / "external"

# Diretórios canônicos complementares do CCDS
MODELS_DIR: Path = PROJECT_ROOT / "models"
NOTEBOOKS_DIR: Path = PROJECT_ROOT / "notebooks"
REFERENCES_DIR: Path = PROJECT_ROOT / "references"
REPORTS_DIR: Path = PROJECT_ROOT / "reports"
REPORTS_FIGURES_DIR: Path = REPORTS_DIR / "figures"
DOCS_DIR: Path = PROJECT_ROOT / "docs"
SCRATCH_DIR: Path = PROJECT_ROOT / "scratch"

# Diretório do dashboard nativo web
DASHBOARD_DIR: Path = PROJECT_ROOT / "src" / "dashboard"
DASHBOARD_DATA_DIR: Path = DASHBOARD_DIR / "data"
DASHBOARD_DATA_PATH: Path = DASHBOARD_DATA_DIR / "dashboard_data.json"

# Parâmetros de governança e regulação
DEFAULT_SEED: int = 42
DATA_MARCO_4966: date = date(2025, 1, 1)


def garantir_diretorios() -> list[Path]:
    """Cria fisicamente toda a topologia canônica de diretórios do projeto caso não existam.

    Garante que os diretórios das três camadas de dados (raw, interim, processed, external),
    bem como as pastas de modelos, notebooks, referências, relatórios e scratch estejam
    disponíveis no sistema de arquivos.

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
        EXTERNAL_DATA_DIR,
        MODELS_DIR,
        NOTEBOOKS_DIR,
        REFERENCES_DIR,
        REPORTS_DIR,
        REPORTS_FIGURES_DIR,
        DOCS_DIR,
        SCRATCH_DIR,
        DASHBOARD_DATA_DIR,
    ]

    for d in diretorios:
        d.mkdir(parents=True, exist_ok=True)

    return diretorios
