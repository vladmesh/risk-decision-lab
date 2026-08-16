from pathlib import Path

import pytest

from riskdlab.cli import main

REPO_ROOT = Path(__file__).resolve().parent.parent
SETS = REPO_ROOT / "assumption_sets"
BAU = SETS / "bau-minimize-catastrophe.yaml"
PM = SETS / "pm-maximize-reduction.yaml"


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
