from pathlib import Path

import pytest

from riskdlab.assumptions import AssumptionSet

REPO_ROOT = Path(__file__).resolve().parent.parent
ASSUMPTION_SETS = sorted((REPO_ROOT / "assumption_sets").glob("*.yaml"))


def test_defaults_are_a_valid_set():
    aset = AssumptionSet(name="plain")
    assert aset.objective == "catastrophic_probability"
    assert aset.cost_for("6.4") == 1.0


def test_cost_multipliers_override_the_default():
    aset = AssumptionSet(name="costed", cost_multipliers={"6.4": 5}, default_cost_multiplier=2)
    assert aset.cost_for("6.4") == 5.0
    assert aset.cost_for("7.2") == 2.0


@pytest.mark.parametrize(
    "kwargs, message",
    [
        ({"name": ""}, "needs a name"),
        ({"name": "x", "objective": "vibes"}, "unknown objective"),
        ({"name": "x", "scenario": "later"}, "unknown scenario"),
        ({"name": "x", "objective": "achievable_reduction"}, "has to be a mitigated one"),
        ({"name": "x", "cost_multipliers": {"6.4": 0}}, "must be > 0"),
        ({"name": "x", "default_cost_multiplier": -1}, "must be > 0"),
    ],
)
def test_invalid_sets_are_rejected(kwargs, message):
    with pytest.raises(ValueError, match=message):
        AssumptionSet(**kwargs)


def test_from_dict_rejects_unknown_keys():
    with pytest.raises(ValueError, match="unknown keys"):
        AssumptionSet.from_dict({"name": "x", "weighting": "utilitarian"})


@pytest.mark.parametrize("suffix", [".yaml", ".json"])
def test_round_trips_through_a_file(tmp_path, suffix):
    aset = AssumptionSet(
        name="round-trip",
        description="…",
        decision_question="where does effort buy the most?",
        objective="achievable_reduction",
        scenario="pm",
        cost_multipliers={"6.4": 5.0},
    )
    loaded = AssumptionSet.load(aset.save(tmp_path / f"set{suffix}"))
    assert loaded == aset


def test_the_repository_ships_two_different_sets():
    sets = [AssumptionSet.load(path) for path in ASSUMPTION_SETS]
    assert len(sets) >= 2
    assert len({(s.objective, s.scenario) for s in sets}) >= 2


@pytest.mark.parametrize("path", ASSUMPTION_SETS, ids=lambda p: p.stem)
def test_shipped_sets_load_and_are_documented(path):
    aset = AssumptionSet.load(path)
    assert aset.name == path.stem
    assert aset.decision_question
    assert aset.description
