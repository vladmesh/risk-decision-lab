from pathlib import Path

import pytest

from riskdlab.assumptions import AssumptionSet
from riskdlab.cli import distinct_labels, effective_level, main

REPO_ROOT = Path(__file__).resolve().parent.parent
SETS = REPO_ROOT / "assumption_sets"
BAU = SETS / "bau-minimize-catastrophe.yaml"
PM = SETS / "pm-maximize-reduction.yaml"
PM_RANGES = SETS / "pm-cost-uncertainty.yaml"


def data_args(delphi_path, repository_path):
    return ["--delphi", str(delphi_path), "--repository", str(repository_path)]


def test_rank_prints_the_assumptions_and_the_table(delphi_path, repository_path, capsys):
    code = main([*data_args(delphi_path, repository_path), "rank", str(BAU)])
    out = capsys.readouterr().out

    assert code == 0
    assert "# bau-minimize-catastrophe" in out
    assert "objective: catastrophic_probability | scenario: bau" in out
    assert "median 95% CI width 7.2 pp" in out
    assert "Dangerous capabilities" in out
    assert "n_risk_rows" in out


def test_rank_can_run_without_the_repository(delphi_path, repository_path, capsys):
    code = main(
        [*data_args(delphi_path, repository_path), "--no-repository", "rank", str(PM)]
    )
    out = capsys.readouterr().out
    assert code == 0
    assert "n_risk_rows" not in out


def test_top_limits_the_table(delphi_path, repository_path, capsys):
    main([*data_args(delphi_path, repository_path), "--top", "2", "rank", str(BAU)])
    out = capsys.readouterr().out
    assert "Governance failure" not in out


def test_compare_prints_both_rankings_and_the_diff(delphi_path, repository_path, capsys):
    code = main([*data_args(delphi_path, repository_path), "compare", str(BAU), str(PM)])
    out = capsys.readouterr().out

    assert code == 0
    assert "# bau-minimize-catastrophe" in out
    assert "# pm-maximize-reduction" in out
    assert "# diff" in out
    assert "rank_bau-minimize-catastrophe" in out
    assert "rank_pm-maximize-reduction" in out
    assert "domains that changed rank: 2/5" in out
    assert "pairs keeping their order: 90.0%" in out


def test_missing_raw_data_is_an_error_not_a_traceback(tmp_path, capsys):
    code = main(["--delphi", str(tmp_path / "absent.rds"), "rank", str(BAU)])
    out = capsys.readouterr().out
    assert code == 2
    assert "README.md" in out


@pytest.mark.parametrize("argv", [["rank"], []])
def test_bad_invocations_exit_with_usage(argv):
    with pytest.raises(SystemExit) as exc:
        main(argv)
    assert exc.value.code == 2


def test_effective_level_prefers_the_set_and_yields_to_the_flag():
    aset = AssumptionSet(name="x", level="severe")
    assert effective_level(aset, None) == "severe"
    assert effective_level(aset, "catastrophic") == "catastrophic"


def test_distinct_labels_only_disambiguate_on_collision():
    assert distinct_labels("a", "b") == ("a", "b")
    assert distinct_labels("a", "a") == ("a#1", "a#2")


def _write_set(path: Path, **kwargs) -> Path:
    return AssumptionSet(**kwargs).save(path)


def test_rank_uses_the_harm_level_stated_in_the_assumption_set(
    tmp_path, delphi_path, repository_path, capsys
):
    aset = _write_set(tmp_path / "major.yaml", name="major-set", level="major")
    main([*data_args(delphi_path, repository_path), "rank", str(aset)])
    out = capsys.readouterr().out

    assert "harm level: major" in out
    # under `major` the fixture reverses the order: 6.5 is worst, 7.2 is best
    body = out.splitlines()
    first_row = [line for line in body if line.strip().startswith("6.5")][0]
    assert first_row.split()[1] == "1"
    assert "85.58" in first_row


def test_level_flag_overrides_the_set_and_says_so(
    tmp_path, delphi_path, repository_path, capsys
):
    aset = _write_set(tmp_path / "major.yaml", name="major-set", level="major")
    main([*data_args(delphi_path, repository_path), "--level", "catastrophic",
          "rank", str(aset)])
    out = capsys.readouterr().out

    assert "harm level: catastrophic (--level, set says major)" in out
    assert "21.51" in out  # the catastrophic values, not the major ones


def test_compare_diffs_the_two_files_even_when_the_names_collide(
    tmp_path, delphi_path, repository_path, capsys
):
    left = _write_set(tmp_path / "left.yaml", name="same", objective="catastrophic_probability")
    right = _write_set(
        tmp_path / "right.yaml",
        name="same",
        objective="achievable_reduction",
        scenario="pm",
        cost_multipliers={"6.4": 5.0, "6.5": 4.0, "4.2": 3.0, "7.1": 2.0, "7.2": 1.5},
    )
    main([*data_args(delphi_path, repository_path), "compare", str(left), str(right)])
    out = capsys.readouterr().out

    assert "rank_same#1" in out and "rank_same#2" in out
    assert "domains that changed rank: 2/5" in out
    assert "pairs keeping their order: 90.0%" in out


def test_compare_ranks_each_set_on_its_own_level(
    tmp_path, delphi_path, repository_path, capsys
):
    left = _write_set(tmp_path / "left.yaml", name="on-catastrophic", level="catastrophic")
    right = _write_set(tmp_path / "right.yaml", name="on-major", level="major")
    main([*data_args(delphi_path, repository_path), "compare", str(left), str(right)])
    out = capsys.readouterr().out

    assert "harm level: catastrophic" in out
    assert "harm level: major" in out
    # the two levels are mirror images in the fixture, so every pair flips
    assert "pairs keeping their order: 0.0%" in out


def test_stability_reports_sampled_rank_ranges(delphi_path, repository_path, capsys):
    code = main([
        *data_args(delphi_path, repository_path),
        "stability", str(PM_RANGES), "--samples", "100", "--seed", "7",
    ])
    out = capsys.readouterr().out

    assert code == 0
    assert "cost stability: 100 samples | seed 7" in out
    assert "not a calibrated real-world probability" in out
    assert "best_rank" in out and "worst_rank" in out and "top_3_share" in out
    assert "Dangerous capabilities" in out


def test_mitigations_needs_no_arguments_and_shows_both_breakdowns(capsys):
    code = main(["mitigations"])
    out = capsys.readouterr().out

    assert code == 0
    assert "831 mitigations" in out
    assert "13 source documents" in out
    assert "## by category and subcategory" in out
    assert "## by source document" in out
    assert "3.1" in out and "Testing & Auditing" in out
    assert "NIST2024" in out
    # the catch-alls are shown, not hidden
    assert "X.X" in out
    assert "no risk linkage and no effectiveness or cost estimate" in out


def test_mitigations_filters_by_subcategory_and_prints_its_description(capsys):
    code = main(["mitigations", "--subcategory", "3.2"])
    out = capsys.readouterr().out

    assert code == 0
    assert "filter: subcategory 3.2 — 57 of 831 mitigations" in out
    assert "3.2 Data Governance (category 3 Operational Process Controls)" in out
    assert "examples:" in out
    assert "Testing & Auditing" not in out


def test_mitigations_filters_by_source(capsys):
    code = main(["mitigations", "--source", "Wiener2024"])
    out = capsys.readouterr().out

    assert code == 0
    assert "filter: source Wiener2024 — 10 of 831 mitigations" in out
    assert "NIST2024" not in out.split("## by source document")[1]


def test_mitigations_keeps_the_uncategorised_bucket_reachable(capsys):
    code = main(["mitigations", "--subcategory", "X.X", "--list", "--limit", "3"])
    out = capsys.readouterr().out

    assert code == 0
    assert "filter: subcategory X.X — 11 of 831 mitigations" in out
    assert "not in the published taxonomy" in out
    assert "... 8 more" in out


def test_mitigations_says_so_when_a_filter_matches_nothing(capsys):
    code = main(["mitigations", "--source", "NoSuchRef2026"])
    out = capsys.readouterr().out

    assert code == 1
    assert "no mitigation matches this filter" in out
    assert "NIST2024" in out
