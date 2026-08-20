# Data snapshots

Everything here is third-party data, redistributed under its own licence — not covered by
this repository's MIT licence. See `../LICENSE`.

The other two MIT datasets this project uses (AI Risk Repository v4, the Delphi OSF
snapshot) are *not* here: both download with one command, so the repository root README
tells you how to fetch them instead of shipping copies.

These two files are different. The AI Risk Mitigation Database is published only as an
Airtable base: `downloadCsv` redirects to a login, the API needs a key, and the public
page is an SPA behind bot protection. Both files below were therefore exported by hand
from the Airtable UI, and no command reproduces them — which is why they are committed.

| File | Rows | sha256 |
|---|---|---|
| `mitigation-database-2025-07-23.csv` | 831 mitigations | `811b78afa73a75d3d794b4d6474cad217dcc6586e56768d6101b273b52de956d` |
| `mitigation-database-included-documents-2025-07-23.csv` | 13 source documents | `c14c99f723636fa488c3ddcbc750cbbf21841eb70ab5886280d6e9085bfc9d47` |

- **Source:** MIT AI Risk Initiative, AI Risk Mitigation Database —
  <https://airisk.mit.edu/ai-risk-mitigations>
  - mitigations: <https://airtable.com/appUJl8KRAUMeIVXs/shrWzxZUTPzwAEZ2u/tblkm9TrIQ0dW8IJY>
  - included documents: <https://airtable.com/appUJl8KRAUMeIVXs/shr0BpCsfMcSamg7U>
- **Exported:** 20 August 2026. The date in each filename (2025-07-23) is the snapshot
  date stated by MIT, not the export date.
- **Licence:** CC BY 4.0, <https://creativecommons.org/licenses/by/4.0/>. Redistributed
  unmodified, with attribution to the MIT AI Risk Initiative.
- **Preprint:** arXiv:2512.11931.

## Notes for anyone reading the files

- Both start with a UTF-8 BOM: read them as `utf-8-sig`, or the first column arrives
  named `﻿Action ID`.
- `MitigationCode` has 27 distinct values, not the 23 subcategories of the published
  taxonomy: four are catch-alls (`1.X`, `2.X`, `3.X`, and `X.X` for 11 mitigations with no
  category at all). Validating against the 23 named subcategories fails on real data.
- Every `Action ID` is `A<number>_<Action Source>`, and all 13 `Action Source` values match
  the 13 `ShortRef` values in the documents file exactly, in both directions.
- `DOI` is empty for six documents — legislation and government publications generally do
  not have one. `URL` is populated for all 13.
- 11 of the 831 mitigations have an empty `Action Definition`.
- There is no risk-to-mitigation link and no effectiveness or cost estimate in either
  file; MIT names that linkage as future work.
