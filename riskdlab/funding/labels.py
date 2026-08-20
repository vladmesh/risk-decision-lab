"""Grant labels: one MIT subdomain (or a reserved label) per in-scope grant.

The labels are a committed snapshot, not something the package computes: they were
produced by a language model reading each grant's text against `rubric.md`, and the
snapshot records which model, when, and under which rubric version. A second,
independent labelling of a control sample is committed beside it so the agreement rate
can be reported instead of assumed. Re-labelling means writing a new snapshot file, not
editing this one.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from riskdlab.funding.grants import SNAPSHOT_DIR

SUBDOMAINS = (
    "1.1", "1.2", "1.3",
    "2.1", "2.2",
    "3.1", "3.2",
    "4.1", "4.2", "4.3",
    "5.1", "5.2",
    "6.1", "6.2", "6.3", "6.4", "6.5", "6.6",
    "7.1", "7.2", "7.3", "7.4", "7.5", "7.6",
)
#: `cross` is not a label the rubric asks for: it is derived from a `field` risk label and
#: a non-talent method label by `derive_cross`, and means "AI-safety work with no single
#: subdomain" as opposed to `field`, which after derivation means talent and community.
RESERVED = ("field", "cross", "not_ai", "unknown")
LABELS = SUBDOMAINS + RESERVED
CONFIDENCES = ("high", "medium", "low")

#: Method labels: the 23 MIT mitigation-control subcategories plus seven of our own,
#: see `rubric_methods.md`. The MIT control taxonomy has no place for research, talent
#: or advocacy, which is most of what grants pay for; the `X.*` labels are marked as ours.
MIT_CONTROLS = (
    "1.1", "1.2", "1.3", "1.4", "1.5", "1.6", "1.7",
    "2.1", "2.2", "2.3", "2.4",
    "3.1", "3.2", "3.3", "3.4", "3.5", "3.6",
    "4.1", "4.2", "4.3", "4.4", "4.5", "4.6",
)
OWN_METHODS = (
    "X.research-interp",
    "X.research-theory",
    "X.research-empirical",
    "X.forecasting",
    "X.advocacy-comms",
    "X.talent-community",
    "X.none",
)
METHODS = MIT_CONTROLS + OWN_METHODS

LABELS_DATE = "2026-08-20"
DEFAULT_LABELS_PATH = SNAPSHOT_DIR / f"labels-mit-subdomains-{LABELS_DATE}.csv"
DEFAULT_CONTROL_PATH = SNAPSHOT_DIR / f"labels-control-{LABELS_DATE}.csv"
DEFAULT_METHODS_PATH = SNAPSHOT_DIR / f"labels-methods-{LABELS_DATE}.csv"


def read_labels(path: Path | str = DEFAULT_LABELS_PATH) -> pd.DataFrame:
    """The labels table, validated: known labels and confidences, unique grant ids."""
    frame = pd.read_csv(path, dtype=str, keep_default_na=False)
    expected = ["grant_id", "primary", "secondary", "confidence", "basis"]
    missing = [c for c in expected if c not in frame.columns]
    if missing:
        raise ValueError(f"{path}: missing column(s) {missing}")
    bad = sorted(set(frame["primary"]) - set(LABELS))
    if bad:
        raise ValueError(f"{path}: unknown primary label(s) {bad}")
    bad = sorted(set(frame["secondary"]) - set(LABELS) - {""})
    if bad:
        raise ValueError(f"{path}: unknown secondary label(s) {bad}")
    bad = sorted(set(frame["confidence"]) - set(CONFIDENCES))
    if bad:
        raise ValueError(f"{path}: unknown confidence value(s) {bad}")
    duplicated = frame["grant_id"][frame["grant_id"].duplicated()].tolist()
    if duplicated:
        raise ValueError(f"{path}: duplicate grant_id {duplicated[:5]}")
    return frame[expected]


def agreement(labels: pd.DataFrame, control: pd.DataFrame) -> dict[str, float | int]:
    """How often two independent labellings agree on the control grants.

    `exact` is agreement on the primary label; `domain` on its first digit (the seven
    MIT domains, reserved labels kept as their own class); `either` counts a match when
    one labeller's primary equals the other's primary or secondary.
    """
    merged = control.merge(labels, on="grant_id", suffixes=("_a", "_b"))
    if merged.empty:
        raise ValueError("the control sample shares no grant_id with the labels")
    exact = merged["primary_a"] == merged["primary_b"]
    domain = merged["primary_a"].str[0] == merged["primary_b"].str[0]
    either = exact | (merged["primary_a"] == merged["secondary_b"]) | (merged["primary_b"] == merged["secondary_a"])
    return {
        "n": int(len(merged)),
        "exact": float(exact.mean()),
        "domain": float(domain.mean()),
        "either": float(either.mean()),
    }


def read_methods(path: Path | str = DEFAULT_METHODS_PATH) -> pd.DataFrame:
    """The method labels table, validated: known methods and confidences, unique ids."""
    frame = pd.read_csv(path, dtype=str, keep_default_na=False)
    expected = ["grant_id", "method", "confidence", "basis"]
    missing = [c for c in expected if c not in frame.columns]
    if missing:
        raise ValueError(f"{path}: missing column(s) {missing}")
    bad = sorted(set(frame["method"]) - set(METHODS))
    if bad:
        raise ValueError(f"{path}: unknown method label(s) {bad}")
    bad = sorted(set(frame["confidence"]) - set(CONFIDENCES))
    if bad:
        raise ValueError(f"{path}: unknown confidence value(s) {bad}")
    duplicated = frame["grant_id"][frame["grant_id"].duplicated()].tolist()
    if duplicated:
        raise ValueError(f"{path}: duplicate grant_id {duplicated[:5]}")
    return frame[expected]


def risk_by_method(
    grants: pd.DataFrame,
    labels: pd.DataFrame,
    methods: pd.DataFrame,
    *,
    splits: pd.DataFrame | None = None,
    year_from: int | None = None,
    year_to: int | None = None,
) -> pd.DataFrame:
    """Dollars in a risk-label × method-label table, for grants that carry both.

    This is the answer to "is subdomain X under-funded or just filed under a method":
    a row is a risk label, a column a method, a cell the dollars of funded grants that
    carry both. Reserved risk rows and `X.*` methods are kept, not dropped.
    """
    if splits is None:
        frame = grants.merge(labels[["grant_id", "primary"]], on="grant_id").merge(
            methods[["grant_id", "method"]], on="grant_id"
        ).rename(columns={"primary": "risk"})
        frame["amount_share_usd"] = frame["amount_usd"]
    else:
        from riskdlab.funding.splits import apply_splits

        frame = apply_splits(grants, labels, methods, splits)
    if year_from is not None:
        frame = frame[frame["year"] >= year_from]
    if year_to is not None:
        frame = frame[frame["year"] <= year_to]
    frame = frame[frame["amount_usd"].fillna(0) > 0]
    table = frame.pivot_table(
        index="risk", columns="method", values="amount_share_usd", aggfunc="sum", fill_value=0.0
    )
    table = table.reindex(index=[l for l in LABELS if l in table.index])
    table = table.reindex(columns=[m for m in METHODS if m in table.columns])
    table.index.name = "risk"
    table.attrs["n_grants"] = int(frame["grant_id"].nunique())
    table.attrs["usd_total"] = float(frame["amount_share_usd"].sum())
    if splits is None:
        table.attrs["split_n_grantees"] = 0
        table.attrs["split_usd"] = 0.0
    else:
        affected = grants[grants["grant_id"].isin(frame["grant_id"])]
        affected = affected[affected["grantee"].isin(set(splits["grantee"]))]
        affected = affected.drop_duplicates("grant_id")
        table.attrs["split_n_grantees"] = int(affected["grantee"].nunique())
        table.attrs["split_usd"] = float(affected["amount_usd"].sum())
    return table


def derive_cross(labels: pd.DataFrame, methods: pd.DataFrame) -> pd.DataFrame:
    """Split the `field` risk label in two, using the method label.

    The rubric files every AI-safety grant with no subdomain as `field`, which mixes two
    things: money that builds the field (talent, courses, hubs, community — method
    `X.talent-community`) and money that pays for AI-safety work whose subdomain the text
    does not say (research, policy, forecasting, advocacy under a general-support grant).
    The first stays `field`; the second becomes `cross`. Secondary labels are untouched.
    """
    merged = labels.merge(methods[["grant_id", "method"]], on="grant_id", how="left")
    is_cross = (merged["primary"] == "field") & merged["method"].notna() & (merged["method"] != "X.talent-community")
    out = labels.copy()
    out.loc[is_cross.to_numpy(), "primary"] = "cross"
    return out
