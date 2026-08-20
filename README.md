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
- **Mitigation Database** (831 mitigations, 13 source documents): published as Airtable
  only, with no programmatic export, so a hand-made snapshot is committed under
  `snapshots/` and read by `riskdlab.mitigations`. Its taxonomy is 4 categories and 23
  named subcategories plus 4 catch-alls; 127 mitigations sit in `3.1 Testing & Auditing`
  and 125 in `1.2 Risk Management`, and two documents (NIST2024, UK Government2023)
  contribute 373 of the 831. Still no risk↔mitigation linkage and no effectiveness or
  cost estimates — the two parameters the ranking turns out to depend on.
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

The mitigation snapshots need no download step: Airtable blocks programmatic export, so
they are committed to `snapshots/` instead, together with a snapshot of the draft
taxonomy page that holds the subcategory descriptions. Provenance, hashes and the parsing
traps are in [`snapshots/README.md`](snapshots/README.md). Nothing in `riskdlab/` or in
the tests goes to the network; the one script that does is run by hand:

```bash
.venv/bin/python experiments/fetch_taxonomy.py   # refetch the taxonomy snapshot
```

## Prototype

`riskdlab/` imports the two downloadable datasets into one domain-level table and ranks the 24 domains
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

## Mitigations

The Mitigation Database is imported by `riskdlab.mitigations`, which reads the committed
snapshot without any argument and needs no download:

```bash
.venv/bin/python -m riskdlab mitigations
.venv/bin/python -m riskdlab mitigations --subcategory 3.1 --list
.venv/bin/python -m riskdlab mitigations --source NIST2024
```

The command prints the breakdown by taxonomy subcategory and by source document, the
description of a subcategory when you filter on one, and — first, every time — the state
of the only link the data does contain: all 13 `Action Source` values match the 13
`ShortRef` values in the documents file in both directions, and every `Action ID` has the
form `A<number>_<Action Source>`. `check_bibliography` is the same check from Python.

`MitigationCode` is split into a category and a subcategory (`3.1 Testing & Auditing` ->
`3`, `3.1`). Four of the 27 codes are catch-alls — `1.X`, `2.X`, `3.X` and `X.X` — and
they are kept and flagged as `uncategorized`, not filtered out: the 11 mitigations coded
`X.X` are as real as the rest. The taxonomy is a lookup from subcategory code to name and
description (`read_taxonomy`), and it covers the 23 named subcategories only; a catch-all
code keeps its row with an empty description.

**What is not in this data.** There is no link from a mitigation to a risk or a risk
domain, and no estimate of a mitigation's effectiveness or cost — MIT collects neither,
and this repository does not invent them. So the mitigation tables cannot rank
mitigations, cannot feed the domain ranking, and cannot answer "what should we do first"
on their own; they say what has been proposed, by whom, and under which heading. The two
missing parameters are exactly the ones the sensitivity analysis above shows the decision
depends on.

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

Tests run on synthetic fixtures plus the committed mitigation snapshot; they need no
download and no network:

```bash
.venv/bin/python -m pytest
```

## Licence

Code and documentation in this repository: MIT, see [`LICENSE`](LICENSE).

The data does not belong to us. The snapshots in `snapshots/` are the MIT AI Risk
Initiative's AI Risk Mitigation Database, redistributed unmodified under CC BY 4.0, plus a
parsed snapshot of its draft taxonomy page; the Repository and Delphi datasets you
download yourself carry their own licences (CC BY 4.0 at the time of writing). Attribution details: [`snapshots/README.md`](snapshots/README.md).

Sources: [airisk.mit.edu/risks](https://airisk.mit.edu/risks),
[osf.io/pj2qr](https://osf.io/pj2qr), [arXiv:2606.04490](https://arxiv.org/abs/2606.04490)
(Delphi), [arXiv:2512.11931](https://arxiv.org/abs/2512.11931) (mitigations),
[arXiv:2408.12622](https://arxiv.org/abs/2408.12622) (repository).
