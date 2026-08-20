# Risk Decision Lab

A gap map over AI risk: what experts expect, beside where the money goes, in the same
24 coordinates. The MIT AI Risk Repository gives the coordinates (its 24 risk subdomains)
and an expert survey over them; five funders' public grant databases give the money. This
repository joins the two, shows the uncertainty on both sides, and says what is missing
before any of it can be called a priority.

Current stage: prototype with real data end to end — snapshots, labels, the joined table,
and a first reading of it. Nothing here is a ranking of what to fund.

## What the table says (2024 – Aug 2026, five funders, $789M)

`results/gapmap-2024-2026-catastrophic.csv` and `results/risk-by-method-2024-2026.csv` are
the outputs; the reading below is ours. The same table as a one-page chart with the
findings and caveats: **[vladmesh.github.io/risk-decision-lab](https://vladmesh.github.io/risk-decision-lab/)**
(source: `docs/index.html`).

| | |
|---|---|
| **Where the money is** | On grant labels alone, 43% of the dollars are field-building and general support that attach to no subdomain; 23% governance (`6.5`); 9% misalignment (`7.1`); 8% dangerous-capability evaluations (`7.2`). Splitting the 21 largest general-support grantees by their own published programme mix (`snapshots/funding/programme-splits-2026-08-20.csv`, an allocation assumption with a source per row) moves $437M: unattributed falls to **28%**, misalignment rises to **16%**, weapons & cyber to 3% (mostly AI-bio fellowship tracks, low confidence), governance stays at **22–23%** either way. Both variants are saved under `results/`. |
| **Where the experts are** | By mean probability of catastrophic harm under business as usual, the Delphi top three are dangerous capabilities (`7.2`, 21.5%), weapons & cyberattacks (`4.2`, 21.0%) and power centralization (`6.1`, 18.0%). By share of experts naming a domain a top-3 concern: fraud & scams (`4.3`, 27%), power centralization (24%), then disinformation, false information and dangerous capabilities (22% each). |
| **The mismatches** | `6.1` power centralization: rank 3 by expected severity, rank 2 by concern, **$5.4M / 0.7%** of the money with or without splits (most of it FLI's power-concentration RFP). `4.2` weapons & cyber: rank 2 by severity, **$2.3M / 0.3%** on grant labels, $26M / 3% once MATS's and CBAI's AI-bio tracks are counted — and not an artefact of scope: Coefficient's biosecurity and GCR funds were read grant by grant, and the 87 AI-related grants there are field-building, not AI-enabled bio or cyber defence. `7.4` interpretability: rank **24 of 24** as a *risk* in the expert survey, **$26–34M** as a *field*. |
| **Risk vs method** | Every grant also carries a *method* label (MIT's 23 mitigation controls plus seven research/talent/advocacy labels of ours). The cross-table resolves the `7.4` puzzle: its $34M is **$30M of interpretability research** — a method, funded because it serves `7.1`/`7.2`, not because anyone rates opacity as a top harm. Likewise `7.2` is $61M of evaluations (`3.1`), `6.5` is $149M of risk-management and regulation work (`1.2`), `7.1` is $57M of empirical alignment research. By method, the whole portfolio is: talent & community 30%, risk management / regulation 21%, empirical safety research 15%, evaluations 10%, advocacy & communication 6%, forecasting 4%, interpretability 4%, theory 3%. |
| **How noisy the expert side is** | Resampling experts within each domain (1,000 draws) keeps 83% of pairwise domain orderings; rank intervals are wide (e.g. `6.6` environmental harm: point rank 5, 90% interval 1–19, from 23 experts). The first seven domains are separated by 5 percentage points with standard errors of 1–2.5 pp. |
| **How noisy the money side is** | A second, independent labelling of 120 control grants agrees with the main labels on the exact subdomain 91% of the time, on the MIT domain 93%. Labels for "General support of X" rest on what X does, not on the grant text. |

The table is not cost-effectiveness: nobody has measured what a dollar buys in any
subdomain, and the mitigation database carries no effectiveness or cost. What it does give
a funder is a map of attention — expert attention and money — and the places where the
two disagree enough to ask why.

## The data

Three layers, all public, all snapshotted with provenance. Nothing in `riskdlab/` or the
tests goes to the network.

**Risk coordinates and expert signal — MIT AI Risk Initiative** ([airisk.mit.edu](https://airisk.mit.edu))

- **AI Risk Repository v4** (arXiv:2408.12622): 2,574 rows extracted from 74 frameworks,
  classified under a causal and a domain taxonomy. We use the domain taxonomy — 7 domains,
  24 subdomains `N.N` — as the coordinate system, and the repository row counts per
  subdomain as a measure of how much literature sits behind each number. No quantitative
  columns.
- **Delphi study, Round 3** (OSF [osf.io/pj2qr](https://osf.io/pj2qr), arXiv:2606.04490):
  209 experts distributing probability over five harm levels per subdomain under two
  scenarios (business as usual, pragmatic mitigations), plus top-3 concerns with an
  insider/outsider split, and responsibility-by-actor / vulnerability-by-sector ratings.
  The snapshot ships **per-expert rows** under a stable hash, which is what lets us compute
  within-expert reductions with standard errors and bootstrap the rankings instead of
  quoting aggregate CIs.
- **AI Risk Mitigation Database** (arXiv:2512.11931): 831 measures from 13 policy
  documents under a four-category control taxonomy; Airtable-only, so a hand export is
  committed in `snapshots/`. It links to no risk subdomain and carries no effectiveness or
  cost, so it stands beside the gap map, not inside it.

**Money — four public grant databases**, `snapshots/funding/` (details and caveats in
[`snapshots/funding/README.md`](snapshots/funding/README.md)):

| funder | rows | labelled as AI-risk work | how |
|---|---|---|---|
| Coefficient Giving (ex-Open Philanthropy) | 2,889 | 716: all 629 of *Navigating Transformative AI* + 87 found by reading the Biosecurity, GCR and Forecasting funds grant by grant | Algolia index behind the site |
| Survival and Flourishing Fund | 515 | 515 (no funder tag; every row labelled) | 11 round pages parsed |
| EA Funds | 1,663 | 693 (*Long-Term Future Fund*) | `api/grants` |
| Manifund | 1,436 | 771 (`tais`, `ai-gov`) | `api/v0/projects` |
| Future of Life Institute | 146 | 130 (nuclear and non-AI rows excluded per grant) | 13 programme pages parsed |

**Labels** — `snapshots/funding/labels-mit-subdomains-2026-08-20.csv`: 2,825 grants mapped
to one subdomain (or `field`, `not_ai`, `unknown`) by a language model reading the grant
text against [`riskdlab/funding/rubric.md`](riskdlab/funding/rubric.md), with a second
independent labelling of 120 control grants beside it; `labels-methods-2026-08-20.csv`:
the same grants mapped to a method against
[`riskdlab/funding/rubric_methods.md`](riskdlab/funding/rubric_methods.md);
`scope-decisions-2026-08-20.csv`: the per-grant in/out decision for the grants outside
the funders' own AI tags, so exclusions are auditable; `programme-splits-2026-08-20.csv`:
for the 21 largest general-support grantees, shares over risk and method labels taken from
each organisation's own published programme composition (URL, year, basis and confidence
per row), applied only to general-support or `field`-labelled grants; `--no-splits`
reproduces the unsplit tables.

## Reproduce

```bash
python3 -m venv .venv && .venv/bin/pip install -e ".[test]"
mkdir -p data/raw
curl -sSL "https://docs.google.com/spreadsheets/d/15LeHcpeuZC9txkvcaMoh3sUhkMvdMMry69xxXL46DT0/export?format=xlsx" \
  -o data/raw/ai-risk-repository.xlsx
curl -sSL "https://osf.io/download/6d58m/" -o data/raw/delphi.zip && unzip -o data/raw/delphi.zip -d data/raw/delphi

.venv/bin/python -m riskdlab funding --year-from 2024           # dollars by subdomain, label agreement
.venv/bin/python -m riskdlab methods --year-from 2024           # dollars by method, risk x method table
.venv/bin/python -m riskdlab gapmap  --year-from 2024 --out results/gapmap.csv
.venv/bin/python -m pytest                                       # synthetic fixtures + committed snapshots, no network
```

Only the two MIT downloads are needed; the grant snapshots and labels are in git. The
expert bootstrap is seeded (`--seed`, `--samples`); `--year-from/--year-to/--sources`
change the funding window. `gapmap --out` writes the full table as CSV or JSON.

The other commands are the earlier prototype and still run: `rank`, `compare` and
`stability` rank the 24 domains under a YAML *assumption set* (objective, scenario, harm
level, assumed relative mitigation cost) and diff two of them; `mitigations` browses the
mitigation snapshot. They are kept because they demonstrate the negative result below.

## What we learned building the earlier prototype

The first version ranked domains by `(bau − pm) / assumed cost` and asked how stable the
ranking was to the unknown cost. Measured against the expert bootstrap, the answer is
that the ranking is about equally unstable to everything: resampling experts keeps
83–84% of pairwise orderings, switching scenario keeps 86%, a 3× unknown cost spread
keeps 79%. Twenty-four estimates between 7% and 22% with ±4 pp intervals do not rank,
and no assumption file changes that. So the domain ranking is retired as a product and
kept as a demonstration; the gap map does not rank.

## Layout

```
riskdlab/
  data.py          MIT Repository + Delphi -> one domain table (download step)
  experts.py       per-expert Delphi rows: paired reduction, bootstrap ranks, top concerns
  mitigations.py   the mitigation snapshot and its taxonomy
  funding/         grant snapshots -> one table; SFF and FLI page parsers; labels, methods, agreement; rubrics
  gapmap.py        subdomain x {expert signal, dollars by source, reserved rows}
  assumptions.py, ranking.py, stability.py   the earlier ranking prototype
  cli.py           funding | methods | gapmap | rank | compare | stability | mitigations
snapshots/         committed third-party data with provenance (mitigations, funding, labels)
results/           saved outputs of the commands above, dated
docs/              the one-page gap map, served by GitHub Pages
experiments/       one-off scripts: data recon, sensitivity, fetchers (the only code that goes online)
assumption_sets/   YAML files for the earlier prototype
tests/
```

See [`PLAN.md`](PLAN.md) for what comes next and what would make the table decision-grade.

## Licence

Code and documentation: MIT, see [`LICENSE`](LICENSE). The data is not ours: MIT AI Risk
Initiative material is CC BY 4.0 (snapshots in `snapshots/`, downloads you make yourself);
the grant databases are each funder's public records, redistributed as exported with
attribution in `snapshots/funding/README.md`.

Sources: [airisk.mit.edu](https://airisk.mit.edu), [osf.io/pj2qr](https://osf.io/pj2qr),
[arXiv:2408.12622](https://arxiv.org/abs/2408.12622), [arXiv:2606.04490](https://arxiv.org/abs/2606.04490),
[arXiv:2512.11931](https://arxiv.org/abs/2512.11931); coefficientgiving.org,
survivalandflourishing.fund, funds.effectivealtruism.org, manifund.org.
