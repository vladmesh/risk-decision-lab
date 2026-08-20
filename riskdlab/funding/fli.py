"""Future of Life Institute: parse the grant-program pages.

FLI lists grants on one page per programme (`futureoflife.org/grant-program/<slug>/`),
each grant an accordion block: grantee, "Amount recommended", and a project summary.
There is no export. Year comes from the programme slug when it carries one
(`2023-grants`), otherwise from the year the page's own intro names; four pages name
none and carry a year read off FLI's announcements by hand, marked `year_basis=assumed`.
"""

from __future__ import annotations

import html as html_module
import re
from pathlib import Path

import pandas as pd

PROGRAMS = (
    "2015-grant-program",
    "2018-grant-program",
    "2021-grants",
    "2022-grants",
    "2023-grants",
    "2024-grants",
    "2025-grants",
    "global-institutions-governing-ai",
    "impact-of-ai-on-sdgs",
    "mitigate-ai-driven-power-concentration",
    "multistakeholder-engagement-for-safe-and-prosperous-ai",
    "nuclear-war-research",
    "rfp-on-religious-projects",
)
PAGE_URL = "https://futureoflife.org/grant-program/{slug}/"

_BLOCK_SPLIT = re.compile(r'class="ct-div-block oxel_accordion ')
_TAG_RE = re.compile(r"<[^>]+>")
_MONEY_RE = re.compile(r"\$\s*([\d,]+(?:\.\d+)?)")
_YEAR_RE = re.compile(r"\b(20[12]\d)\b")

#: Pages whose intro names no year. Read from FLI's own announcements (newsletter /
#: RFP posts) on 20 Aug 2026; the grants on these pages were awarded in these years.
ASSUMED_YEARS = {
    "mitigate-ai-driven-power-concentration": 2024,
    "multistakeholder-engagement-for-safe-and-prosperous-ai": 2025,
    "nuclear-war-research": 2022,
    "rfp-on-religious-projects": 2025,
}


def _text(fragment: str) -> str:
    text = html_module.unescape(_TAG_RE.sub("|", fragment))
    return re.sub(r"(\|\s*)+", "|", text).strip("| ")


def _page_year(page: str, slug: str) -> tuple[int | None, str]:
    match = _YEAR_RE.search(slug)
    if match:
        return int(match.group(1)), "slug"
    # the intro between the page title and the recipients list says when the round ran
    start = page.find("<h1")
    head = page[start:].split('class="ct-div-block oxel_accordion ', 1)[0]
    years = [int(y) for y in _YEAR_RE.findall(_text(head))]
    if years:
        return max(years), "intro"
    if slug in ASSUMED_YEARS:
        return ASSUMED_YEARS[slug], "assumed"
    return None, "none"


def parse_program(page: str, slug: str) -> pd.DataFrame:
    """One row per grant block on a programme page."""
    blocks = _BLOCK_SPLIT.split(page)[1:]
    year, year_basis = _page_year(page, slug)
    rows = []
    for i, block in enumerate(blocks):
        fields = _text(block).split("|")
        grantee, amount, summary = "", None, ""
        for j, field in enumerate(fields):
            if field == "Project title" and j + 1 < len(fields):
                grantee = fields[j + 1]
            elif field == "Amount recommended" and j + 1 < len(fields):
                match = _MONEY_RE.search(fields[j + 1])
                amount = float(match.group(1).replace(",", "")) if match else None
            elif field == "Project Summary":
                summary = " ".join(f for f in fields[j + 1 :] if f and not f.startswith("<"))
                break
        if not grantee:
            continue
        rows.append(
            {
                "program": slug,
                "grant_id": f"fli/{slug}/{i}",
                "year": year,
                "year_basis": year_basis,
                "grantee": grantee,
                "amount_usd": amount,
                "summary": summary[:2000],
            }
        )
    if not rows:
        raise ValueError(f"{slug}: no grant blocks parsed")
    return pd.DataFrame(rows)


def parse_programs(pages: dict[str, str]) -> pd.DataFrame:
    return pd.concat([parse_program(page, slug) for slug, page in pages.items()], ignore_index=True)


def read_program_files(directory: Path | str) -> pd.DataFrame:
    """Parse every `fli_<slug>.html` the fetcher saved."""
    directory = Path(directory)
    pages = {}
    for slug in PROGRAMS:
        path = directory / f"fli_{slug}.html"
        if path.exists():
            pages[slug] = path.read_text(encoding="utf-8")
    if not pages:
        raise FileNotFoundError(f"no fli_*.html files in {directory}")
    return parse_programs(pages)
