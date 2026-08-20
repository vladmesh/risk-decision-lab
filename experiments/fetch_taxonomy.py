"""Fetch the mitigation taxonomy descriptions once and write the snapshot.

The subcategory names in the mitigation CSV are labels, not definitions: the only
machine-readable descriptions live on the draft taxonomy page, a static GitHub Pages
file with everything inlined in the markup. It is not a versioned dataset and it may
move, so it is fetched by hand, committed to `snapshots/`, and never touched again by
the package or the tests.

    python3 experiments/fetch_taxonomy.py            # rewrite the committed snapshot
    python3 experiments/fetch_taxonomy.py --stdout   # print it instead

The parser is deliberately literal about the markup it expects and fails loudly when
the page changes shape, because a silently half-parsed taxonomy is worse than none.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import urllib.request
from html import unescape
from pathlib import Path

SOURCE_URL = "https://readyresearch.github.io/mitigation-taxonomy-draft/"
REPO_ROOT = Path(__file__).resolve().parent.parent
SNAPSHOT_PATH = REPO_ROOT / "snapshots" / "mitigation-taxonomy-2026-08-20.json"

EXPECTED_CATEGORIES = 4
EXPECTED_SUBCATEGORIES = 23

_COLUMN_MARKER = '<div class="category-column">'
_CATEGORY_RE = re.compile(
    r'<div class="category-header[^"]*"[^>]*>\s*<div>(?P<title>.*?)</div>.*?'
    r'<div class="category-description">(?P<description>.*?)</div>',
    re.S,
)
_SUBCATEGORY_RE = re.compile(
    r'<div class="subcategory-header">(?P<title>.*?)</div>\s*'
    r'<div class="subcategory-details">\s*'
    r'<div class="description">(?P<description>.*?)</div>\s*'
    r'<div class="examples">\s*<div class="examples-title">Examples:</div>\s*'
    r'(?P<examples>.*?)\s*</div>',
    re.S,
)
_TITLE_RE = re.compile(r"^\s*(?P<code>[0-9]+(?:\.[0-9]+)?)\.?\s+(?P<name>.+?)\s*$")


def _text(raw: str) -> str:
    """Markup-free, whitespace-collapsed text. The page inlines `&amp;` in every title."""
    return unescape(re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", raw))).strip()


def _split_title(raw: str) -> tuple[str, str]:
    match = _TITLE_RE.match(_text(raw))
    if match is None:
        raise ValueError(f"title does not start with a taxonomy code: {_text(raw)!r}")
    return match.group("code"), match.group("name")


def parse(html: str) -> list[dict]:
    """The four category columns, each with its subcategories, in page order."""
    # The columns are siblings with no closing marker of their own, so they are cut on
    # the opening tag; the trailing script block is dropped first so it cannot be scanned.
    columns = html.split("<script", 1)[0].split(_COLUMN_MARKER)[1:]
    categories = []
    for column in columns:
        header = _CATEGORY_RE.search(column)
        if header is None:
            raise ValueError("a category column has no header or description")
        code, name = _split_title(header.group("title"))
        subcategories = []
        for sub in _SUBCATEGORY_RE.finditer(column):
            sub_code, sub_name = _split_title(sub.group("title"))
            if not sub_code.startswith(f"{code}."):
                raise ValueError(f"subcategory {sub_code} is not under category {code}")
            subcategories.append(
                {
                    "code": sub_code,
                    "name": sub_name,
                    "description": _text(sub.group("description")),
                    "examples": _text(sub.group("examples")),
                }
            )
        if not subcategories:
            raise ValueError(f"category {code} parsed with no subcategories")
        categories.append(
            {
                "code": code,
                "name": name,
                "description": _text(header.group("description")),
                "subcategories": subcategories,
            }
        )
    return categories


def build(html: str, url: str = SOURCE_URL) -> dict:
    categories = parse(html)
    total = sum(len(c["subcategories"]) for c in categories)
    if len(categories) != EXPECTED_CATEGORIES or total != EXPECTED_SUBCATEGORIES:
        raise ValueError(
            f"expected {EXPECTED_CATEGORIES} categories and {EXPECTED_SUBCATEGORIES} "
            f"subcategories, parsed {len(categories)} and {total}: the page changed"
        )
    return {
        "source": url,
        "retrieved": "2026-08-20",
        "source_sha256": hashlib.sha256(html.encode("utf-8")).hexdigest(),
        "licence": "unstated on the page; draft taxonomy of the MIT AI Risk Initiative",
        "note": (
            "The four catch-all codes used by the mitigation CSV (1.X, 2.X, 3.X, X.X) "
            "are not part of this taxonomy and have no entry here."
        ),
        "categories": categories,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--url", default=SOURCE_URL)
    parser.add_argument("--stdout", action="store_true",
                        help="print the snapshot instead of writing it")
    args = parser.parse_args(argv)

    with urllib.request.urlopen(args.url) as response:  # noqa: S310 - a fixed https URL
        html = response.read().decode("utf-8")
    snapshot = build(html, url=args.url)
    text = json.dumps(snapshot, indent=2, ensure_ascii=False) + "\n"

    if args.stdout:
        sys.stdout.write(text)
        return 0
    SNAPSHOT_PATH.write_text(text, encoding="utf-8")
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
    print(f"{SNAPSHOT_PATH.relative_to(REPO_ROOT)}: {len(text)} bytes, sha256 {digest}")
    print(f"source page sha256 {snapshot['source_sha256']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
