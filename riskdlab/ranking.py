"""Ranking domains under an assumption set, and diffing two rankings."""

from __future__ import annotations

import warnings

import numpy as np
import pandas as pd

from riskdlab.assumptions import AssumptionSet


def base_score(domains: pd.DataFrame, assumptions: AssumptionSet) -> pd.Series:
    """The quantity the assumption set says it cares about, before cost is applied."""
    scenario = assumptions.scenario
    if scenario not in domains.columns:
        raise ValueError(f"the domain table has no column for scenario {scenario!r}")

    if assumptions.objective == "catastrophic_probability":
        score = domains[scenario]
    else:  # achievable_reduction
        score = domains["bau"] - domains[scenario]
    return score.astype(float).rename("base_score")


def rank_domains(domains: pd.DataFrame, assumptions: AssumptionSet) -> pd.DataFrame:
    """Rank domains under one assumption set; rank 1 is the top priority.

    Score is the objective divided by the domain's assumed relative mitigation cost,
    so a domain that is twice as expensive has to buy twice as much to rank alongside.
    """
    configured = set(assumptions.cost_multipliers) | set(assumptions.cost_ranges)
    unknown = sorted(configured - set(map(str, domains.index)))
    if unknown:
        warnings.warn(
            f"{assumptions.name}: cost multipliers for domains that are not in the data: "
            f"{unknown}",
            stacklevel=2,
        )

    out = pd.DataFrame(index=domains.index)
    out["short_name"] = domains.get("short_name", pd.Series(dtype=str))
    out["base_score"] = base_score(domains, assumptions)
    out["cost_multiplier"] = [assumptions.cost_for(code) for code in domains.index]
    out["score"] = out["base_score"] / out["cost_multiplier"]
    out["rank"] = out["score"].rank(ascending=False, method="min").astype(int)
    if "n_risk_rows" in domains.columns:
        out["n_risk_rows"] = domains["n_risk_rows"]
    return out.sort_values("rank")


def diff_rankings(
    left: pd.DataFrame,
    right: pd.DataFrame,
    left_name: str = "left",
    right_name: str = "right",
) -> pd.DataFrame:
    """Which domains changed relative order between two rankings, and by how much.

    `shift` is positive when the domain moved up (towards rank 1) in `right`.
    """
    common = left.index.intersection(right.index)
    if len(common) == 0:
        raise ValueError("the two rankings share no domain")

    out = pd.DataFrame(index=common)
    out["short_name"] = left.loc[common, "short_name"]
    out[f"rank_{left_name}"] = left.loc[common, "rank"]
    out[f"rank_{right_name}"] = right.loc[common, "rank"]
    out["shift"] = out[f"rank_{left_name}"] - out[f"rank_{right_name}"]
    return out.reindex(
        out["shift"].abs().sort_values(ascending=False, kind="stable").index
    )


def pair_order_agreement(left: pd.DataFrame, right: pd.DataFrame) -> float:
    """Share of domain pairs that keep their relative order across the two rankings.

    The same measure the sensitivity experiment reports, so a diff between two
    assumption sets is comparable to the spread an unknown mitigation cost produces.
    """
    common = left.index.intersection(right.index)
    if len(common) < 2:
        raise ValueError("need at least two shared domains to compare pairs")
    a = left.loc[common, "rank"].to_numpy(dtype=float)
    b = right.loc[common, "rank"].to_numpy(dtype=float)
    agree = np.sign(np.subtract.outer(a, a)) * np.sign(np.subtract.outer(b, b)) > 0
    iu = np.triu_indices(len(common), 1)
    return float(agree[iu].mean())
