# Funding snapshots

Public grant databases of five AI-safety funders, exported on **20 August 2026** by
`experiments/fetch_funding.py`, plus the subdomain labels put on them. Third-party data;
each funder's own terms apply. Nothing here is modified beyond column selection, type
normalisation and (for SFF) parsing an HTML table into CSV.

| File | Rows | What | Source and method |
|---|---|---|---|
| `coefficient-grants-2026-08-20.csv` | 2,889 | every grant in Coefficient Giving's (ex-Open Philanthropy) grants database, all focus areas | The site serves its database from an Algolia index queried by the page's own JavaScript; the index was read with the public front-end search key, paging inside each `award_year` because the key caps pagination at 1,000 hits. 2 of the index's 2,891 hits carry no award year and are not in the file. The index holds no grant description and the new site has no per-grant pages, so `title` + `organization` is all the text there is. |
| `eafunds-grants-2026-08-20.csv` | 1,663 | all EA Funds grants (LTFF 693, EAIF, AWF, GHDF), 2017–2026 Q2 | `GET https://funds.effectivealtruism.org/api/grants`, saved as served. |
| `manifund-projects-2026-08-20.csv` | 1,436 | every Manifund project, funded or not, 2023–2026 | `GET https://manifund.org/api/v0/projects`, paged with `?before=<created_at>`. `raised_usd` is the sum of USD transactions into the project; `description` is cut at 4,000 characters. |
| `sff-recommendations-2026-08-20.csv` | 515 | Survival and Flourishing Fund S-process recommendations, all 11 rounds 2019–2025 | Parsed from `https://survivalandflourishing.fund/<round>/recommendations` by `riskdlab.funding.sff`. Amounts are the page's own totals; the 2025 total ($34,334,950) matches the published "$34.33MM". 2023 H2 includes the Lightspeed Grants table the page carries. |
| `fli-grants-2026-08-20.csv` | 146 | Future of Life Institute grants from 13 programme pages (yearly lists 2015–2025 and the thematic RFPs) | Parsed from `futureoflife.org/grant-program/<slug>/` by `riskdlab.funding.fli`: grantee, amount recommended, project summary. Year from the slug or the page intro; four pages name none and carry a year read off FLI's announcements (`year_basis=assumed`). |
| `labels-mit-subdomains-2026-08-20.csv` | 2,825 | one label per in-scope grant: an MIT subdomain code or `field` / `not_ai` / `unknown`, with optional secondary, confidence, ten-word basis | Produced by a language model reading each grant's text against `riskdlab/funding/rubric.md` (v1). Batches 01–17 and the control sample: Claude Opus; batch 00: Claude Fable 5; 20 August 2026. 2,608 rows are the funders' own AI tag (Coefficient focus area *Navigating Transformative AI*; EA Funds fund *Long-Term Future Fund*; Manifund causes `tais`/`ai-gov`; all SFF rows); 217 more are grants outside those tags that the scope pass below judged to be AI-risk work (87 from Coefficient's Biosecurity, GCR and Forecasting funds, 130 from FLI). |
| `scope-decisions-2026-08-20.csv` | 661 | the per-grant AI-scope decision for Coefficient's Biosecurity / Global Catastrophic Risks / Forecasting grants (515) and all FLI grants (146), with a label for the `true` rows | Same rubric and model family, one pass, 20 August 2026. 444 `false` (pure bio, nuclear, non-AI GCR), 217 `true`. Kept so that exclusions are auditable, not silent. |
| `labels-methods-2026-08-20.csv` | 2,825 | one METHOD label per labelled grant: an MIT mitigation-control subcategory (`1.1`–`4.6`) or one of seven labels of ours (`X.research-interp`, `X.research-theory`, `X.research-empirical`, `X.forecasting`, `X.advocacy-comms`, `X.talent-community`, `X.none`) | Produced by Claude Opus against `riskdlab/funding/rubric_methods.md` (v1), 20 August 2026. The MIT control taxonomy describes controls a developer or regulator implements and has no place for research, talent or advocacy, which is most of what grants pay for; the `X.*` labels are ours and marked as such. |
| `labels-control-2026-08-20.csv` | 120 | an independent second labelling of a random control sample | Same rubric, same model family, separate run with no access to the main labels. Agreement with the main labels: exact 91%, same MIT domain 93%, primary-or-secondary 95%. |

## What the numbers mean

- `amount_usd` is *granted* (Coefficient, EA Funds), *recommended* (SFF) or *raised*
  (Manifund) — see `amount_kind` in the unified table. SFF matching pledges and
  speculation-grant footnotes are kept in `note`, not added.
- A grant counts towards a subdomain only through its label. "General support of X" is
  labelled by what X mainly does; that is a judgement about the organisation, not the
  grant, and it is the single largest source of labelling error.
- Scope is decided per grant. The funders' own AI tags are the first pass; Coefficient's
  Biosecurity, GCR and Forecasting funds and all of FLI were then read grant by grant
  (`scope-decisions-*.csv`). Of the 515 Coefficient bio/GCR/forecasting grants, 87 are
  AI-risk work and almost all of those are field-building (MATS, 80,000 Hours, regional
  AI-safety groups), not AI-enabled bio or cyber defence — so the low count for `4.2` is
  what these databases contain, not an artefact of the scope filter.
- Five funders is not the field: corporate labs, governments, most academic funders and
  private donors are absent.

## Refreshing

```bash
COEFFICIENT_ALGOLIA_APP_ID=… COEFFICIENT_ALGOLIA_KEY=… \
  .venv/bin/python experiments/fetch_funding.py fetch      # network -> data/raw/funding/
.venv/bin/python experiments/fetch_funding.py build       # -> snapshots/funding/*-<today>.csv
```

Re-labelling is a new `labels-*` file written by an LLM against the rubric, with a new
control file; the snapshot date in `riskdlab/funding/grants.py` and `labels.py` then moves.
