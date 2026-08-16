# Risk Decision Lab

A decision-modeling layer on top of the [MIT AI Risk Repository](https://airisk.mit.edu).
MIT maps the evidence; this project makes competing interpretations of that evidence
explicit, computable, and comparable — and shows which missing parameters actually change
the conclusions.

Current stage: data reality check. Prototype (assumption sets, ranking diff, sensitivity)
is next.

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

Sources: [airisk.mit.edu/risks](https://airisk.mit.edu/risks),
[osf.io/pj2qr](https://osf.io/pj2qr), [arXiv:2606.04490](https://arxiv.org/abs/2606.04490)
(Delphi), [arXiv:2512.11931](https://arxiv.org/abs/2512.11931) (mitigations),
[arXiv:2408.12622](https://arxiv.org/abs/2408.12622) (repository).
