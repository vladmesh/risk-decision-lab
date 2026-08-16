import pytest

from riskdlab.assumptions import AssumptionSet
from riskdlab.data import load_domains
from riskdlab.ranking import diff_rankings, pair_order_agreement, rank_domains


@pytest.fixture
def domains(delphi_path, repository_path):
    return load_domains(delphi_path, repository_path)


@pytest.fixture
def bau():
    return AssumptionSet(name="bau", objective="catastrophic_probability", scenario="bau")


@pytest.fixture
def pm_costed():
    return AssumptionSet(
        name="pm",
        objective="achievable_reduction",
        scenario="pm",
        cost_multipliers={"6.4": 5.0, "6.5": 4.0, "4.2": 3.0, "7.1": 2.0, "7.2": 1.5},
    )


def test_ranking_by_probability_follows_the_bau_column(domains, bau):
    ranked = rank_domains(domains, bau)
    assert list(ranked.index) == ["7.2", "4.2", "7.1", "6.4", "6.5"]
    assert ranked.loc["7.2", "rank"] == 1
    assert ranked.loc["7.2", "base_score"] == pytest.approx(21.51)
    assert (ranked["cost_multiplier"] == 1.0).all()


def test_ranking_by_reduction_divides_by_the_assumed_cost(domains, pm_costed):
    ranked = rank_domains(domains, pm_costed)
    assert ranked.loc["6.4", "base_score"] == pytest.approx(9.31)
    assert ranked.loc["6.4", "score"] == pytest.approx(9.31 / 5.0)
    assert list(ranked.index) == ["7.2", "7.1", "4.2", "6.4", "6.5"]


def test_equal_costs_leave_the_reduction_ranking_alone(domains):
    plain = AssumptionSet(name="plain", objective="achievable_reduction", scenario="pm")
    ranked = rank_domains(domains, plain)
    assert list(ranked.index) == ["6.4", "7.2", "4.2", "7.1", "6.5"]


def test_ranking_carries_the_granularity_column(domains, bau):
    ranked = rank_domains(domains, bau)
    assert ranked.loc["4.2", "n_risk_rows"] == 3


def test_ties_share_a_rank(domains):
    flat = domains.copy()
    flat["bau"] = 10.0
    ranked = rank_domains(flat, AssumptionSet(name="flat"))
    assert (ranked["rank"] == 1).all()


def test_unknown_domain_in_the_cost_multipliers_warns(domains):
    aset = AssumptionSet(name="typo", cost_multipliers={"9.9": 2.0})
    with pytest.warns(UserWarning, match="not in the data"):
        rank_domains(domains, aset)


def test_diff_reports_the_shift_in_positions(domains, bau, pm_costed):
    left = rank_domains(domains, bau)
    right = rank_domains(domains, pm_costed)
    diff = diff_rankings(left, right, left_name=bau.name, right_name=pm_costed.name)

    assert list(diff.columns) == ["short_name", "rank_bau", "rank_pm", "shift"]
    assert diff.loc["7.1", "shift"] == 1  # moved up one position under the pm reading
    assert diff.loc["4.2", "shift"] == -1
    assert diff.loc["7.2", "shift"] == 0
    # largest movement first
    assert diff["shift"].abs().is_monotonic_decreasing


def test_diff_needs_a_shared_domain(domains, bau):
    ranked = rank_domains(domains, bau)
    other = ranked.rename(index=lambda code: f"z{code}")
    with pytest.raises(ValueError, match="share no domain"):
        diff_rankings(ranked, other)


def test_pair_order_agreement_is_one_against_itself(domains, bau):
    ranked = rank_domains(domains, bau)
    assert pair_order_agreement(ranked, ranked) == 1.0


def test_pair_order_agreement_counts_swapped_pairs(domains, bau, pm_costed):
    left = rank_domains(domains, bau)
    right = rank_domains(domains, pm_costed)
    # one swapped pair out of the ten pairs among five domains
    assert pair_order_agreement(left, right) == pytest.approx(0.9)
