# Risk Decision Lab

A decision-modeling layer on top of the [MIT AI Risk Repository](https://airisk.mit.edu).
MIT maps the evidence; this project makes competing interpretations of that evidence
explicit, computable, and comparable — and shows which missing parameters actually change
the conclusions.

Current stage: prototype — assumption sets, ranking diffs, and a simple cost-stability
analysis over the imported data.

## Findings so far

- **Repository v4** (2,574 rows, 74 frameworks): extraction and classification of quotes,
  two taxonomies, zero quantitative columns.
- **Delphi elicitation** ([osf.io/pj2qr](https://osf.io/pj2qr)): fully machine-readable,
  with bootstrap CIs. Joins to the Repository cleanly (24/24 subdomain codes), but one
  estimate covers on average ~54 risk rows (max 126) — domain-level numbers can't be
  propagated to individual risks.
- **Mitigation Database** (831 mitigations): published as Airtable only, no machine
  access; no risk↔mitigation linkage, no effectiveness/cost estimates.
- **Sensitivity**: an unknown mitigation-cost parameter with a 3x spread across domains
  disrupts the domain ranking more (79% of pairs keep their order) than switching the
  entire scenario from business-as-usual to pragmatic mitigations (86%). The decision is
  dominated by a parameter that isn't collected yet.
- Median 95% CI width on P(catastrophic) is 7.2 pp at a median estimate of 9.9% — any
  interface over these numbers must show that first.

## Reproduce

```bash
python3 -m venv .venv && .venv/bin/pip install pandas openpyxl rdata scipy
mkdir -p data/raw
curl -sSL "https://docs.google.com/spreadsheets/d/15LeHcpeuZC9txkvcaMoh3sUhkMvdMMry69xxXL46DT0/export?format=xlsx" \
  -o data/raw/ai-risk-repository.xlsx
curl -sSL "https://osf.io/download/6d58m/" -o data/raw/delphi.zip && unzip -o data/raw/delphi.zip -d data/raw/delphi
.venv/bin/python experiments/recon.py         # what is in the Delphi snapshot
.venv/bin/python experiments/join_test.py     # does Delphi join the Repository
.venv/bin/python experiments/sensitivity.py   # what drives the decision: present or missing data
```

All three scripts are deterministic (fixed seed in `sensitivity.py`).

## Prototype

`riskdlab/` imports both datasets into one domain-level table and ranks the 24 domains
under an **assumption set** — a named file stating the decision question, the scenario,
the harm level, and the assumed relative mitigation cost per domain. Cost is not in any
MIT dataset, so it is an assumption by construction; leaving it out is the assumption that
mitigation costs the same everywhere.

Three assumption sets ship in `assumption_sets/`: `bau-minimize-catastrophe` (which domain
is most dangerous under business as usual), `pm-maximize-reduction` (where pragmatic
mitigations buy the largest reduction per unit of assumed point cost), and
`pm-cost-uncertainty` (whether that priority survives broad cost ranges).

```bash
.venv/bin/pip install pyyaml pytest
.venv/bin/python -m riskdlab rank assumption_sets/bau-minimize-catastrophe.yaml
.venv/bin/python -m riskdlab compare \
  assumption_sets/bau-minimize-catastrophe.yaml \
  assumption_sets/pm-maximize-reduction.yaml
.venv/bin/python -m riskdlab stability \
  assumption_sets/pm-cost-uncertainty.yaml
```

`compare` prints both rankings and the diff: which domains changed relative order, by how
many positions, and what share of domain pairs kept it — the same measure the sensitivity
experiment uses, so a disagreement between two readings is comparable to the spread an
unknown mitigation cost produces. Both commands print the median 95% CI width first.

Each set is ranked on the harm level it states, so two sets in one `compare` may differ in
that too; `--level` overrides every set in the invocation and is labelled as an override in
the output. `--top N` shortens the ranking tables (the diff always covers all domains) and
`--no-repository` runs on the Delphi file alone, dropping the `n_risk_rows` column that
says how many repository risk rows each single estimate covers.

## Simple cost-stability analysis

An assumption set may state a `default_cost_range` and domain-specific `cost_ranges`:

```yaml
default_cost_range: [1.0, 2.0]
cost_ranges:
  "6.4": [3.0, 7.0]
  "7.2": [1.0, 2.5]
```

`stability` samples each domain's relative cost independently and log-uniformly within
these ranges. It reports the best, median, and worst observed rank and the share of sampled
rankings in the top 3. The seed and sample count are explicit and configurable:

```bash
.venv/bin/python -m riskdlab stability \
  assumption_sets/pm-cost-uncertainty.yaml \
  --samples 10000 --seed 20260816 --top-cutoff 3
```

These top-N shares describe the sampled assumption space. They are **not calibrated
probabilities** of a domain being a real-world priority: the ranges and the independent
log-uniform sampling rule are assumptions, not observed cost data. A normal one-off
`rank` command represents each range by its geometric midpoint.

See `PLAN.md` for the path from this simple sensitivity check to a more defensible
decision model.

Tests run on synthetic fixtures and need no downloaded data:

```bash
.venv/bin/python -m pytest
```

Sources: [airisk.mit.edu/risks](https://airisk.mit.edu/risks),
[osf.io/pj2qr](https://osf.io/pj2qr), [arXiv:2606.04490](https://arxiv.org/abs/2606.04490)
(Delphi), [arXiv:2512.11931](https://arxiv.org/abs/2512.11931) (mitigations),
[arXiv:2408.12622](https://arxiv.org/abs/2408.12622) (repository).
