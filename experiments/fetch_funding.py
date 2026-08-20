"""Fetch the public grant databases and write the committed funding snapshots.

Run by hand; nothing in `riskdlab/` or the tests goes to the network. Two steps:

    python experiments/fetch_funding.py fetch      # network -> data/raw/funding/
    python experiments/fetch_funding.py build      # data/raw/funding/ -> snapshots/funding/

`fetch` needs two environment variables for Coefficient Giving, whose site blocks
data-centre IPs but whose grants database is an Algolia index queried by the page's own
JavaScript. The app id and the search-only key sit in two hidden inputs on any fund
page (`#algolia-app-id`, `#algolia-search-key`; index name in `#algolia-index-name`):

    COEFFICIENT_ALGOLIA_APP_ID=...  COEFFICIENT_ALGOLIA_KEY=...  python experiments/fetch_funding.py fetch

The key is the public front-end key the site ships to every visitor; it is still not
committed here. Everything else (EA Funds, Manifund, SFF) is a plain unauthenticated GET.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import sys
import urllib.parse
import urllib.request
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from riskdlab.funding.sff import ROUNDS, PAGE_URL, read_round_files  # noqa: E402

RAW = ROOT / "data" / "raw" / "funding"
SNAPSHOTS = ROOT / "snapshots" / "funding"
UA = {"User-Agent": "Mozilla/5.0 (risk-decision-lab; research snapshot)"}

EAFUNDS_URL = "https://funds.effectivealtruism.org/api/grants"
MANIFUND_URL = "https://manifund.org/api/v0/projects"
ALGOLIA_INDEX = os.environ.get("COEFFICIENT_ALGOLIA_INDEX", "coefficientgiving")


def _get(url: str, headers: dict | None = None, data: bytes | None = None) -> bytes:
    request = urllib.request.Request(url, headers={**UA, **(headers or {})}, data=data)
    with urllib.request.urlopen(request, timeout=60) as response:
        return response.read()


def fetch(today: str) -> None:
    RAW.mkdir(parents=True, exist_ok=True)

    (RAW / f"eafunds_grants_{today}.csv").write_bytes(_get(EAFUNDS_URL))
    print("EA Funds: ok")

    projects, before = [], None
    while True:
        url = MANIFUND_URL + (f"?before={urllib.parse.quote(before)}" if before else "")
        page = json.loads(_get(url))
        if not page:
            break
        projects.extend(page)
        before = page[-1]["created_at"]
        if len(page) < 100:
            break
    (RAW / f"manifund_projects_{today}.json").write_text(json.dumps(projects))
    print(f"Manifund: {len(projects)} projects")

    for name in ROUNDS:
        page = _get(PAGE_URL.format(round=name))
        (RAW / f"sff_{name.replace('/', '_')}.html").write_bytes(page)
    print(f"SFF: {len(ROUNDS)} round pages")

    app_id = os.environ.get("COEFFICIENT_ALGOLIA_APP_ID")
    key = os.environ.get("COEFFICIENT_ALGOLIA_KEY")
    if not (app_id and key):
        print("Coefficient: skipped (set COEFFICIENT_ALGOLIA_APP_ID and COEFFICIENT_ALGOLIA_KEY)")
        return
    endpoint = f"https://{app_id}-dsn.algolia.net/1/indexes/{ALGOLIA_INDEX}/query"
    headers = {
        "X-Algolia-API-Key": key,
        "X-Algolia-Application-Id": app_id,
        "Content-Type": "application/json",
    }

    def query(params: str) -> dict:
        return json.loads(_get(endpoint, headers, json.dumps({"params": params}).encode()))

    years = query("query=&filters=post_type:Grants&hitsPerPage=0&facets=award_year&maxValuesPerFacet=100")
    hits: dict[str, dict] = {}
    # the public key caps pagination at 1000 hits, so page inside each award year
    for year in years["facets"]["award_year"]:
        page_number = 0
        while True:
            page = query(
                f"query=&filters=post_type:Grants AND award_year:{year}"
                f"&hitsPerPage=1000&page={page_number}&attributesToHighlight="
            )
            for hit in page["hits"]:
                hits[hit["objectID"]] = hit
            if page_number + 1 >= page["nbPages"]:
                break
            page_number += 1
    total = query("query=&filters=post_type:Grants&hitsPerPage=0")["nbHits"]
    (RAW / f"coefficient_grants_algolia_{today}.json").write_text(json.dumps(list(hits.values())))
    print(f"Coefficient: {len(hits)} grants fetched, index reports {total}")


def _latest(pattern: str) -> Path:
    matches = sorted(RAW.glob(pattern))
    if not matches:
        raise FileNotFoundError(f"no {pattern} in {RAW}; run `fetch` first")
    return matches[-1]


def build(today: str) -> None:
    SNAPSHOTS.mkdir(parents=True, exist_ok=True)

    raw = json.loads(_latest("coefficient_grants_algolia_*.json").read_text())
    rows = []
    for hit in raw:
        rows.append(
            {
                "grant_id": hit["objectID"],
                "post_id": hit.get("post_id"),
                "award_date": dt.datetime.fromtimestamp(int(hit["award_date"]), dt.UTC).date().isoformat()
                if hit.get("award_date") else "",
                "award_year": hit.get("award_year"),
                "organization": "; ".join(hit.get("organization_name") or []),
                "title": hit.get("title", ""),
                "amount_usd": hit.get("grant_amount"),
                "focus_areas": "; ".join(hit.get("focus-area") or []),
                "funding_type": "; ".join(hit.get("funding_type") or []),
                "url": hit.get("url", ""),
            }
        )
    coefficient = pd.DataFrame(rows).sort_values(["award_date", "grant_id"])
    coefficient.to_csv(SNAPSHOTS / f"coefficient-grants-{today}.csv", index=False)
    print(f"coefficient: {len(coefficient)} rows")

    eafunds = pd.read_csv(_latest("eafunds_grants_*.csv"))
    eafunds.to_csv(SNAPSHOTS / f"eafunds-grants-{today}.csv", index=False)
    print(f"eafunds: {len(eafunds)} rows")

    projects = json.loads(_latest("manifund_projects_*.json").read_text())
    rows = []
    for project in projects:
        txns = project.get("txns") or []
        usd = [float(t.get("amount") or 0) for t in txns if t.get("token") == "USD"]
        profile = project.get("profiles") or {}
        rows.append(
            {
                "project_id": project["id"],
                "slug": project.get("slug", ""),
                "title": project.get("title", ""),
                "created_at": project.get("created_at", ""),
                "stage": project.get("stage", ""),
                "type": project.get("type", ""),
                "creator": profile.get("username", "") if isinstance(profile, dict) else "",
                "causes": "; ".join(c.get("slug", "") for c in (project.get("causes") or []) if isinstance(c, dict)),
                "funding_goal_usd": project.get("funding_goal"),
                "min_funding_usd": project.get("min_funding"),
                "raised_usd": sum(usd),
                "n_txns": len(txns),
                "blurb": project.get("blurb", "") or "",
                "description": (project.get("description") or "")[:4000],
            }
        )
    manifund = pd.DataFrame(rows).sort_values("created_at")
    manifund.to_csv(SNAPSHOTS / f"manifund-projects-{today}.csv", index=False)
    print(f"manifund: {len(manifund)} rows")

    sff = read_round_files(RAW)
    sff.to_csv(SNAPSHOTS / f"sff-recommendations-{today}.csv", index=False)
    print(f"sff: {len(sff)} rows, ${sff['amount_usd'].sum():,.0f}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("step", choices=["fetch", "build"])
    parser.add_argument("--date", default=dt.date.today().isoformat(), help="snapshot date stamp (default: today)")
    args = parser.parse_args()
    (fetch if args.step == "fetch" else build)(args.date)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
