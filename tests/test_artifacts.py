"""Regression checks for the committed result files and their public reading."""

from __future__ import annotations

import json
from pathlib import Path
import re

import pandas as pd
import pytest


ROOT = Path(__file__).resolve().parent.parent


def test_saved_csv_json_and_public_copy_agree_on_totals():
    payload = json.loads(
        (ROOT / "results/gapmap-2024-2026-catastrophic.json").read_text(encoding="utf-8")
    )
    table = pd.read_csv(ROOT / "results/gapmap-2024-2026-catastrophic.csv")
    reviewed = table["fund_usd"].sum()
    ai_risk = table.loc[table["label"] != "not_ai", "fund_usd"].sum()

    assert payload["attrs"]["usd_total"] == pytest.approx(reviewed)
    assert payload["attrs"]["usd_total_ai"] == pytest.approx(ai_risk)
    assert sum(payload["attrs"]["amount_kind_usd"].values()) == pytest.approx(reviewed)

    page = (ROOT / "docs/index.html").read_text(encoding="utf-8")
    saved_page = (ROOT / "results/gapmap-2024-2026-page.html").read_text(encoding="utf-8")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    assert page == saved_page, "the GitHub Pages copy must match the saved result"

    reviewed_label = f"${reviewed / 1e6:.0f}M reviewed"
    ai_label = f"${ai_risk / 1e6:.0f}M"
    not_ai_label = f"${(reviewed - ai_risk) / 1e6:.0f}M labelled `not_ai`"
    assert reviewed_label in page
    assert ai_label in page and ai_label in readme
    assert not_ai_label in readme
    assert "$776M" not in page and "$776M" not in readme


def test_page_payload_matches_all_three_saved_readings():
    page = (ROOT / "docs/index.html").read_text(encoding="utf-8")
    match = re.search(
        r'<script id="data" type="application/json">(.*?)</script>', page, re.DOTALL
    )
    assert match is not None
    payload = json.loads(match.group(1))
    page_rows = {row["label"]: row for row in payload["rows"]}

    variants = {
        "": pd.read_csv(
            ROOT / "results/gapmap-2024-2026-catastrophic.csv", dtype={"label": str}
        ).set_index("label"),
        "_low": pd.read_csv(
            ROOT / "results/gapmap-2024-2026-catastrophic-allsplits.csv",
            dtype={"label": str},
        ).set_index("label"),
        "_nosplit": pd.read_csv(
            ROOT / "results/gapmap-2024-2026-catastrophic-nosplits.csv",
            dtype={"label": str},
        ).set_index("label"),
    }
    for label, page_row in page_rows.items():
        for suffix, table in variants.items():
            assert page_row[f"usd{suffix}"] == pytest.approx(
                round(table.loc[label, "fund_usd"] / 1e6, 1)
            )
            expected_share = table.loc[label, "fund_share"]
            if pd.isna(expected_share):
                assert page_row[f"share{suffix}"] is None
            else:
                assert page_row[f"share{suffix}"] == pytest.approx(
                    round(expected_share * 100, 1)
                )

    methods = pd.read_csv(
        ROOT / "results/risk-by-method-2024-2026.csv", index_col=0
    ).sum(axis=0)
    for method, amount_millions in payload["methods"].items():
        assert amount_millions == pytest.approx(round(methods[method] / 1e6, 1))
