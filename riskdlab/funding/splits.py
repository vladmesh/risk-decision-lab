"""Programme-level allocation assumptions for grants whose headline label is too broad.

The source rows describe an organisation's programme mix rather than observed spending
on any individual grant. Applying them preserves each grant's total while making that
assumption explicit in the long funding table.
"""

from __future__ import annotations

import re
from pathlib import Path

import pandas as pd

from riskdlab.funding.grants import SNAPSHOT_DIR
from riskdlab.funding.labels import LABELS, METHODS

DEFAULT_SPLITS_PATH = SNAPSHOT_DIR / "programme-splits-2026-08-20.csv"

SPLIT_COLUMNS = [
    "grantee",
    "dimension",
    "label",
    "share",
    "source_url",
    "source_year",
    "basis",
    "confidence",
    "note",
]


def read_splits(path: Path | str = DEFAULT_SPLITS_PATH) -> pd.DataFrame:
    """Read allocation assumptions only when they form complete distributions."""
    frame = pd.read_csv(path, dtype=str, keep_default_na=False)
    missing = [column for column in SPLIT_COLUMNS if column not in frame.columns]
    if missing:
        raise ValueError(f"{path}: missing column(s) {missing}")
    frame = frame[SPLIT_COLUMNS].copy()

    if (frame["grantee"].str.strip() == "").any():
        raise ValueError(f"{path}: grantee must be non-empty")

    bad_dimensions = sorted(set(frame["dimension"]) - {"risk", "method"})
    if bad_dimensions:
        raise ValueError(f"{path}: unknown dimension(s) {bad_dimensions}")

    empty_label = frame["label"].str.strip() == ""
    empty_share = frame["share"].str.strip() == ""
    if (empty_label != empty_share).any():
        raise ValueError(f"{path}: label and share must either both be present or both be empty")
    frame = frame[~empty_label].copy()

    known = {"risk": set(LABELS), "method": set(METHODS)}
    bad_labels = sorted(
        {(dimension, label) for dimension, label in frame[["dimension", "label"]].itertuples(index=False, name=None)
         if label not in known[dimension]}
    )
    if bad_labels:
        raise ValueError(f"{path}: unknown label(s) {bad_labels}")

    numeric = pd.to_numeric(frame["share"], errors="coerce")
    if numeric.isna().any() or ((numeric <= 0) | (numeric > 1)).any():
        raise ValueError(f"{path}: shares must be numbers in (0, 1]")
    frame["share"] = numeric.astype(float)

    totals = frame.groupby(["grantee", "dimension"])["share"].sum()
    bad_totals = totals[~totals.sub(1.0).abs().le(0.0100000001)]
    if not bad_totals.empty:
        detail = {key: float(value) for key, value in bad_totals.items()}
        raise ValueError(f"{path}: shares must sum to 1 within 0.01; got {detail}")
    return frame


#: Titles that say the grant funds the organisation rather than a named project.
_GENERAL_SUPPORT_RE = re.compile(
    r"general (?:operating )?support|operating (?:costs|expenses|support)|core (?:support|funding)"
    r"|unrestricted|general funding|^\s*$",
    re.I,
)


def split_eligible(frame: pd.DataFrame) -> pd.Series:
    """Which grants a programme split may touch.

    A split describes the organisation's mix, so it applies to money given to the
    organisation as such: general support, operating costs, or a grant the labeller could
    only file as `field`. A grant with a project title of its own ("AI evals benchmark")
    already says what it is for and keeps its own label.
    """
    title = frame["title"] if "title" in frame.columns else pd.Series("", index=frame.index)
    general = title.fillna("").astype(str).str.contains(_GENERAL_SUPPORT_RE)
    return general | frame["risk"].isin(("field", "cross"))


CONFIDENCE_ORDER = ("low", "medium", "high")


def gate_splits(splits: pd.DataFrame, min_confidence: str = "medium") -> pd.DataFrame:
    """Keep only organisation×dimension blocks whose every share meets `min_confidence`.

    A block is all-or-nothing: dropping one row of a distribution would leave shares that
    no longer sum to one. "low" keeps everything; "high" keeps only measured splits.
    """
    if min_confidence not in CONFIDENCE_ORDER:
        raise ValueError(f"min_confidence must be one of {CONFIDENCE_ORDER}")
    floor = CONFIDENCE_ORDER.index(min_confidence)
    rank = splits["confidence"].map(lambda c: CONFIDENCE_ORDER.index(c) if c in CONFIDENCE_ORDER else -1)
    passes = rank.groupby([splits["grantee"], splits["dimension"]]).transform("min") >= floor
    return splits[passes].copy()


def _apply_risk_splits(frame: pd.DataFrame, splits: pd.DataFrame) -> pd.DataFrame:
    risk = splits[splits["dimension"] == "risk"][
        ["grantee", "label", "share", "confidence"]
    ].rename(
        columns={"label": "split_risk", "share": "risk_weight", "confidence": "split_confidence"}
    )
    eligible = split_eligible(frame)
    out = frame[eligible].merge(risk, on="grantee", how="left")
    matched = out["split_risk"].notna()
    out["risk"] = out["split_risk"].fillna(out["risk"])
    out["risk_weight"] = out["risk_weight"].fillna(1.0)
    split_confidence = out["split_confidence"].replace("", pd.NA)
    out.loc[matched, "confidence"] = split_confidence[matched].fillna(out.loc[matched, "confidence"])
    out = out.drop(columns=["split_risk", "split_confidence"])
    rest = frame[~eligible].copy()
    rest["risk_weight"] = 1.0
    return pd.concat([out, rest], ignore_index=True)


def apply_splits(
    grants: pd.DataFrame,
    labels: pd.DataFrame,
    methods: pd.DataFrame,
    splits: pd.DataFrame,
) -> pd.DataFrame:
    """Expand grants across programme risk and method shares without changing totals."""
    frame = grants.merge(
        labels[["grant_id", "primary", "confidence"]].rename(columns={"primary": "risk"}),
        on="grant_id",
        how="inner",
    ).merge(methods[["grant_id", "method"]], on="grant_id", how="inner")
    eligible_ids = set(frame.loc[split_eligible(frame), "grant_id"])
    frame = _apply_risk_splits(frame, splits)

    method = splits[splits["dimension"] == "method"][["grantee", "label", "share"]].rename(
        columns={"label": "split_method", "share": "method_weight"}
    )
    # eligibility was decided on the original label, before the risk split changed it
    eligible_rows = frame["grant_id"].isin(eligible_ids)
    expanded = frame[eligible_rows].merge(method, on="grantee", how="left")
    rest = frame[~eligible_rows].copy()
    rest["split_method"] = pd.NA
    rest["method_weight"] = 1.0
    frame = pd.concat([expanded, rest], ignore_index=True)
    frame["method"] = frame["split_method"].fillna(frame["method"])
    frame["method_weight"] = frame["method_weight"].fillna(1.0)
    frame["weight"] = frame["risk_weight"] * frame["method_weight"]
    frame["amount_share_usd"] = frame["amount_usd"] * frame["weight"]
    columns = [
        "grant_id", "source", "year", "amount_usd", "amount_share_usd",
        "weight", "risk", "method", "confidence",
    ]
    return frame[columns]
