"""Per-expert Delphi rows: paired reduction, bootstrap ranks, top concerns."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from riskdlab.experts import bootstrap_rankings, expert_level_table, paired_reduction, top_concerns


@pytest.fixture
def severity_expert():
    rows = []
    rng = np.random.default_rng(0)
    # risk 1: big, consistent reduction; risk 2: none; risk 3: noisy
    for expert in range(1, 21):
        rows.append({"expert_hash": f"e_{expert:03d}", "risk_number": 1, "scenario": "bau", "sev5": 30.0})
        rows.append({"expert_hash": f"e_{expert:03d}", "risk_number": 1, "scenario": "pm", "sev5": 10.0})
        rows.append({"expert_hash": f"e_{expert:03d}", "risk_number": 2, "scenario": "bau", "sev5": 15.0})
        rows.append({"expert_hash": f"e_{expert:03d}", "risk_number": 2, "scenario": "pm", "sev5": 15.0})
        rows.append({"expert_hash": f"e_{expert:03d}", "risk_number": 3, "scenario": "bau", "sev5": float(rng.integers(0, 40))})
        rows.append({"expert_hash": f"e_{expert:03d}", "risk_number": 3, "scenario": "pm", "sev5": float(rng.integers(0, 40))})
    # an expert who rated only bau for risk 1 must be dropped from the paired table
    rows.append({"expert_hash": "e_999", "risk_number": 1, "scenario": "bau", "sev5": 99.0})
    frame = pd.DataFrame(rows)
    for column in ("sev1", "sev2", "sev3", "sev4"):
        frame[column] = 0.0
    return frame


@pytest.fixture
def risks():
    return pd.DataFrame(
        {"risk_number": [1, 2, 3], "taxonomy_id": ["7.1", "6.5", "4.2"], "short_name": ["A", "B", "C"]}
    )


def test_paired_table_keeps_only_experts_with_both_scenarios(severity_expert):
    table = expert_level_table(severity_expert)
    assert "e_999" not in set(table["expert_hash"])
    assert len(table) == 60


def test_paired_reduction_has_se_and_counts(severity_expert, risks):
    out = paired_reduction(severity_expert, risks)
    assert list(out.index) == ["4.2", "6.5", "7.1"]
    assert out.loc["7.1", "reduction"] == pytest.approx(20.0)
    assert out.loc["7.1", "reduction_se"] == pytest.approx(0.0)
    assert out.loc["6.5", "reduction"] == pytest.approx(0.0)
    assert out.loc["7.1", "n_experts"] == 20
    assert out.loc["4.2", "reduction_se"] > 0


def test_unknown_level_is_an_error(severity_expert):
    with pytest.raises(ValueError):
        expert_level_table(severity_expert, level="apocalyptic")


def test_bootstrap_reports_rank_spread_and_agreement(severity_expert, risks):
    out = bootstrap_rankings(severity_expert, risks, samples=50, seed=1)
    assert out.loc["7.1", "reduction_point_rank"] == 1
    assert out.loc["7.1", "reduction_rank_p95"] == 1, "a consistent 20pp reduction never loses rank 1"
    assert 0.0 <= out.attrs["pair_agreement"]["bau"] <= 1.0
    assert out.attrs["samples"] == 50


def test_bootstrap_is_deterministic_for_a_seed(severity_expert, risks):
    a = bootstrap_rankings(severity_expert, risks, samples=30, seed=7)
    b = bootstrap_rankings(severity_expert, risks, samples=30, seed=7)
    pd.testing.assert_frame_equal(a, b)
    assert a.attrs["pair_agreement"] == b.attrs["pair_agreement"]


def test_top_concerns_joins_on_risk_number(risks):
    table = pd.DataFrame(
        {
            "risk_number": [1, 2, 3],
            "count": [50, 10, 30],
            "percentage": [25.0, 5.0, 15.0],
            "domain_balanced_percentage": [20.0, 4.0, 12.0],
            "insider_rate": [30.0, 6.0, 18.0],
            "outsider_percentage": [10.0, 2.0, 6.0],
            "total_respondents": [200, 200, 200],
        }
    )
    out = top_concerns(table, risks)
    assert out.loc["7.1", "concern_pct"] == 25.0
    assert out.loc["6.5", "short_name"] == "B"
