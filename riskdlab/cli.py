"""CLI: rank the risk domains under one assumption set, diff two of them, or
browse the committed mitigation snapshot."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Sequence

import pandas as pd

from riskdlab.assumptions import AssumptionSet
from riskdlab.data import DEFAULT_DELPHI_PATH, DEFAULT_REPOSITORY_PATH, load_domains
from riskdlab.mitigations import (
    ACTION_ID_COLUMN,
    DEFAULT_DOCUMENTS_PATH,
    DEFAULT_MITIGATIONS_PATH,
    DEFAULT_TAXONOMY_PATH,
    SHORT_REF_COLUMN,
    SOURCE_COLUMN,
    check_bibliography,
    load_mitigations,
    read_documents,
    read_taxonomy,
    source_counts,
    subcategory_counts,
)
from riskdlab.ranking import diff_rankings, pair_order_agreement, rank_domains
from riskdlab.stability import DEFAULT_SAMPLES, DEFAULT_SEED, analyze_cost_stability

_FLOAT = "{:6.2f}".format


def _fmt(value: float) -> str:
    return _FLOAT(value)


def _positive_int(value: str) -> int:
    parsed = int(value)
    if parsed <= 0:
        raise argparse.ArgumentTypeError("must be greater than zero")
    return parsed


def format_ranking(ranked: pd.DataFrame, top: int | None = None) -> str:
    shown = ranked if top is None else ranked.head(top)
    columns = ["rank", "short_name", "base_score", "cost_multiplier", "score"]
    if "n_risk_rows" in shown.columns:
        columns.append("n_risk_rows")
    table = shown.reset_index()[["domain", *columns]]
    if "n_risk_rows" in table.columns:
        # a count, printed as one; a domain with no repository rows prints as missing
        table["n_risk_rows"] = [
            "-" if pd.isna(value) else str(int(value)) for value in table["n_risk_rows"]
        ]
    return table.to_string(index=False, float_format=_fmt, na_rep="-")


def format_stability(stability: pd.DataFrame, cutoff: int) -> str:
    """Render the empirical rank range and top-N share for every domain."""
    table = stability.reset_index()
    share = f"top_{cutoff}_share"
    table[share] = table[share].map(lambda value: f"{value:.1%}")
    return table.to_string(index=False, float_format=_fmt, na_rep="-")


def format_mitigation_counts(mitigations: pd.DataFrame) -> str:
    """Two breakdowns of the same rows: by taxonomy subcategory and by source document."""
    by_code = subcategory_counts(mitigations).reset_index()
    by_source = source_counts(mitigations).reset_index()
    return "\n".join(
        [
            "## by category and subcategory",
            by_code.to_string(index=False),
            "",
            "## by source document",
            by_source.to_string(index=False),
        ]
    )


def format_subcategory(code: str, taxonomy: pd.DataFrame) -> str:
    """The reference entry for one subcategory, or a note that it has none."""
    if code not in taxonomy.index:
        return (
            f"{code}: not in the published taxonomy — a catch-all code the database uses "
            "for mitigations that fit no named subcategory"
        )
    entry = taxonomy.loc[code]
    return "\n".join(
        [
            f"{code} {entry['name']} (category {entry['category']} {entry['category_name']})",
            f"  {entry['description']}",
            f"  examples: {entry['examples']}",
        ]
    )


def format_mitigation_list(mitigations: pd.DataFrame, limit: int) -> str:
    shown = mitigations.head(limit)
    table = shown[[ACTION_ID_COLUMN, "subcategory", "Action Name"]]
    lines = [table.to_string(index=False)]
    if len(mitigations) > limit:
        lines.append(f"... {len(mitigations) - limit} more (raise --limit to see them)")
    return "\n".join(lines)


def format_header(
    assumptions: AssumptionSet,
    level: str | None = None,
    source: Path | str | None = None,
) -> str:
    """`level` is the level actually ranked on, which `--level` may override."""
    level = assumptions.level if level is None else level
    lines = [f"# {assumptions.name}"]
    if source is not None:
        lines.append(f"source: {source}")
    if assumptions.decision_question:
        lines.append(f"decision question: {assumptions.decision_question}")
    overridden = "" if level == assumptions.level else f" (--level, set says {assumptions.level})"
    lines.append(
        f"objective: {assumptions.objective} | scenario: {assumptions.scenario} "
        f"| harm level: {level}{overridden}"
    )
    has_ranges = assumptions.default_cost_range is not None or bool(assumptions.cost_ranges)
    if assumptions.cost_multipliers:
        costs = ", ".join(
            f"{code}={value:g}"
            for code, value in sorted(assumptions.cost_multipliers.items())
        )
        lines.append(
            f"assumed relative mitigation cost (default {assumptions.default_cost_multiplier:g}): {costs}"
        )
    elif not has_ranges:
        lines.append("assumed relative mitigation cost: equal across domains")
    if has_ranges:
        ranges = ", ".join(
            f"{code}=[{bounds[0]:g}, {bounds[1]:g}]"
            for code, bounds in sorted(assumptions.cost_ranges.items())
        )
        default = (
            "fixed"
            if assumptions.default_cost_range is None
            else f"[{assumptions.default_cost_range[0]:g}, "
                 f"{assumptions.default_cost_range[1]:g}]"
        )
        detail = f": {ranges}" if ranges else ""
        lines.append(f"mitigation cost ranges (default {default}){detail}")
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


def effective_level(assumptions: AssumptionSet, override: str | None) -> str:
    """The harm level a ranking is computed on: the assumption set's, unless overridden.

    The level is part of the interpretation, so it comes from the file; `--level` is an
    explicit command-line override that applies to every set in the invocation and is
    labelled as such in the printed header.
    """
    return assumptions.level if override is None else override


def distinct_labels(left: str, right: str) -> tuple[str, str]:
    """Column labels for the diff. Names are not unique, so collisions get a suffix."""
    if left != right:
        return left, right
    return f"{left}#1", f"{right}#2"


class _DomainSource:
    """Loads the domain table once per harm level in this invocation."""

    def __init__(self, args: argparse.Namespace) -> None:
        self._delphi = args.delphi
        self._repository = None if args.no_repository else args.repository
        self._cache: dict[str, pd.DataFrame] = {}

    def for_level(self, level: str) -> pd.DataFrame:
        if level not in self._cache:
            self._cache[level] = load_domains(
                delphi_path=self._delphi, repository_path=self._repository, level=level
            )
        return self._cache[level]


def _render(
    assumptions: AssumptionSet,
    source: Path,
    domains: pd.DataFrame,
    level: str,
    top: int | None,
) -> pd.DataFrame:
    ranked = rank_domains(domains, assumptions)
    print(format_header(assumptions, level=level, source=source))
    note = format_uncertainty(domains, assumptions)
    if note:
        print(note)
    print()
    print(format_ranking(ranked, top))
    return ranked


def _cmd_rank(args: argparse.Namespace) -> int:
    assumptions = AssumptionSet.load(args.assumption_set)
    level = effective_level(assumptions, args.level)
    domains = _DomainSource(args).for_level(level)
    _render(assumptions, args.assumption_set, domains, level, args.top)
    return 0


def _cmd_compare(args: argparse.Namespace) -> int:
    sets = [(path, AssumptionSet.load(path)) for path in (args.left, args.right)]
    domains = _DomainSource(args)

    rankings = []
    for path, assumptions in sets:
        level = effective_level(assumptions, args.level)
        rankings.append(
            _render(assumptions, path, domains.for_level(level), level, args.top)
        )
        print()

    left_label, right_label = distinct_labels(sets[0][1].name, sets[1][1].name)
    left, right = rankings
    diff = diff_rankings(left, right, left_name=left_label, right_name=right_label)
    print(format_diff(diff, pair_order_agreement(left, right)))
    return 0


def _cmd_stability(args: argparse.Namespace) -> int:
    assumptions = AssumptionSet.load(args.assumption_set)
    level = effective_level(assumptions, args.level)
    domains = _DomainSource(args).for_level(level)
    result = analyze_cost_stability(
        domains,
        assumptions,
        samples=args.samples,
        seed=args.seed,
        top=args.top_cutoff,
    )
    print(format_header(assumptions, level=level, source=args.assumption_set))
    note = format_uncertainty(domains, assumptions)
    if note:
        print(note)
    print(
        f"cost stability: {args.samples} samples | seed {args.seed} | "
        "independent log-uniform draws within each cost range"
    )
    print(
        "top share is the share of sampled assumption sets, not a calibrated "
        "real-world probability"
    )
    print()
    print(format_stability(result, args.top_cutoff))
    return 0


def _relative(path: Path) -> str:
    """Snapshot paths default to inside the repository; print them that way."""
    try:
        return str(Path(path).resolve().relative_to(Path(__file__).resolve().parent.parent))
    except ValueError:
        return str(path)


def _cmd_mitigations(args: argparse.Namespace) -> int:
    mitigations = load_mitigations(args.mitigations, args.taxonomy)
    documents = read_documents(args.documents)
    taxonomy = read_taxonomy(args.taxonomy)

    print("# mitigations")
    print(f"snapshot: {_relative(args.mitigations)}")
    catch_all = mitigations[mitigations["uncategorized"]]
    print(
        f"{len(mitigations)} mitigations | "
        f"{mitigations['subcategory'].nunique()} subcategory codes, "
        f"{catch_all['subcategory'].nunique()} of them catch-alls holding "
        f"{len(catch_all)} mitigations | {len(documents)} source documents"
    )
    print(check_bibliography(mitigations, documents).summary())
    print(
        "this dataset carries no risk linkage and no effectiveness or cost estimate; "
        "nothing below is a priority"
    )

    total = len(mitigations)
    filters = []
    if args.subcategory:
        mitigations = mitigations[mitigations["subcategory"] == args.subcategory]
        filters.append(f"subcategory {args.subcategory}")
    if args.source:
        mitigations = mitigations[mitigations[SOURCE_COLUMN] == args.source]
        filters.append(f"source {args.source}")
    if filters:
        print(f"filter: {' and '.join(filters)} — {len(mitigations)} of {total} mitigations")
    if args.subcategory:
        print(format_subcategory(args.subcategory, taxonomy))
    print()

    if mitigations.empty:
        known = ", ".join(sorted(documents[SHORT_REF_COLUMN]))
        print(f"no mitigation matches this filter. Known sources: {known}")
        return 1

    print(format_mitigation_counts(mitigations))
    if args.list:
        print()
        print("## mitigations")
        print(format_mitigation_list(mitigations, args.limit))
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
    parser.add_argument("--level", default=None,
                        help="override the harm level of every assumption set "
                             "(by default each set states its own)")
    parser.add_argument("--top", type=int, default=None,
                        help="show only the top N domains in each ranking table "
                             "(the diff always covers all of them)")

    sub = parser.add_subparsers(dest="command", required=True)

    rank = sub.add_parser("rank", help="ranking under one assumption set")
    rank.add_argument("assumption_set", type=Path)
    rank.set_defaults(func=_cmd_rank)

    compare = sub.add_parser("compare", help="two rankings and the diff between them")
    compare.add_argument("left", type=Path)
    compare.add_argument("right", type=Path)
    compare.set_defaults(func=_cmd_compare)

    stability = sub.add_parser(
        "stability", help="rank robustness across uncertain mitigation costs"
    )
    stability.add_argument("assumption_set", type=Path)
    stability.add_argument("--samples", type=_positive_int, default=DEFAULT_SAMPLES)
    stability.add_argument("--seed", type=int, default=DEFAULT_SEED)
    stability.add_argument(
        "--top-cutoff", type=_positive_int, default=3,
        help="report the share of sampled rankings in the top N (default: 3)",
    )
    stability.set_defaults(func=_cmd_stability)

    mitigations = sub.add_parser(
        "mitigations",
        help="the committed mitigation snapshot: counts by category and by source",
    )
    mitigations.add_argument("--subcategory", default=None,
                             help="keep only one subcategory code, e.g. 3.1 (or X.X)")
    mitigations.add_argument("--source", default=None,
                             help="keep only one source document, e.g. NIST2024")
    mitigations.add_argument("--list", action="store_true",
                             help="also print the matching mitigations themselves")
    mitigations.add_argument("--limit", type=_positive_int, default=20,
                             help="how many mitigations --list prints (default: 20)")
    mitigations.add_argument("--mitigations", type=Path, default=DEFAULT_MITIGATIONS_PATH)
    mitigations.add_argument("--documents", type=Path, default=DEFAULT_DOCUMENTS_PATH)
    mitigations.add_argument("--taxonomy", type=Path, default=DEFAULT_TAXONOMY_PATH)
    mitigations.set_defaults(func=_cmd_mitigations)

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
