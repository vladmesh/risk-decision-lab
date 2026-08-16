"""Synthetic fixtures that repeat the schema of the real MIT files.

The raw data is not in git, so every test builds miniature files with the same shape:
a Delphi rds holding `meta$risks` and `severity_aggregate`, and an xlsx whose header
sits on the third row of an `AI Risk Database v4` sheet.
"""

from __future__ import annotations

import pandas as pd
import pytest

from riskdlab.data import (
    CATEGORY_LEVEL_COLUMN,
    REPOSITORY_HEADER_ROW,
    REPOSITORY_SHEET,
    SUBDOMAIN_COLUMN,
)

# 5 of the 24 domains, with numbers taken from the real snapshot so the fixtures stay
# recognisable; the ranking logic does not care about the values.
DOMAINS = [
    # risk_number, code, short name, P(catastrophic) bau, pm
    (1, "4.2", "Weapons & cyberattacks", 21.00, 11.90),
    (2, "6.4", "Competitive dynamics", 16.61, 7.30),
    (3, "6.5", "Governance failure", 14.42, 7.26),
    (4, "7.1", "AI misalignment", 16.62, 8.86),
    (5, "7.2", "Dangerous capabilities", 21.51, 12.30),
]


@pytest.fixture
def risks_frame() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "risk_number": [row[0] for row in DOMAINS],
            "taxonomy_id": [row[1] for row in DOMAINS],
            "short_name": [row[2] for row in DOMAINS],
        }
    )


@pytest.fixture
def severity_frame() -> pd.DataFrame:
    """24 domains x 2 scenarios x 5 harm levels in the real file; here 5 x 2 x 2."""
    rows = []
    for risk_number, _code, _name, bau, pm in DOMAINS:
        for scenario, pct in (("bau", bau), ("pm", pm)):
            for level, value in (("catastrophic", pct), ("major", 100.0 - pct)):
                rows.append(
                    {
                        "risk_number": risk_number,
                        "scenario": scenario,
                        "level": level,
                        "pct": value,
                        "pct_ci_lower": value - 3.5,
                        "pct_ci_upper": value + 3.7,
                    }
                )
    return pd.DataFrame(rows)


@pytest.fixture
def delphi_path(tmp_path, risks_frame, severity_frame):
    import rdata

    path = tmp_path / "delphi_snapshot.rds"
    rdata.write_rds(
        path,
        {
            "meta": {"risks": risks_frame, "round": 3},
            "severity_aggregate": severity_frame,
        },
    )
    return path


@pytest.fixture
def repository_frame() -> pd.DataFrame:
    """Rows of all four category levels, including the two that are not risks."""
    rows = [
        ("Paper", None),
        ("Additional evidence", "4.2 > Weapons & cyberattacks"),
        ("Risk Category", "4.2 > Weapons & cyberattacks"),
        ("Risk Subcategory", "4.2 > Weapons & cyberattacks"),
        ("Risk Subcategory", "4.2 > Weapons & cyberattacks"),
        ("Risk Subcategory", "6.4 > Competitive dynamics"),
        ("Risk Subcategory", "7.2 > Dangerous capabilities"),
        ("Risk Subcategory", "X.0 > Other"),
    ]
    return pd.DataFrame(
        {
            "Title": [f"Paper {i}" for i in range(len(rows))],
            "Paper_ID": list(range(len(rows))),
            CATEGORY_LEVEL_COLUMN: [level for level, _ in rows],
            "Description": ["…"] * len(rows),
            SUBDOMAIN_COLUMN: [subdomain for _, subdomain in rows],
        }
    )


@pytest.fixture
def repository_path(tmp_path, repository_frame):
    path = tmp_path / "ai-risk-repository.xlsx"
    with pd.ExcelWriter(path) as writer:
        repository_frame.to_excel(
            writer,
            sheet_name=REPOSITORY_SHEET,
            index=False,
            startrow=REPOSITORY_HEADER_ROW,
        )
        # the real sheet has two banner rows above the header; leave them blank here
    return path
