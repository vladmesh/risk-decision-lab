"""The gap map: one row per MIT subdomain, expert signal beside money.

Columns come from three places and are labelled by origin so nothing gets read as
something it is not:

- `delphi_*`: the Delphi expert survey — mean probability of catastrophic harm under
  business as usual and pragmatic mitigations, the within-expert reduction with its
  standard error, the number of experts behind the number, the share naming the domain
  a top-3 concern, and the bootstrap rank interval.
- `fund_*`: the labelled grant snapshots — dollars and grant counts per subdomain, total
  and per source, over the year window asked for.
- the reserved rows `field`, `not_ai`, `unknown`: money that was in scope but does not
  attach to a subdomain. They are part of the table, not dropped, because the share of
  money that cannot be attributed is itself a finding.

No column here is a priority score. The table is the input to a reading, and the
reading is the analyst's.
"""

from __future__ import annotations

import pandas as pd

from riskdlab.data import DEFAULT_LEVEL
from riskdlab.experts import bootstrap_rankings, paired_reduction, top_concerns
from riskdlab.funding.labels import RESERVED, SUBDOMAINS


def funding_by_label(
    grants: pd.DataFrame,
    labels: pd.DataFrame,
    *,
    splits: pd.DataFrame | None = None,
    year_from: int | None = None,
    year_to: int | None = None,
    sources: tuple[str, ...] | None = None,
) -> pd.DataFrame:
    """Dollars and grant counts per label, total and per source.

    A grant counts if and only if it carries a label — the label is the scope decision,
    whether the funder tagged the grant as AI or not. Manifund rows count their raised
    amount, which is zero for unfunded proposals; they count towards `fund_n_grants`
    only when money moved, so a proposal nobody funded is not a grant.
    """
    frame = grants.merge(
        labels[["grant_id", "primary", "confidence"]].rename(columns={"primary": "risk"}),
        on="grant_id",
        how="inner",
    )
    if splits is not None:
        from riskdlab.funding.splits import _apply_risk_splits

        frame = _apply_risk_splits(frame, splits)
        frame["weight"] = frame["risk_weight"]
    else:
        frame["weight"] = 1.0
    if year_from is not None:
        frame = frame[frame["year"] >= year_from]
    if year_to is not None:
        frame = frame[frame["year"] <= year_to]
    if sources is not None:
        frame = frame[frame["source"].isin(sources)]
    frame = frame[frame["amount_usd"].fillna(0) > 0]
    frame["amount_share_usd"] = frame["amount_usd"] * frame["weight"]

    per_source = frame.pivot_table(index="risk", columns="source", values="amount_share_usd", aggfunc="sum", fill_value=0.0)
    per_source.columns = [f"fund_usd_{c}" for c in per_source.columns]
    out = pd.DataFrame(index=pd.Index(list(SUBDOMAINS) + list(RESERVED), name="label"))
    out["fund_usd"] = frame.groupby("risk")["amount_share_usd"].sum()
    out["fund_n_grants"] = frame.groupby("risk")["grant_id"].nunique()
    out["fund_n_low_confidence"] = frame[frame["confidence"] == "low"].groupby("risk")["grant_id"].nunique()
    out = out.join(per_source)
    out = out.fillna(0.0)
    out["fund_n_grants"] = out["fund_n_grants"].astype(int)
    out["fund_n_low_confidence"] = out["fund_n_low_confidence"].astype(int)
    total = out["fund_usd"].sum()
    out["fund_share"] = out["fund_usd"] / total if total else 0.0
    out.attrs["year_from"] = year_from
    out.attrs["year_to"] = year_to
    out.attrs["n_grants"] = int(frame["grant_id"].nunique())
    out.attrs["usd_total"] = float(total)
    split_grantees = set() if splits is None else set(splits.loc[splits["dimension"] == "risk", "grantee"])
    affected = frame[frame["grantee"].isin(split_grantees)].drop_duplicates("grant_id")
    out.attrs["split_n_grantees"] = int(affected["grantee"].nunique())
    out.attrs["split_usd"] = float(affected["amount_usd"].sum())
    return out


def expert_signal(delphi: dict[str, pd.DataFrame], *, level: str = DEFAULT_LEVEL, samples: int = 1000, seed: int = 20260820) -> pd.DataFrame:
    """Per subdomain: paired Delphi estimates, concern shares, and bootstrap rank spread."""
    risks = delphi["risks"]
    reduction = paired_reduction(delphi["severity_expert"], risks, level=level)
    ranks = bootstrap_rankings(delphi["severity_expert"], risks, level=level, samples=samples, seed=seed)
    concern = top_concerns(delphi["top_concerns"], risks)

    out = reduction.rename(
        columns={
            "bau": "delphi_bau_pct",
            "pm": "delphi_pm_pct",
            "reduction": "delphi_reduction_pp",
            "reduction_se": "delphi_reduction_se",
            "n_experts": "delphi_n_experts",
        }
    )
    out = out.join(
        ranks[["bau_point_rank", "bau_rank_p05", "bau_rank_p95", "reduction_point_rank", "reduction_rank_p05", "reduction_rank_p95"]]
        .add_prefix("delphi_")
    )
    out = out.join(concern[["concern_pct", "concern_pct_balanced", "concern_pct_insiders", "concern_pct_outsiders"]].add_prefix("delphi_"))
    out.attrs["pair_agreement"] = ranks.attrs["pair_agreement"]
    out.attrs["level"] = level
    return out


def build_gap_map(
    delphi: dict[str, pd.DataFrame],
    grants: pd.DataFrame,
    labels: pd.DataFrame,
    *,
    splits: pd.DataFrame | None = None,
    level: str = DEFAULT_LEVEL,
    year_from: int | None = None,
    year_to: int | None = None,
    sources: tuple[str, ...] | None = None,
    samples: int = 1000,
    seed: int = 20260820,
) -> pd.DataFrame:
    """The gap map table; subdomain rows carry both halves, reserved rows only money."""
    experts = expert_signal(delphi, level=level, samples=samples, seed=seed)
    money = funding_by_label(
        grants, labels, splits=splits, year_from=year_from, year_to=year_to, sources=sources
    )
    out = money.join(experts, how="left")
    out.index.name = "label"
    out["short_name"] = out["short_name"].fillna(
        pd.Series({"field": "(field-building, unattributed)", "not_ai": "(not AI risk)", "unknown": "(unknown)"})
    )
    front = ["short_name", "fund_usd", "fund_share", "fund_n_grants"]
    out = out[front + [c for c in out.columns if c not in front]]
    out.attrs.update(money.attrs)
    out.attrs["pair_agreement"] = experts.attrs["pair_agreement"]
    out.attrs["level"] = level
    return out
