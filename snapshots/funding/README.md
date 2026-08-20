# Funding snapshots

Public grant databases of four AI-safety funders, exported on **20 August 2026** by
`experiments/fetch_funding.py`, plus the subdomain labels put on them. Third-party data;
each funder's own terms apply. Nothing here is modified beyond column selection, type
normalisation and (for SFF) parsing an HTML table into CSV.

| File | Rows | What | Source and method |
|---|---|---|---|
| `coefficient-grants-2026-08-20.csv` | 2,889 | every grant in Coefficient Giving's (ex-Open Philanthropy) grants database, all focus areas | The site serves its database from an Algolia index queried by the page's own JavaScript; the index was read with the public front-end search key, paging inside each `award_year` because the key caps pagination at 1,000 hits. 2 of the index's 2,891 hits carry no award year and are not in the file. The index holds no grant description and the new site has no per-grant pages, so `title` + `organization` is all the text there is. |
| `eafunds-grants-2026-08-20.csv` | 1,663 | all EA Funds grants (LTFF 693, EAIF, AWF, GHDF), 2017–2026 Q2 | `GET https://funds.effectivealtruism.org/api/grants`, saved as served. |
| `manifund-projects-2026-08-20.csv` | 1,436 | every Manifund project, funded or not, 2023–2026 | `GET https://manifund.org/api/v0/projects`, paged with `?before=<created_at>`. `raised_usd` is the sum of USD transactions into the project; `description` is cut at 4,000 characters. |
| `sff-recommendations-2026-08-20.csv` | 515 | Survival and Flourishing Fund S-process recommendations, all 11 rounds 2019–2025 | Parsed from `https://survivalandflourishing.fund/<round>/recommendations` by `riskdlab.funding.sff`. Amounts are the page's own totals; the 2025 total ($34,334,950) matches the published "$34.33MM". 2023 H2 includes the Lightspeed Grants table the page carries. |
| `labels-mit-subdomains-2026-08-20.csv` | 2,608 | one label per in-scope grant: an MIT subdomain code or `field` / `not_ai` / `unknown`, with optional secondary, confidence, ten-word basis | Produced by a language model reading each grant's text against `riskdlab/funding/rubric.md` (v1). Batches 01–17 and the control sample: Claude Opus; batch 00: Claude Fable 5; 20 August 2026. In scope = the funder's own AI tag (Coefficient focus area *Navigating Transformative AI*; EA Funds fund *Long-Term Future Fund*; Manifund causes `tais`/`ai-gov`; all SFF rows). |
| `labels-control-2026-08-20.csv` | 120 | an independent second labelling of a random control sample | Same rubric, same model family, separate run with no access to the main labels. Agreement with the main labels: exact 91%, same MIT domain 93%, primary-or-secondary 95%. |

## What the numbers mean

- `amount_usd` is *granted* (Coefficient, EA Funds), *recommended* (SFF) or *raised*
  (Manifund) — see `amount_kind` in the unified table. SFF matching pledges and
  speculation-grant footnotes are kept in `note`, not added.
- A grant counts towards a subdomain only through its label. "General support of X" is
  labelled by what X mainly does; that is a judgement about the organisation, not the
  grant, and it is the single largest source of labelling error.
- The scope filter follows the funders' own tags. Coefficient's *Biosecurity & Pandemic
  Preparedness* and *Global Catastrophic Risks Opportunities* funds are out of scope even
  where they pay for AI-enabled bio or cyber defence, so subdomain `4.2` is undercounted
  here by construction.
- Four funders is not the field: corporate labs, governments, most academic funders and
  private donors are absent.

## Refreshing

```bash
COEFFICIENT_ALGOLIA_APP_ID=… COEFFICIENT_ALGOLIA_KEY=… \
  .venv/bin/python experiments/fetch_funding.py fetch      # network -> data/raw/funding/
.venv/bin/python experiments/fetch_funding.py build       # -> snapshots/funding/*-<today>.csv
```

Re-labelling is a new `labels-*` file written by an LLM against the rubric, with a new
control file; the snapshot date in `riskdlab/funding/grants.py` and `labels.py` then moves.
