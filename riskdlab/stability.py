"""Simple robustness analysis over uncertain relative mitigation costs."""

from __future__ import annotations

import warnings

import numpy as np
import pandas as pd
from scipy.stats import rankdata

from riskdlab.assumptions import AssumptionSet
from riskdlab.ranking import base_score


DEFAULT_SAMPLES = 4_000
DEFAULT_SEED = 20260816


def analyze_cost_stability(
    domains: pd.DataFrame,
    assumptions: AssumptionSet,
    *,
    samples: int = DEFAULT_SAMPLES,
    seed: int = DEFAULT_SEED,
    top: int = 3,
) -> pd.DataFrame:
    """Summarize ranks across sampled cost assumptions.

    Each domain cost is sampled independently and log-uniformly within its declared
    range. The resulting shares describe the sampled assumption space; they are not
    calibrated probabilities about the real world.
    """
    if samples <= 0:
        raise ValueError("samples must be > 0")
    if top <= 0:
        raise ValueError("top must be > 0")
    if domains.empty:
        raise ValueError("need at least one domain")

    codes = [str(code) for code in domains.index]
    configured = set(assumptions.cost_multipliers) | set(assumptions.cost_ranges)
    unknown = sorted(configured - set(codes))
    if unknown:
        warnings.warn(
            f"{assumptions.name}: costs for domains that are not in the data: {unknown}",
            stacklevel=2,
        )
    ranges = np.asarray([assumptions.cost_range_for(code) for code in codes], dtype=float)
    rng = np.random.default_rng(seed)
    draws = np.exp(
        rng.uniform(np.log(ranges[:, 0]), np.log(ranges[:, 1]), size=(samples, len(codes)))
    )
    scores = base_score(domains, assumptions).to_numpy(dtype=float)[None, :] / draws
    ranks = rankdata(-scores, axis=1, method="min")

    out = pd.DataFrame(index=domains.index).rename_axis("domain")
    out["short_name"] = domains.get("short_name", pd.Series(dtype=str))
    out["cost_min"] = ranges[:, 0]
    out["cost_max"] = ranges[:, 1]
    out["best_rank"] = ranks.min(axis=0).astype(int)
    out["median_rank"] = np.median(ranks, axis=0)
    out["worst_rank"] = ranks.max(axis=0).astype(int)
    out[f"top_{top}_share"] = (ranks <= top).mean(axis=0)
    return out.sort_values(
        [f"top_{top}_share", "median_rank"], ascending=[False, True], kind="stable"
    )
