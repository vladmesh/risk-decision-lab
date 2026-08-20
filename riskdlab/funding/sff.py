"""Survival and Flourishing Fund: parse the per-round recommendation pages.

SFF publishes each S-process round as one HTML page and nothing else — no CSV, no API.
The markup changed three times between 2019 and 2025 (a `<table>`, then a `<table>` with
per-funder columns, then a CSS grid of `div.in-grid` cells), so the parser does not
trust the tag structure: it collects the cells in document order, reads the header row
to learn the column names, and chunks the rest into rows of that width.

Amounts are whatever the page prints as the total recommendation for the row. Footnote
figures in parentheses — speculation grants already paid, matching pledges — are kept in
`note` and not added or subtracted: the page's own total is the number of record.
"""

from __future__ import annotations

import html as html_module
import re
from pathlib import Path

import pandas as pd

ROUNDS = (
    "2019",
    "2020/h1",
    "2020/h2",
    "2021/h1",
    "2021/h2",
    "2022/h1",
    "2022/h2",
    "2023/h1",
    "2023/h2",
    "2024",
    "2025",
)
PAGE_URL = "https://survivalandflourishing.fund/{round}/recommendations"

_CELL_RE = re.compile(
    r"<(?P<tag>t[dh]|div)\b(?P<attrs>[^>]*)>(?P<body>.*?)</(?P=tag)>", re.S | re.I
)
_TAG_RE = re.compile(r"<[^>]+>")
_MONEY_RE = re.compile(r"\$\s*([\d,]+(?:\.\d+)?)")
_PAREN_RE = re.compile(r"[\(\{][^\)\}]*[\)\}]")


def _text(fragment: str) -> str:
    fragment = re.sub(r"<br\s*/?>", " ", fragment, flags=re.I)
    return re.sub(r"\s+", " ", html_module.unescape(_TAG_RE.sub(" ", fragment))).strip()


def _cells(page: str) -> list[tuple[bool, str]]:
    """(is_header, text) for every grid cell, in document order.

    A cell is a `<td>`/`<th>` or a `div.in-grid`; nested wrapper divs inside a grid
    cell are skipped by taking only the outermost match per position.
    """
    out: list[tuple[bool, str]] = []
    pos = 0
    while True:
        match = _CELL_RE.search(page, pos)
        if match is None:
            break
        tag = match.group("tag").lower()
        attrs = match.group("attrs")
        if tag == "div" and "in-grid" not in attrs:
            pos = match.start() + 1
            continue
        is_header = tag == "th" or "is-header" in attrs
        out.append((is_header, _text(match.group("body"))))
        pos = match.end()
    return out


def _money(cell: str) -> float | None:
    """The first dollar figure outside parentheses/braces; None when there is none."""
    visible = _PAREN_RE.sub("", cell)
    match = _MONEY_RE.search(visible)
    if match is None:
        return None
    return float(match.group(1).replace(",", ""))


def _column_roles(header: list[str]) -> dict[str, int]:
    roles: dict[str, int] = {}
    for i, name in enumerate(header):
        low = name.lower()
        if low.startswith("organization") and "organization" not in roles:
            roles["organization"] = i
        elif low.startswith("receiving") and "receiving" not in roles:
            roles["receiving"] = i
        elif low.startswith("purpose") and "purpose" not in roles:
            roles["purpose"] = i
        elif low == "source" or low.startswith("funder"):
            roles.setdefault("source", i)
        elif low.startswith("total") or low == "amount":
            roles["total"] = i
    if "organization" not in roles:
        raise ValueError(f"no Organization column in header {header}")
    return roles


def parse_round(page: str, round_name: str) -> pd.DataFrame:
    """One row per recommendation on a round page."""
    cells = _cells(page)
    header_idx = [i for i, (is_header, _) in enumerate(cells) if is_header]
    if not header_idx:
        raise ValueError(f"{round_name}: no header cells found")

    rows = []
    # A page can hold several tables (2023 H2: SFF proper and Lightspeed Grants); each
    # header run starts a new block that ends at the next header run.
    blocks: list[tuple[list[str], list[str]]] = []
    i = 0
    while i < len(cells):
        if not cells[i][0]:
            i += 1
            continue
        header = []
        while i < len(cells) and cells[i][0]:
            header.append(cells[i][1])
            i += 1
        body = []
        while i < len(cells) and not cells[i][0]:
            body.append(cells[i][1])
            i += 1
        blocks.append((header, body))

    for header, body in blocks:
        width = len(header)
        if width < 3 or not body:
            continue
        roles = _column_roles(header)
        if "purpose" not in roles:
            # the 2025 page has a second grid, the matching-pledge schedule; it has
            # no Purpose column and repeats organisations that are already listed
            continue
        money_columns = [
            j for j, name in enumerate(header)
            if j not in (roles["organization"], roles.get("receiving"), roles.get("purpose"), roles.get("source"))
        ]
        for start in range(0, len(body) - width + 1, width):
            row = body[start : start + width]
            org = row[roles["organization"]]
            if not org:
                continue
            if "total" in roles:
                total = _money(row[roles["total"]])
                note = row[roles["total"]]
            else:
                parts = [_money(row[j]) for j in money_columns]
                total = sum(p for p in parts if p is not None) if any(p is not None for p in parts) else None
                note = " | ".join(f"{header[j]}: {row[j]}" for j in money_columns if row[j])
            rows.append(
                {
                    "round": round_name,
                    "source": row[roles["source"]] if "source" in roles else "",
                    "organization": org,
                    "amount_usd": total,
                    "receiving_charity": row[roles["receiving"]] if "receiving" in roles else "",
                    "purpose": row[roles["purpose"]] if "purpose" in roles else "",
                    "note": note,
                }
            )
    if not rows:
        raise ValueError(f"{round_name}: header found but no rows parsed")
    frame = pd.DataFrame(rows)
    frame["year"] = frame["round"].str[:4].astype(int)
    return frame


def parse_rounds(pages: dict[str, str]) -> pd.DataFrame:
    """`{round_name: html}` -> one table for all rounds."""
    return pd.concat(
        [parse_round(page, name) for name, page in pages.items()], ignore_index=True
    )


def read_round_files(directory: Path | str) -> pd.DataFrame:
    """Parse every `sff_<round>.html` in a directory (the files `fetch_funding.py` saves)."""
    directory = Path(directory)
    pages = {}
    for name in ROUNDS:
        path = directory / f"sff_{name.replace('/', '_')}.html"
        if path.exists():
            pages[name] = path.read_text(encoding="utf-8")
    if not pages:
        raise FileNotFoundError(f"no sff_*.html files in {directory}")
    return parse_rounds(pages)
