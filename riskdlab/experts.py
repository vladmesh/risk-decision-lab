"""What the Delphi snapshot says about its own uncertainty, from the per-expert rows.

`severity_aggregate` gives one number per domain and scenario with a bootstrap CI, but the
snapshot also ships `severity_expert`: every expert's probability distribution over the
five harm levels, for both scenarios, under a hash that is stable within the file. That
allows three things the aggregate table cannot: a *paired* reduction (bau minus pm within
the same expert, with its own standard error), a bootstrap over experts of any ranking,
and a count of how many experts actually stand behind each domain's number.

The `top_concerns` table is the other expert signal the prototype ignored: the share of
experts who put a domain in their top three, with an insider/outsider split.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from riskdlab.data import DEFAULT_LEVEL, SCENARIOS

LEVELS = ("negligible", "minor", "substantial", "severe", "catastrophic")
_LEVEL_COLUMN = {level: f"sev{i + 1}" for i, level in enumerate(LEVELS)}


def expert_level_table(severity_expert: pd.DataFrame, level: str = DEFAULT_LEVEL) -> pd.DataFrame:
    """One row per (expert, risk) with the expert's probability of `level` per scenario.

    Only experts who rated both scenarios for a risk are kept, so that bau - pm is a
    within-expert difference.
    """
    if level not in _LEVEL_COLUMN:
        raise ValueError(f"unknown harm level {level!r}; expected one of {list(LEVELS)}")
    column = _LEVEL_COLUMN[level]
    wide = severity_expert.pivot_table(
        index=["expert_hash", "risk_number"], columns="scenario", values=column
    )
    missing = [s for s in SCENARIOS if s not in wide.columns]
    if missing:
        raise ValueError(f"severity_expert lacks scenario(s) {missing}")
    wide = wide.dropna(subset=list(SCENARIOS)).copy()
    wide["reduction"] = wide["bau"] - wide["pm"]
    return wide.reset_index()


def paired_reduction(severity_expert: pd.DataFrame, risks: pd.DataFrame, level: str = DEFAULT_LEVEL) -> pd.DataFrame:
    """Per domain: mean bau, mean pm, mean within-expert reduction, its SE, and n experts."""
    table = expert_level_table(severity_expert, level)
    grouped = table.groupby("risk_number")
    out = pd.DataFrame(
        {
            "bau": grouped["bau"].mean(),
            "pm": grouped["pm"].mean(),
            "reduction": grouped["reduction"].mean(),
            "reduction_se": grouped["reduction"].std(ddof=1) / np.sqrt(grouped.size()),
            "n_experts": grouped.size(),
        }
    )
    index = risks.set_index("risk_number")[["taxonomy_id", "short_name"]]
    out = out.join(index, how="inner")
    out["domain"] = out["taxonomy_id"].astype(str)
    out["short_name"] = out["short_name"].astype(str)
    return out.drop(columns="taxonomy_id").set_index("domain").sort_index()


def _pair_agreement(a: np.ndarray, b: np.ndarray) -> float:
    sign = np.sign(np.subtract.outer(a, a)) * np.sign(np.subtract.outer(b, b))
    iu = np.triu_indices(len(a), 1)
    return float((sign[iu] > 0).mean())


def bootstrap_rankings(
    severity_expert: pd.DataFrame,
    risks: pd.DataFrame,
    *,
    level: str = DEFAULT_LEVEL,
    samples: int = 1000,
    seed: int = 20260820,
) -> pd.DataFrame:
    """Resample experts within each domain; report rank spread and pair-order agreement.

    For each bootstrap draw, every domain's experts are resampled with replacement and
    the domain means (bau, reduction) recomputed; domains are then ranked on each. The
    output has, per domain and per objective, the median and the 5th/95th percentile
    rank across draws, and the frame carries `attrs['pair_agreement']`: the mean share
    of domain pairs whose order matches the point ranking — the same statistic the cost
    stability analysis reports, so estimate noise and cost noise are on one scale.
    """
    table = expert_level_table(severity_expert, level)
    groups = {risk: frame[["bau", "reduction"]].to_numpy() for risk, frame in table.groupby("risk_number")}
    order = sorted(groups)
    point = np.array([groups[r].mean(axis=0) for r in order])
    rng = np.random.default_rng(seed)

    ranks = np.empty((samples, len(order), 2))
    agreement = np.empty((samples, 2))
    for s in range(samples):
        means = np.array(
            [groups[r][rng.integers(0, len(groups[r]), len(groups[r]))].mean(axis=0) for r in order]
        )
        for j in range(2):
            ranks[s, :, j] = pd.Series(-means[:, j]).rank(method="min").to_numpy()
            agreement[s, j] = _pair_agreement(point[:, j], means[:, j])

    index = risks.set_index("risk_number")
    out = pd.DataFrame({"risk_number": order})
    out["domain"] = [str(index.loc[r, "taxonomy_id"]) for r in order]
    out["short_name"] = [str(index.loc[r, "short_name"]) for r in order]
    for j, name in enumerate(("bau", "reduction")):
        out[f"{name}_point_rank"] = pd.Series(-point[:, j]).rank(method="min").astype(int).to_numpy()
        out[f"{name}_rank_p05"] = np.percentile(ranks[:, :, j], 5, axis=0)
        out[f"{name}_rank_median"] = np.median(ranks[:, :, j], axis=0)
        out[f"{name}_rank_p95"] = np.percentile(ranks[:, :, j], 95, axis=0)
    out = out.drop(columns="risk_number").set_index("domain").sort_index()
    out.attrs["pair_agreement"] = {"bau": float(agreement[:, 0].mean()), "reduction": float(agreement[:, 1].mean())}
    out.attrs["samples"] = samples
    out.attrs["seed"] = seed
    return out


def top_concerns(top_concerns_table: pd.DataFrame, risks: pd.DataFrame) -> pd.DataFrame:
    """Share of experts naming each domain a top-3 concern, raw and domain-balanced."""
    index = risks.set_index("risk_number")[["taxonomy_id", "short_name"]]
    out = top_concerns_table.set_index("risk_number")[
        ["percentage", "domain_balanced_percentage", "insider_rate", "outsider_percentage", "count", "total_respondents"]
    ].join(index, how="inner")
    out = out.rename(
        columns={
            "percentage": "concern_pct",
            "domain_balanced_percentage": "concern_pct_balanced",
            "insider_rate": "concern_pct_insiders",
            "outsider_percentage": "concern_pct_outsiders",
            "count": "concern_n",
            "total_respondents": "concern_n_respondents",
        }
    )
    out["domain"] = out["taxonomy_id"].astype(str)
    out["short_name"] = out["short_name"].astype(str)
    return out.drop(columns="taxonomy_id").set_index("domain").sort_index()
