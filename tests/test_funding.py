"""Funding snapshots: the SFF page parser, the unified grants table, the labels."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from riskdlab.funding.grants import COLUMNS, load_grants, read_coefficient, read_eafunds, read_manifund, read_sff
from riskdlab.funding.labels import LABELS, agreement, read_labels
from riskdlab.funding.splits import apply_splits, read_splits
from riskdlab.funding.fli import parse_program
from riskdlab.funding.sff import parse_round, parse_rounds

FLI_PAGE = """
<h1>Some programme</h1><p>In 2024, FLI called for proposals.</p>
<div class="ct-div-block oxel_accordion width--full"><div>Project title</div><h4><span>AI Impacts</span></h4>
<div>Amount recommended</div><div>$162,000.00</div><div>Details</div><div>Project Summary</div><p>General support. AI Impacts performs research related to the future of AI.</p></div>
<div class="ct-div-block oxel_accordion width--full"><div>Project title</div><h4><span>Another Org</span></h4>
<div>Amount recommended</div><div>$1,000.00</div><div>Project Summary</div><p>Something else.</p></div>
"""

TABLE_PAGE = """
<html><body><table>
<tr><th>Source</th><th>Organization</th><th>Amount</th><th>Receiving Charity</th><th>Purpose</th></tr>
<tr><td>SFF</td><td>AI Impacts</td><td>$70,000</td><td>MIRI</td><td>General Support of AI Impacts</td></tr>
<tr><td>SFF</td><td>ALLFED</td><td>$10,000</td><td>SEE</td><td>General Support of ALLFED</td></tr>
</table></body></html>
"""

GRID_PAGE = """
<div class="grid">
<div class="in-grid is-header"><div>Source</div></div>
<div class="in-grid is-header"><div>Organization</div></div>
<div class="in-grid is-header"><div>Track Rec.</div></div>
<div class="in-grid is-header"><div>Total Funding Rec.</div></div>
<div class="in-grid is-header"><div>Receiving Charity</div></div>
<div class="in-grid is-header"><div>Purpose</div></div>
<div class="in-grid"><div>Jaan Tallinn</div></div>
<div class="in-grid"><div>AI Futures Project</div></div>
<div class="in-grid"><div><span> Main: $1,530,000<br> Freedom: $361,000</span></div></div>
<div class="in-grid"><div>$2,035,000<br><span> Speculation: ($95,000)&dagger;<br> Matching: {$500,000}&Dagger;</span></div></div>
<div class="in-grid"><div>AI Futures Project</div></div>
<div class="in-grid"><div>General support</div></div>
<div class="in-grid is-header"><div>Source</div></div>
<div class="in-grid is-header"><div>Organization</div></div>
<div class="in-grid is-header"><div>Matching Pledge Amount</div></div>
<div class="in-grid is-header"><div>Matching Rate</div></div>
<div class="in-grid"><div>Jaan Tallinn</div></div>
<div class="in-grid"><div>AI Futures Project</div></div>
<div class="in-grid"><div>$500,000</div></div>
<div class="in-grid"><div>1x</div></div>
</div>
"""

FUNDER_COLUMNS_PAGE = """
<table>
<tr><th>Organization</th><th>Amount (Jaan Tallinn via LSG)</th><th>Amount (FLI)</th><th>Receiving Charity</th><th>Purpose</th></tr>
<tr><td>Legal Priorities Project</td><td>$302,900 ($199,900)&Dagger;</td><td>$0</td><td>Legal Priorities, Inc.</td><td>General Support</td></tr>
</table>
"""


def test_sff_table_page_parses_rows_and_amounts():
    frame = parse_round(TABLE_PAGE, "2019")
    assert frame["organization"].tolist() == ["AI Impacts", "ALLFED"]
    assert frame["amount_usd"].tolist() == [70000.0, 10000.0]
    assert frame["purpose"].iloc[0] == "General Support of AI Impacts"
    assert frame["year"].iloc[0] == 2019


def test_sff_grid_page_takes_the_total_and_skips_the_pledge_schedule():
    frame = parse_round(GRID_PAGE, "2025")
    assert len(frame) == 1, "the matching-pledge grid has no Purpose column and must not add rows"
    row = frame.iloc[0]
    assert row["amount_usd"] == 2035000.0, "footnote figures in parentheses/braces are not the amount"
    assert "Speculation" in row["note"]


def test_sff_funder_columns_are_summed_when_there_is_no_total():
    frame = parse_round(FUNDER_COLUMNS_PAGE, "2023/h2")
    assert frame["amount_usd"].iloc[0] == 302900.0, "the bracketed figure is a footnote, not an amount"
    assert frame["year"].iloc[0] == 2023


def test_sff_page_without_header_is_an_error():
    with pytest.raises(ValueError):
        parse_round("<table><tr><td>no header</td></tr></table>", "2019")


def test_fli_program_page_parses_grantee_amount_summary_and_year():
    frame = parse_program(FLI_PAGE, "some-programme")
    assert frame["grantee"].tolist() == ["AI Impacts", "Another Org"]
    assert frame["amount_usd"].tolist() == [162000.0, 1000.0]
    assert frame["summary"].iloc[0].startswith("General support. AI Impacts")
    assert frame["year"].iloc[0] == 2024 and frame["year_basis"].iloc[0] == "intro"
    slug_year = parse_program(FLI_PAGE, "2023-grants")
    assert slug_year["year"].iloc[0] == 2023 and slug_year["year_basis"].iloc[0] == "slug"


def test_parse_rounds_concatenates():
    frame = parse_rounds({"2019": TABLE_PAGE, "2025": GRID_PAGE})
    assert sorted(frame["round"].unique()) == ["2019", "2025"]


@pytest.fixture
def snapshot_files(tmp_path):
    coefficient = tmp_path / "coefficient.csv"
    pd.DataFrame(
        {
            "grant_id": ["grants-1-0", "grants-2-0"],
            "post_id": ["1", "2"],
            "award_date": ["2025-01-01", "2024-06-01"],
            "award_year": ["2025", "2024"],
            "organization": ["Redwood Research", "Some Bio Lab"],
            "title": ["General Support", "Vaccine Work"],
            "amount_usd": ["1000000", "500000"],
            "focus_areas": ["Navigating Transformative AI", "Biosecurity & Pandemic Preparedness"],
            "funding_type": ["Grants", "Grants"],
            "url": ["", ""],
        }
    ).to_csv(coefficient, index=False)
    eafunds = tmp_path / "eafunds.csv"
    pd.DataFrame(
        {
            "id": ["recA", "recB"],
            "fund": ["Long-Term Future Fund", "Animal Welfare Fund"],
            "description": ["MATS extension on interpretability", "cage-free campaign"],
            "grantee": ["A Person", "An Org"],
            "amount": ["20000", "30000"],
            "round": ["2025 Q1", "2025 Q1"],
            "year": ["2025", "2025"],
            "highlighted": ["", ""],
        }
    ).to_csv(eafunds, index=False)
    manifund = tmp_path / "manifund.csv"
    pd.DataFrame(
        {
            "project_id": ["p1", "p2"],
            "slug": ["one", "two"],
            "title": ["Shutdown evals", "A poultry project"],
            "created_at": ["2026-03-01T00:00:00Z", "2026-02-01T00:00:00Z"],
            "stage": ["active", "proposal"],
            "type": ["grant", "grant"],
            "creator": ["alice", "bob"],
            "causes": ["tais", "animal-welfare"],
            "funding_goal_usd": ["10000", "5000"],
            "min_funding_usd": ["1000", "1000"],
            "raised_usd": ["7500", "0"],
            "n_txns": ["3", "0"],
            "blurb": ["why agents resist shutdown", ""],
            "description": ["long text", "long text"],
        }
    ).to_csv(manifund, index=False)
    sff = tmp_path / "sff.csv"
    pd.DataFrame(
        {
            "round": ["2025", "2025"],
            "source": ["Jaan Tallinn", "Jaan Tallinn"],
            "organization": ["MIRI", "SecureDNA"],
            "amount_usd": ["1000000", "1500000"],
            "receiving_charity": ["MIRI", "SecureBio"],
            "purpose": ["General support", "General support of SecureDNA"],
            "note": ["", ""],
            "year": ["2025", "2025"],
        }
    ).to_csv(sff, index=False)
    return {"coefficient_path": coefficient, "eafunds_path": eafunds, "manifund_path": manifund, "sff_path": sff, "fli_path": None}


def test_each_reader_returns_the_common_columns(snapshot_files):
    for reader, key in (
        (read_coefficient, "coefficient_path"),
        (read_eafunds, "eafunds_path"),
        (read_manifund, "manifund_path"),
        (read_sff, "sff_path"),
    ):
        frame = reader(snapshot_files[key])
        assert list(frame.columns) == COLUMNS
        assert len(frame) == 2


def test_ai_scope_is_the_funders_own_tagging(snapshot_files):
    grants = load_grants(**snapshot_files)
    scope = grants.set_index("grant_id")["ai_scope"]
    assert scope["grants-1-0"] and not scope["grants-2-0"], "Coefficient: by focus area"
    assert scope["recA"] and not scope["recB"], "EA Funds: LTFF only"
    assert scope["p1"] and not scope["p2"], "Manifund: tais/ai-gov tags"
    assert scope["2025/0"] and scope["2025/1"], "SFF has no tag; every row is in scope"


def test_text_carries_the_grantee_where_the_title_is_thin(snapshot_files):
    grants = load_grants(**snapshot_files).set_index("grant_id")
    assert grants.loc["grants-1-0", "text"] == "Redwood Research — General Support"
    assert grants.loc["2025/0", "text"] == "MIRI — General support"


def test_manifund_amount_is_raised_money(snapshot_files):
    grants = load_grants(**snapshot_files).set_index("grant_id")
    assert grants.loc["p1", "amount_usd"] == 7500.0
    assert grants.loc["p1", "amount_kind"] == "raised"
    assert grants.loc["p2", "amount_usd"] == 0.0


def test_labels_are_validated(tmp_path):
    path = tmp_path / "labels.csv"
    pd.DataFrame(
        {"grant_id": ["a", "b"], "primary": ["7.1", "field"], "secondary": ["", "6.5"],
         "confidence": ["high", "low"], "basis": ["x", "y"]}
    ).to_csv(path, index=False)
    labels = read_labels(path)
    assert len(labels) == 2
    assert set(labels["primary"]) <= set(LABELS)

    bad = tmp_path / "bad.csv"
    pd.DataFrame(
        {"grant_id": ["a"], "primary": ["8.1"], "secondary": [""], "confidence": ["high"], "basis": [""]}
    ).to_csv(bad, index=False)
    with pytest.raises(ValueError, match="unknown primary"):
        read_labels(bad)


def test_agreement_counts_exact_domain_and_either():
    labels = pd.DataFrame(
        {"grant_id": ["a", "b", "c", "d"], "primary": ["7.1", "7.2", "6.5", "field"],
         "secondary": ["", "", "", ""], "confidence": ["high"] * 4, "basis": [""] * 4}
    )
    control = pd.DataFrame(
        {"grant_id": ["a", "b", "c", "d"], "primary": ["7.1", "7.4", "6.4", "7.1"],
         "secondary": ["", "7.2", "", ""], "confidence": ["high"] * 4, "basis": [""] * 4}
    )
    score = agreement(labels, control)
    assert score["n"] == 4
    assert score["exact"] == pytest.approx(0.25)
    assert score["domain"] == pytest.approx(0.75)
    assert score["either"] == pytest.approx(0.5)


def test_methods_are_validated_and_crossed_with_risk(tmp_path):
    from riskdlab.funding.labels import read_methods, risk_by_method

    path = tmp_path / "methods.csv"
    pd.DataFrame(
        {"grant_id": ["a", "b", "c"], "method": ["X.research-interp", "3.1", "X.talent-community"],
         "confidence": ["high", "high", "medium"], "basis": ["", "", ""]}
    ).to_csv(path, index=False)
    methods = read_methods(path)
    assert len(methods) == 3

    bad = tmp_path / "bad.csv"
    pd.DataFrame({"grant_id": ["a"], "method": ["5.9"], "confidence": ["high"], "basis": [""]}).to_csv(bad, index=False)
    with pytest.raises(ValueError, match="unknown method"):
        read_methods(bad)

    grants = pd.DataFrame(
        {"grant_id": ["a", "b", "c"], "year": pd.array([2025, 2025, 2023], dtype="Int64"),
         "amount_usd": [100.0, 50.0, 25.0], "source": ["x"] * 3}
    )
    labels = pd.DataFrame(
        {"grant_id": ["a", "b", "c"], "primary": ["7.4", "7.2", "field"], "secondary": [""] * 3,
         "confidence": ["high"] * 3, "basis": [""] * 3}
    )
    table = risk_by_method(grants, labels, methods, year_from=2024)
    assert table.loc["7.4", "X.research-interp"] == 100.0
    assert table.loc["7.2", "3.1"] == 50.0
    assert "field" not in table.index, "the 2023 grant is outside the window"
    assert table.attrs["usd_total"] == 150.0


def test_programme_splits_are_validated(tmp_path):
    path = Path(__file__).parent / "fixtures" / "programme-splits.csv"
    splits = read_splits(path)
    assert len(splits) == 4, "the no-public-split marker is not an allocation"
    assert splits.groupby(["grantee", "dimension"])["share"].sum().eq(1.0).all()

    bad = pd.read_csv(path, dtype=str, keep_default_na=False)
    bad.loc[(bad["dimension"] == "risk") & (bad["label"] == "6.5"), "share"] = "0.2"
    bad_path = tmp_path / "bad-sum.csv"
    bad.to_csv(bad_path, index=False)
    with pytest.raises(ValueError, match="sum to 1"):
        read_splits(bad_path)

    bad.loc[0, "label"] = "8.1"
    bad.loc[1, "share"] = "0.4"
    bad_path = tmp_path / "bad-label.csv"
    bad.to_csv(bad_path, index=False)
    with pytest.raises(ValueError, match="unknown label"):
        read_splits(bad_path)


def test_apply_splits_crosses_dimensions_and_leaves_other_grants_alone():
    grants = pd.DataFrame(
        {
            "grant_id": ["split", "plain"], "source": ["x", "x"],
            "year": pd.array([2025, 2025], dtype="Int64"),
            "grantee": ["Split Org", "Unsplit Org"], "amount_usd": [100.0, 40.0],
        }
    )
    labels = pd.DataFrame(
        {
            "grant_id": ["split", "plain"], "primary": ["field", "7.4"],
            "confidence": ["low", "high"],
        }
    )
    methods = pd.DataFrame(
        {"grant_id": ["split", "plain"], "method": ["X.none", "X.research-interp"]}
    )
    splits = read_splits(Path(__file__).parent / "fixtures" / "programme-splits.csv")
    long = apply_splits(grants, labels, methods, splits)

    allocated = long[long["grant_id"] == "split"]
    assert len(allocated) == 4
    assert allocated["amount_share_usd"].sum() == pytest.approx(100.0)
    assert set(allocated["risk"]) == {"7.1", "6.5"}
    assert set(allocated["method"]) == {"X.research-empirical", "3.1"}
    plain = long[long["grant_id"] == "plain"].iloc[0]
    assert plain["risk"] == "7.4" and plain["method"] == "X.research-interp"
    assert plain["weight"] == 1.0 and plain["amount_share_usd"] == 40.0
