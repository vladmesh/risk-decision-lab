"""Risk Decision Lab: competing interpretations of the MIT AI risk data, made comparable.

The package holds three pieces: `data` imports the MIT files (Risk Repository v4 xlsx,
Delphi snapshot rds) into one domain-level table, `assumptions` defines the named set of
assumptions a ranking is computed under, and `ranking` turns a table plus an assumption
set into a ranking and diffs two of them.
"""

from riskdlab.assumptions import AssumptionSet
from riskdlab.data import load_domains
from riskdlab.ranking import diff_rankings, rank_domains

__all__ = ["AssumptionSet", "load_domains", "rank_domains", "diff_rankings"]
