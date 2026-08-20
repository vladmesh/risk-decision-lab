"""Risk Decision Lab: expert signal beside money, per MIT AI risk subdomain.

`data` imports the downloadable MIT files (Risk Repository v4 xlsx, Delphi snapshot rds);
`experts` reads the Delphi per-expert rows (paired reductions, bootstrap ranks, top
concerns); `funding` reads the committed grant snapshots and their subdomain labels;
`gapmap` joins the two into one table per subdomain. `mitigations` imports the Mitigation
Database snapshot, which links to no subdomain and stands beside the map. `assumptions`,
`ranking` and `stability` are the earlier ranking prototype, kept as a demonstration.
"""

from riskdlab.assumptions import AssumptionSet
from riskdlab.data import load_domains, read_delphi
from riskdlab.experts import bootstrap_rankings, paired_reduction, top_concerns
from riskdlab.funding import agreement, load_grants, read_labels
from riskdlab.gapmap import build_gap_map, funding_by_label
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
    "read_delphi",
    "paired_reduction",
    "bootstrap_rankings",
    "top_concerns",
    "load_grants",
    "read_labels",
    "agreement",
    "build_gap_map",
    "funding_by_label",
    "load_mitigations",
    "read_documents",
    "read_taxonomy",
    "check_bibliography",
    "rank_domains",
    "diff_rankings",
    "analyze_cost_stability",
]
