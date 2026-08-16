"""Import of the MIT data into one domain-level table.

Loading logic is lifted from `experiments/recon.py` and `experiments/join_test.py`:
the Delphi snapshot carries the numbers (24 domains x 2 scenarios x 5 harm levels, with
bootstrap CIs), the Risk Repository carries the risks (1835 risk-level rows) and joins to
Delphi by the N.N sub-domain code. The join is clean, but one Delphi estimate covers ~54
repository rows, so `n_risk_rows` is kept as a column: it is how coarse the number is.
"""

from __future__ import annotations

import warnings
from pathlib import Path

import pandas as pd

DEFAULT_DELPHI_PATH = Path("data/raw/delphi/safe_for_osf/delphi_snapshot.rds")
DEFAULT_REPOSITORY_PATH = Path("data/raw/ai-risk-repository.xlsx")

REPOSITORY_SHEET = "AI Risk Database v4"
REPOSITORY_HEADER_ROW = 2
SUBDOMAIN_COLUMN = "Sub-domain"
CATEGORY_LEVEL_COLUMN = "Category level"

#: Category levels that are not a risk. Excluding them is the difference between
#: 2574 rows and the 1835 rows that actually describe a risk (see research recon).
NON_RISK_CATEGORY_LEVELS = frozenset({"paper", "additional evidence"})

SCENARIOS = ("bau", "pm")
DEFAULT_LEVEL = "catastrophic"

_CODE_RE = r"^\s*(\d+\.\d+)"

_MISSING_DATA_HINT = (
    "raw MIT data is not in git; see the download commands in README.md"
)


def _str_columns(df: pd.DataFrame) -> pd.DataFrame:
    """The rds reader hands back numpy string column labels; make them plain str."""
    df = df.copy()
    df.columns = [str(c) for c in df.columns]
    return df


def _require(path: Path) -> Path:
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"{path}: {_MISSING_DATA_HINT}")
    return path


def read_delphi(path: Path | str = DEFAULT_DELPHI_PATH) -> dict[str, pd.DataFrame]:
    """Read the two Delphi tables the prototype needs: the risk index and the estimates."""
    import rdata  # imported lazily: the pure functions below are usable without it

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        snapshot = rdata.read_rds(_require(path))
    snapshot = {str(k): v for k, v in snapshot.items()}
    meta = {str(k): v for k, v in snapshot["meta"].items()}
    return {
        "risks": _str_columns(meta["risks"]),
        "severity_aggregate": _str_columns(snapshot["severity_aggregate"]),
    }


def delphi_domains(
    risks: pd.DataFrame,
    severity_aggregate: pd.DataFrame,
    level: str = DEFAULT_LEVEL,
) -> pd.DataFrame:
    """One row per domain: probability of `level` harm per scenario, with CI bounds.

    Indexed by the taxonomy code (`6.4`), which is what the Risk Repository joins on.
    """
    sev = severity_aggregate[severity_aggregate["level"] == level]
    if sev.empty:
        known = sorted(severity_aggregate["level"].astype(str).unique())
        raise ValueError(f"no rows for harm level {level!r}; available: {known}")

    wide = sev.pivot(index="risk_number", columns="scenario", values="pct")
    missing = [s for s in SCENARIOS if s not in wide.columns]
    if missing:
        raise ValueError(f"Delphi estimates are missing scenario(s): {missing}")

    out = wide[list(SCENARIOS)].copy()
    for bound, column in (("ci_lower", "pct_ci_lower"), ("ci_upper", "pct_ci_upper")):
        if column not in sev.columns:
            continue
        wide_bound = sev.pivot(index="risk_number", columns="scenario", values=column)
        for scenario in SCENARIOS:
            out[f"{scenario}_{bound}"] = wide_bound[scenario]

    index = risks.set_index("risk_number")[["taxonomy_id", "short_name"]]
    out = out.join(index, how="inner")
    out["domain"] = out["taxonomy_id"].astype(str)
    out["short_name"] = out["short_name"].astype(str)
    out = out.drop(columns=["taxonomy_id"]).set_index("domain").sort_index()

    front = ["short_name", *SCENARIOS]
    return out[front + [c for c in out.columns if c not in front]]


def read_repository(path: Path | str = DEFAULT_REPOSITORY_PATH) -> pd.DataFrame:
    """Read the `AI Risk Database v4` sheet (the header sits on the third row)."""
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        repo = pd.read_excel(
            _require(path), sheet_name=REPOSITORY_SHEET, header=REPOSITORY_HEADER_ROW
        )
    return repo.dropna(how="all")


def repository_domain_counts(repo: pd.DataFrame, risk_rows_only: bool = True) -> pd.Series:
    """How many repository risk rows fall under each N.N sub-domain code.

    With `risk_rows_only`, paper-level and additional-evidence rows are dropped: counting
    them inflates the repository by half, which is the trap named in the recon note.
    """
    if risk_rows_only and CATEGORY_LEVEL_COLUMN in repo.columns:
        level = repo[CATEGORY_LEVEL_COLUMN].astype(str).str.strip().str.lower()
        repo = repo[~level.isin(NON_RISK_CATEGORY_LEVELS)]
    codes = (
        repo[SUBDOMAIN_COLUMN].dropna().astype(str).str.extract(_CODE_RE)[0].dropna()
    )
    return codes.value_counts().rename("n_risk_rows").rename_axis("domain")


def load_domains(
    delphi_path: Path | str = DEFAULT_DELPHI_PATH,
    repository_path: Path | str | None = DEFAULT_REPOSITORY_PATH,
    level: str = DEFAULT_LEVEL,
) -> pd.DataFrame:
    """The prototype's single input table: one row per Delphi domain.

    Columns: `short_name`, `bau`, `pm` (percent of experts expecting `level` harm),
    the CI bounds of both, `reduction` (bau - pm, the achievable reduction in pp) and,
    when the repository is available, `n_risk_rows`.
    """
    delphi = read_delphi(delphi_path)
    domains = delphi_domains(delphi["risks"], delphi["severity_aggregate"], level=level)
    domains["reduction"] = domains["bau"] - domains["pm"]

    if repository_path is not None:
        counts = repository_domain_counts(read_repository(repository_path))
        domains["n_risk_rows"] = counts.reindex(domains.index)

    return domains
