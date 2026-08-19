import pandas as pd
import pytest

from riskdlab.assumptions import AssumptionSet
from riskdlab.data import load_domains
from riskdlab.ranking import rank_domains
from riskdlab.stability import analyze_cost_stability


@pytest.fixture
def domains(delphi_path, repository_path):
    return load_domains(delphi_path, repository_path)


def test_fixed_costs_reproduce_the_single_ranking(domains):
    assumptions = AssumptionSet(
        name="fixed",
        objective="achievable_reduction",
        scenario="pm",
        cost_multipliers={"6.4": 5, "6.5": 4, "4.2": 3, "7.1": 2, "7.2": 1.5},
    )
    ranked = rank_domains(domains, assumptions)
    stable = analyze_cost_stability(domains, assumptions, samples=20, top=3)

    expected = ranked["rank"].sort_index()
    assert stable["best_rank"].sort_index().equals(expected)
    assert stable["worst_rank"].sort_index().equals(expected)
    assert stable.loc["7.2", "top_3_share"] == 1.0
    assert stable.loc["6.5", "top_3_share"] == 0.0


def test_ranged_cost_analysis_is_reproducible_and_reports_ordered_rank_bounds(domains):
    assumptions = AssumptionSet(
        name="ranged",
        objective="achievable_reduction",
        scenario="pm",
        default_cost_range=[1, 4],
    )
    first = analyze_cost_stability(domains, assumptions, samples=200, seed=7)
    second = analyze_cost_stability(domains, assumptions, samples=200, seed=7)

    pd.testing.assert_frame_equal(first, second)
    assert (first["cost_min"] == 1.0).all()
    assert (first["cost_max"] == 4.0).all()
    assert (first["best_rank"] <= first["median_rank"]).all()
    assert (first["median_rank"] <= first["worst_rank"]).all()
    assert first["top_3_share"].between(0, 1).all()
    assert (first["best_rank"] < first["worst_rank"]).any()


@pytest.mark.parametrize(
    "kwargs, message",
    [({"samples": 0}, "samples"), ({"top": 0}, "top")],
)
def test_invalid_analysis_options_are_rejected(domains, kwargs, message):
    with pytest.raises(ValueError, match=message):
        analyze_cost_stability(domains, AssumptionSet(name="x"), **kwargs)
