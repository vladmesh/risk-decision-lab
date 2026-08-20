"""Risk Decision Lab: competing interpretations of the MIT AI risk data, made comparable.

The package holds four pieces: `data` imports the downloadable MIT files (Risk Repository
v4 xlsx, Delphi snapshot rds) into one domain-level table, `mitigations` imports the
committed Mitigation Database snapshot and its taxonomy, `assumptions` defines the named
set of assumptions a ranking is computed under, and `ranking` turns a table plus an
assumption set into a ranking and diffs two of them.

The mitigations stand apart on purpose: nothing links them to a risk domain, and neither
MIT file estimates their effectiveness or their cost, so they inform a decision without
entering the ranking.
"""

from riskdlab.assumptions import AssumptionSet
from riskdlab.data import load_domains
from riskdlab.mitigations import (
    check_bibliography,
    load_mitigations,
    read_documents,
    read_taxonomy,
)
from riskdlab.ranking import diff_rankings, rank_domains
from riskdlab.stability import analyze_cost_stability

__all__ = [
    "AssumptionSet",
    "load_domains",
    "load_mitigations",
    "read_documents",
    "read_taxonomy",
    "check_bibliography",
    "rank_domains",
    "diff_rankings",
    "analyze_cost_stability",
]
