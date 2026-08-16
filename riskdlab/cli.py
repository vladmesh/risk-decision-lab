"""CLI: rank the risk domains under one assumption set, or diff two of them."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Sequence

import pandas as pd

from riskdlab.assumptions import AssumptionSet
from riskdlab.data import DEFAULT_DELPHI_PATH, DEFAULT_REPOSITORY_PATH, load_domains
from riskdlab.ranking import diff_rankings, pair_order_agreement, rank_domains

_FLOAT = "{:6.2f}".format


def _fmt(value: float) -> str:
    return _FLOAT(value)


def format_ranking(ranked: pd.DataFrame, top: int | None = None) -> str:
    shown = ranked if top is None else ranked.head(top)
    columns = ["rank", "short_name", "base_score", "cost_multiplier", "score"]
    if "n_risk_rows" in shown.columns:
        columns.append("n_risk_rows")
    table = shown.reset_index()[["domain", *columns]]
    if "n_risk_rows" in table.columns:
        table["n_risk_rows"] = table["n_risk_rows"].astype("Int64")
    return table.to_string(index=False, float_format=_fmt, na_rep="-")


def format_header(assumptions: AssumptionSet) -> str:
    lines = [f"# {assumptions.name}"]
    if assumptions.decision_question:
        lines.append(f"decision question: {assumptions.decision_question}")
    lines.append(
        f"objective: {assumptions.objective} | scenario: {assumptions.scenario} "
        f"| harm level: {assumptions.level}"
    )
    if assumptions.cost_multipliers:
        costs = ", ".join(
            f"{code}={value:g}"
            for code, value in sorted(assumptions.cost_multipliers.items())
        )
        lines.append(
            f"assumed relative mitigation cost (default {assumptions.default_cost_multiplier:g}): {costs}"
        )
    else:
        lines.append("assumed relative mitigation cost: equal across domains")
    return "\n".join(lines)


def format_uncertainty(domains: pd.DataFrame, assumptions: AssumptionSet) -> str | None:
    """The CI is nearly as wide as the estimate; any ranking has to say so up front."""
    lower = f"{assumptions.scenario}_ci_lower"
    upper = f"{assumptions.scenario}_ci_upper"
    if lower not in domains.columns or upper not in domains.columns:
        return None
    width = (domains[upper] - domains[lower]).median()
    estimate = domains[assumptions.scenario].median()
    return (
        f"median 95% CI width {width:.1f} pp at a median estimate of {estimate:.1f}% "
        f"— rank differences below that are noise"
    )


def format_diff(diff: pd.DataFrame, agreement: float) -> str:
    moved = diff[diff["shift"] != 0]
    largest = int(diff["shift"].abs().max())
    lines = [
        "# diff",
        f"domains that changed rank: {len(moved)}/{len(diff)} "
        f"| largest shift: {largest} position{'' if largest == 1 else 's'} "
        f"| pairs keeping their order: {agreement:.1%}",
        "",
        diff.reset_index().to_string(index=False, na_rep="-"),
    ]
    return "\n".join(lines)


def _load(args: argparse.Namespace) -> pd.DataFrame:
    repository = None if args.no_repository else args.repository
    return load_domains(delphi_path=args.delphi, repository_path=repository, level=args.level)


def _cmd_rank(args: argparse.Namespace) -> int:
    assumptions = AssumptionSet.load(args.assumption_set)
    domains = _load(args)
    ranked = rank_domains(domains, assumptions)
    print(format_header(assumptions))
    note = format_uncertainty(domains, assumptions)
    if note:
        print(note)
    print()
    print(format_ranking(ranked, args.top))
    return 0


def _cmd_compare(args: argparse.Namespace) -> int:
    left = AssumptionSet.load(args.left)
    right = AssumptionSet.load(args.right)
    domains = _load(args)

    ranked = {}
    for assumptions in (left, right):
        ranking = rank_domains(domains, assumptions)
        ranked[assumptions.name] = ranking
        print(format_header(assumptions))
        note = format_uncertainty(domains, assumptions)
        if note:
            print(note)
        print()
        print(format_ranking(ranking, args.top))
        print()

    diff = diff_rankings(
        ranked[left.name], ranked[right.name], left_name=left.name, right_name=right.name
    )
    print(format_diff(diff, pair_order_agreement(ranked[left.name], ranked[right.name])))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="riskdlab",
        description="Rank MIT AI risk domains under explicit assumption sets and diff them.",
    )
    parser.add_argument("--delphi", type=Path, default=DEFAULT_DELPHI_PATH,
                        help="path to delphi_snapshot.rds")
    parser.add_argument("--repository", type=Path, default=DEFAULT_REPOSITORY_PATH,
                        help="path to the Risk Repository xlsx")
    parser.add_argument("--no-repository", action="store_true",
                        help="skip the repository (drops the n_risk_rows column)")
    parser.add_argument("--level", default="catastrophic", help="harm level to rank on")
    parser.add_argument("--top", type=int, default=None, help="show only the top N domains")

    sub = parser.add_subparsers(dest="command", required=True)

    rank = sub.add_parser("rank", help="ranking under one assumption set")
    rank.add_argument("assumption_set", type=Path)
    rank.set_defaults(func=_cmd_rank)

    compare = sub.add_parser("compare", help="two rankings and the diff between them")
    compare.add_argument("left", type=Path)
    compare.add_argument("right", type=Path)
    compare.set_defaults(func=_cmd_compare)

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return args.func(args)
    except FileNotFoundError as exc:
        print(f"error: {exc}")
        return 2


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
