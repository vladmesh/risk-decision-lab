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
RESERVED = ("field", "not_ai", "unknown")
LABELS = SUBDOMAINS + RESERVED
CONFIDENCES = ("high", "medium", "low")

LABELS_DATE = "2026-08-20"
DEFAULT_LABELS_PATH = SNAPSHOT_DIR / f"labels-mit-subdomains-{LABELS_DATE}.csv"
DEFAULT_CONTROL_PATH = SNAPSHOT_DIR / f"labels-control-{LABELS_DATE}.csv"


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
