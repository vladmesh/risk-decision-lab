"""The gap map on synthetic grants, labels and Delphi rows."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from riskdlab.gapmap import build_gap_map, funding_by_label


@pytest.fixture
def grants():
    return pd.DataFrame(
        {
            "source": ["coefficient", "coefficient", "eafunds", "manifund", "sff"],
            "grant_id": ["c1", "c2", "e1", "m1", "s1"],
            "year": pd.array([2025, 2023, 2025, 2026, 2025], dtype="Int64"),
            "date": [""] * 5,
            "funder_program": [""] * 5,
            "grantee": ["Split Org", "Legacy Org", "Unsplit Org", "Other", "Field Org"],
            "title": [""] * 5,
            "text": [""] * 5,
            "amount_usd": [1_000_000.0, 500_000.0, 20_000.0, 0.0, 300_000.0],
            "amount_kind": ["granted", "granted", "granted", "raised", "recommended"],
            "ai_scope": [True, True, True, True, True],
            "url": [""] * 5,
        }
    )


@pytest.fixture
def labels():
    return pd.DataFrame(
        {
            "grant_id": ["c1", "c2", "e1", "m1", "s1"],
            "primary": ["7.1", "7.1", "7.4", "7.2", "field"],
            "secondary": ["", "", "", "", ""],
            "confidence": ["high", "high", "low", "high", "medium"],
            "basis": [""] * 5,
        }
    )


def test_funding_by_label_sums_dollars_and_counts_funded_grants(grants, labels):
    table = funding_by_label(grants, labels)
    assert table.loc["7.1", "fund_usd"] == 1_500_000.0
    assert table.loc["7.1", "fund_n_grants"] == 2
    assert table.loc["7.4", "fund_n_low_confidence"] == 1
    assert table.loc["7.2", "fund_n_grants"] == 0, "an unfunded Manifund proposal is not a grant"
    assert table.loc["field", "fund_usd_sff"] == 300_000.0
    assert table["fund_share"].sum() == pytest.approx(1.0)
    assert table.attrs["n_grants"] == 4


def test_funding_by_label_year_window_and_sources(grants, labels):
    table = funding_by_label(grants, labels, year_from=2024)
    assert table.loc["7.1", "fund_usd"] == 1_000_000.0
    table = funding_by_label(grants, labels, sources=("sff",))
    assert table.attrs["usd_total"] == 300_000.0


def test_funding_splits_allocate_dollars_without_double_counting(grants, labels):
    from riskdlab.funding.splits import read_splits

    splits = read_splits(Path(__file__).parent / "fixtures" / "programme-splits.csv")
    table = funding_by_label(grants, labels, splits=splits)
    assert table.loc["7.1", "fund_usd"] == 1_100_000.0
    assert table.loc["6.5", "fund_usd"] == 400_000.0
    assert table.loc["7.4", "fund_usd"] == 20_000.0, "an unsplit grant keeps its original label"
    assert table.loc["7.1", "fund_n_grants"] == 2
    assert table.attrs["n_grants"] == 4
    assert table.attrs["split_n_grantees"] == 1
    assert table.attrs["split_usd"] == 1_000_000.0


@pytest.fixture
def delphi():
    risks = pd.DataFrame(
        {"risk_number": [1, 2, 3], "taxonomy_id": ["7.1", "7.2", "7.4"], "short_name": ["A", "B", "C"]}
    )
    rows = []
    for expert in range(1, 16):
        for risk, bau, pm in ((1, 30.0, 10.0), (2, 20.0, 12.0), (3, 8.0, 6.0)):
            rows.append({"expert_hash": f"e_{expert:03d}", "risk_number": risk, "scenario": "bau", "sev5": bau + (expert % 3)})
            rows.append({"expert_hash": f"e_{expert:03d}", "risk_number": risk, "scenario": "pm", "sev5": pm})
    severity_expert = pd.DataFrame(rows)
    for column in ("sev1", "sev2", "sev3", "sev4"):
        severity_expert[column] = 0.0
    top = pd.DataFrame(
        {
            "risk_number": [1, 2, 3],
            "count": [30, 20, 5],
            "percentage": [30.0, 20.0, 5.0],
            "domain_balanced_percentage": [28.0, 18.0, 4.0],
            "insider_rate": [35.0, 22.0, 6.0],
            "outsider_percentage": [21.0, 14.0, 2.0],
            "total_respondents": [100, 100, 100],
        }
    )
    return {"risks": risks, "severity_expert": severity_expert, "top_concerns": top}


def test_gap_map_joins_experts_and_money_and_keeps_reserved_rows(delphi, grants, labels):
    table = build_gap_map(delphi, grants, labels, samples=20, seed=3)
    assert table.loc["7.1", "delphi_bau_pct"] == pytest.approx(31.0)
    assert table.loc["7.1", "delphi_bau_point_rank"] == 1
    assert table.loc["7.1", "fund_usd"] == 1_500_000.0
    assert table.loc["7.4", "delphi_concern_pct"] == 5.0
    assert table.loc["field", "fund_usd"] == 300_000.0
    assert np.isnan(table.loc["field", "delphi_bau_pct"])
    assert table.loc["field", "short_name"] == "(field-building: talent & community)"
    assert "pair_agreement" in table.attrs
    # domains with no grants at all are still rows, with zero money
    assert table.loc["1.1", "fund_usd"] == 0.0
