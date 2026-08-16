import pandas as pd
import pytest

from riskdlab.data import (
    delphi_domains,
    load_domains,
    read_delphi,
    read_repository,
    repository_domain_counts,
)


def test_read_delphi_returns_the_two_tables(delphi_path):
    tables = read_delphi(delphi_path)
    assert set(tables) == {"risks", "severity_aggregate"}
    assert all(isinstance(c, str) for c in tables["risks"].columns)
    assert len(tables["severity_aggregate"]) == 20  # 5 domains x 2 scenarios x 2 levels


def test_delphi_domains_pivots_to_one_row_per_domain(risks_frame, severity_frame):
    domains = delphi_domains(risks_frame, severity_frame)
    assert list(domains.index) == ["4.2", "6.4", "6.5", "7.1", "7.2"]
    assert domains.index.name == "domain"
    assert domains.loc["6.4", "bau"] == pytest.approx(16.61)
    assert domains.loc["6.4", "pm"] == pytest.approx(7.30)
    assert domains.loc["6.4", "short_name"] == "Competitive dynamics"


def test_delphi_domains_keeps_confidence_bounds(risks_frame, severity_frame):
    domains = delphi_domains(risks_frame, severity_frame)
    width = domains["bau_ci_upper"] - domains["bau_ci_lower"]
    assert width.round(2).eq(7.20).all()


def test_delphi_domains_filters_by_harm_level(risks_frame, severity_frame):
    catastrophic = delphi_domains(risks_frame, severity_frame, level="catastrophic")
    major = delphi_domains(risks_frame, severity_frame, level="major")
    assert catastrophic.loc["4.2", "bau"] == pytest.approx(21.00)
    assert major.loc["4.2", "bau"] == pytest.approx(79.00)


def test_delphi_domains_rejects_an_unknown_harm_level(risks_frame, severity_frame):
    with pytest.raises(ValueError, match="no rows for harm level"):
        delphi_domains(risks_frame, severity_frame, level="apocalyptic")


def test_read_repository_finds_the_header_on_the_third_row(repository_path):
    repo = read_repository(repository_path)
    assert "Sub-domain" in repo.columns
    assert "Category level" in repo.columns


def test_repository_counts_only_risk_level_rows(repository_path):
    repo = read_repository(repository_path)
    counts = repository_domain_counts(repo)
    # 3 risk-level rows for 4.2; the additional-evidence row is not one of them
    assert counts["4.2"] == 3
    assert counts["6.4"] == 1
    assert "X.0" not in counts.index  # served by the N.N regex, not by the level filter


def test_repository_counts_all_rows_when_asked(repository_path):
    repo = read_repository(repository_path)
    counts = repository_domain_counts(repo, risk_rows_only=False)
    assert counts["4.2"] == 4


def test_load_domains_joins_delphi_and_repository(delphi_path, repository_path):
    domains = load_domains(delphi_path, repository_path)
    assert domains.loc["4.2", "reduction"] == pytest.approx(21.00 - 11.90)
    assert domains.loc["4.2", "n_risk_rows"] == 3
    # a domain with no repository rows joins as missing, not as zero
    assert pd.isna(domains.loc["7.1", "n_risk_rows"])


def test_load_domains_without_the_repository(delphi_path):
    domains = load_domains(delphi_path, repository_path=None)
    assert "n_risk_rows" not in domains.columns


def test_missing_raw_data_points_at_the_readme(tmp_path):
    with pytest.raises(FileNotFoundError, match="README"):
        load_domains(tmp_path / "nope.rds")
