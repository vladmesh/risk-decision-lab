"""Import of the MIT AI Risk Mitigation Database and its taxonomy.

Where `data` downloads its inputs, this module reads what is committed: Airtable serves
the mitigation base only through a bot-protected UI, so both CSVs live in `snapshots/`
and the default paths point straight at them — reading the mitigations takes no argument.
The taxonomy descriptions come from the same place: a snapshot of the draft taxonomy page,
fetched once by `experiments/fetch_taxonomy.py`. Nothing here goes to the network.

Two properties of the real files shape the code. `MitigationCode` carries four catch-all
codes (`1.X`, `2.X`, `3.X` and `X.X`) beside the 23 named subcategories, so the parser
accepts `X` in either position and flags those rows instead of dropping them; and every
file starts with a UTF-8 BOM, so every read is `utf-8-sig`.

There is no link from a mitigation to a risk and no effectiveness or cost estimate in
either file — MIT does not collect them — so nothing here produces one.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

SNAPSHOT_DIR = Path(__file__).resolve().parent.parent / "snapshots"

DEFAULT_MITIGATIONS_PATH = SNAPSHOT_DIR / "mitigation-database-2025-07-23.csv"
DEFAULT_DOCUMENTS_PATH = SNAPSHOT_DIR / "mitigation-database-included-documents-2025-07-23.csv"
DEFAULT_TAXONOMY_PATH = SNAPSHOT_DIR / "mitigation-taxonomy-2026-08-20.json"

#: The files are exported from Airtable with a BOM; without this the first column is
#: named `﻿Action ID` and every lookup by name misses.
SNAPSHOT_ENCODING = "utf-8-sig"

ACTION_ID_COLUMN = "Action ID"
SOURCE_COLUMN = "Action Source"
CODE_COLUMN = "MitigationCode"
SHORT_REF_COLUMN = "ShortRef"

#: The placeholder both halves of a catch-all code use: `1.X`, `X.X`.
UNCATEGORIZED = "X"

_CODE_RE = re.compile(
    rf"^\s*(?P<category>\d+|{UNCATEGORIZED})\.(?P<subcategory>\d+|{UNCATEGORIZED})"
    r"(?:\s+(?P<label>\S.*?))?\s*$"
)
_ACTION_ID_RE = re.compile(r"^A(?P<number>\d+)_(?P<source>.+)$")


def _read_csv(path: Path | str, expected: list[str]) -> pd.DataFrame:
    frame = pd.read_csv(path, encoding=SNAPSHOT_ENCODING, dtype=str).fillna("")
    missing = [column for column in expected if column not in frame.columns]
    if missing:
        raise ValueError(f"{path}: missing column(s) {missing}; columns are {list(frame.columns)}")
    return frame


def split_mitigation_code(code: str) -> tuple[str, str, str]:
    """`'1.2 Risk Management'` -> `('1', '1.2', 'Risk Management')`.

    Both halves may be the literal `X`: `X.X Control not otherwise categorized` is a real
    code carried by 11 mitigations, and dropping it would quietly lose them.
    """
    match = _CODE_RE.match(str(code))
    if match is None:
        raise ValueError(f"not a mitigation code: {code!r}")
    category, subcategory = match.group("category"), match.group("subcategory")
    return category, f"{category}.{subcategory}", (match.group("label") or "").strip()


def read_mitigations(path: Path | str = DEFAULT_MITIGATIONS_PATH) -> pd.DataFrame:
    """The 831 mitigations, with `MitigationCode` split into its parts.

    Adds `category`, `subcategory`, `subcategory_label` and `uncategorized` (true for the
    four catch-all codes). An unparsable or empty code is an error naming the rows that
    carry it, so a changed export cannot silently shrink the table.
    """
    frame = _read_csv(path, [ACTION_ID_COLUMN, SOURCE_COLUMN, CODE_COLUMN])

    parsed, bad = [], []
    for action_id, code in zip(frame[ACTION_ID_COLUMN], frame[CODE_COLUMN]):
        try:
            parsed.append(split_mitigation_code(code))
        except ValueError:
            bad.append(f"{action_id}: {code!r}")
            parsed.append(("", "", ""))
    if bad:
        raise ValueError(
            f"{path}: {len(bad)} row(s) with an unreadable {CODE_COLUMN}: "
            + "; ".join(bad[:5])
            + (" ..." if len(bad) > 5 else "")
        )

    frame["category"] = [row[0] for row in parsed]
    frame["subcategory"] = [row[1] for row in parsed]
    frame["subcategory_label"] = [row[2] for row in parsed]
    frame["uncategorized"] = [UNCATEGORIZED in (row[0], row[1].split(".")[-1]) for row in parsed]

    duplicated = frame[ACTION_ID_COLUMN][frame[ACTION_ID_COLUMN].duplicated()].tolist()
    if duplicated:
        raise ValueError(f"{path}: duplicate {ACTION_ID_COLUMN}: {sorted(set(duplicated))[:5]}")
    return frame


def read_documents(path: Path | str = DEFAULT_DOCUMENTS_PATH) -> pd.DataFrame:
    """The 13 source documents, keyed by `ShortRef` — the value `Action Source` holds."""
    frame = _read_csv(path, [SHORT_REF_COLUMN])
    duplicated = frame[SHORT_REF_COLUMN][frame[SHORT_REF_COLUMN].duplicated()].tolist()
    if duplicated:
        raise ValueError(f"{path}: duplicate {SHORT_REF_COLUMN}: {sorted(set(duplicated))}")
    return frame


def read_taxonomy(path: Path | str = DEFAULT_TAXONOMY_PATH) -> pd.DataFrame:
    """The subcategory reference: code -> name, description, examples, category.

    One row per named subcategory, indexed by `subcategory`. The four catch-all codes are
    not in the published taxonomy and deliberately have no row here; look them up through
    `describe_subcategories`, which keeps them visible with an empty description.
    """
    snapshot = json.loads(Path(path).read_text(encoding="utf-8"))
    rows = [
        {
            "subcategory": sub["code"],
            "name": sub["name"],
            "description": sub["description"],
            "examples": sub["examples"],
            "category": category["code"],
            "category_name": category["name"],
            "category_description": category["description"],
        }
        for category in snapshot["categories"]
        for sub in category["subcategories"]
    ]
    return pd.DataFrame(rows).set_index("subcategory").sort_index()


def describe_subcategories(
    codes: pd.Series | list[str], taxonomy: pd.DataFrame | None = None
) -> pd.DataFrame:
    """Name and description for each code, in the order given.

    A code with no taxonomy entry — the four catch-alls — keeps its row with an empty
    name and description rather than disappearing from the join.
    """
    taxonomy = read_taxonomy() if taxonomy is None else taxonomy
    index = pd.Index(list(codes), name="subcategory")
    return taxonomy.reindex(index).fillna("")


@dataclass(frozen=True)
class BibliographyCheck:
    """Whether the mitigations and the documents file describe the same 13 sources."""

    n_sources: int
    n_documents: int
    sources_without_document: tuple[str, ...]
    documents_without_mitigation: tuple[str, ...]
    malformed_action_ids: tuple[str, ...]

    @property
    def ok(self) -> bool:
        return not (
            self.sources_without_document
            or self.documents_without_mitigation
            or self.malformed_action_ids
        )

    def summary(self) -> str:
        if self.ok:
            return (
                f"bibliography: {self.n_sources} sources match {self.n_documents} "
                "documents both ways; every Action ID is A<number>_<Action Source>"
            )
        parts = []
        if self.sources_without_document:
            parts.append(f"sources with no document: {list(self.sources_without_document)}")
        if self.documents_without_mitigation:
            parts.append(f"documents with no mitigation: {list(self.documents_without_mitigation)}")
        if self.malformed_action_ids:
            shown = list(self.malformed_action_ids[:5])
            parts.append(
                f"{len(self.malformed_action_ids)} Action ID(s) not A<number>_<Action Source>: {shown}"
            )
        return "bibliography: " + "; ".join(parts)


def check_bibliography(
    mitigations: pd.DataFrame, documents: pd.DataFrame
) -> BibliographyCheck:
    """Verify the only link the two files do have: mitigation -> source document."""
    sources = set(mitigations[SOURCE_COLUMN])
    refs = set(documents[SHORT_REF_COLUMN])

    malformed = []
    for action_id, source in zip(mitigations[ACTION_ID_COLUMN], mitigations[SOURCE_COLUMN]):
        match = _ACTION_ID_RE.match(str(action_id))
        if match is None or match.group("source") != source:
            malformed.append(str(action_id))

    return BibliographyCheck(
        n_sources=len(sources),
        n_documents=len(refs),
        sources_without_document=tuple(sorted(sources - refs)),
        documents_without_mitigation=tuple(sorted(refs - sources)),
        malformed_action_ids=tuple(malformed),
    )


def load_mitigations(
    mitigations_path: Path | str = DEFAULT_MITIGATIONS_PATH,
    taxonomy_path: Path | str | None = DEFAULT_TAXONOMY_PATH,
) -> pd.DataFrame:
    """The mitigations table with the taxonomy name and description joined on.

    Columns added on top of `read_mitigations`: `subcategory_name`,
    `subcategory_description`, `category_name`. The catch-all rows keep empty strings
    there — they are real mitigations with no published definition, not missing rows.
    """
    frame = read_mitigations(mitigations_path)
    if taxonomy_path is None:
        return frame

    described = describe_subcategories(frame["subcategory"], read_taxonomy(taxonomy_path))
    frame["subcategory_name"] = described["name"].to_numpy()
    frame["subcategory_description"] = described["description"].to_numpy()
    frame["category_name"] = described["category_name"].to_numpy()
    return frame


def subcategory_counts(
    mitigations: pd.DataFrame, taxonomy: pd.DataFrame | None = None
) -> pd.DataFrame:
    """One row per subcategory present: category, name, and how many mitigations."""
    counts = mitigations["subcategory"].value_counts().rename("n_mitigations")
    table = describe_subcategories(counts.index, taxonomy).copy()
    table["n_mitigations"] = counts.to_numpy()
    # the label from the CSV is what a catch-all row has instead of a taxonomy name
    labels = mitigations.drop_duplicates("subcategory").set_index("subcategory")
    fallback = labels["subcategory_label"].reindex(table.index).fillna("")
    table["name"] = table["name"].where(table["name"] != "", fallback)
    table["category"] = [code.split(".")[0] for code in table.index]
    return table[["category", "name", "n_mitigations"]].sort_index()


def source_counts(mitigations: pd.DataFrame) -> pd.Series:
    """How many mitigations each source document contributes, largest first."""
    return (
        mitigations[SOURCE_COLUMN]
        .value_counts()
        .rename("n_mitigations")
        .rename_axis("source")
    )
