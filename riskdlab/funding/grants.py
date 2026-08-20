"""The grant snapshots read into one table.

Each funder publishes something different — Coefficient Giving a grant list with a focus
area and no description, EA Funds a one-line description per grant, Manifund a full
project page with cause tags and transactions, SFF a recommendation table whose purpose
is almost always "General support", FLI a programme page with a paragraph per grant —
so the common table keeps only what all of them can
fill: who gave, to whom, when, how much, and what text there is to classify on. What a
source cannot fill is empty, not guessed.

`amount_usd` means different things per source and the `amount_kind` column says which:
Coefficient and EA Funds publish the granted amount, SFF and FLI the recommended amount,
and Manifund the sum of USD transactions into the project (zero for an unfunded proposal).
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

SNAPSHOT_DIR = Path(__file__).resolve().parent.parent.parent / "snapshots" / "funding"
SNAPSHOT_DATE = "2026-08-20"

DEFAULT_COEFFICIENT_PATH = SNAPSHOT_DIR / f"coefficient-grants-{SNAPSHOT_DATE}.csv"
DEFAULT_EAFUNDS_PATH = SNAPSHOT_DIR / f"eafunds-grants-{SNAPSHOT_DATE}.csv"
DEFAULT_MANIFUND_PATH = SNAPSHOT_DIR / f"manifund-projects-{SNAPSHOT_DATE}.csv"
DEFAULT_SFF_PATH = SNAPSHOT_DIR / f"sff-recommendations-{SNAPSHOT_DATE}.csv"
DEFAULT_FLI_PATH = SNAPSHOT_DIR / f"fli-grants-{SNAPSHOT_DATE}.csv"

COLUMNS = [
    "source",
    "grant_id",
    "year",
    "date",
    "funder_program",
    "grantee",
    "title",
    "text",
    "amount_usd",
    "amount_kind",
    "ai_scope",
    "url",
]

#: Coefficient focus areas that are about AI by construction. The GCR fund is mixed
#: (AI, bio, nuclear) and is classified on its titles like everything else.
COEFFICIENT_AI_FOCUS_AREAS = frozenset({"Navigating Transformative AI"})
#: EA Funds funds whose grants are classified; the others do not fund AI risk work.
EAFUNDS_AI_FUNDS = frozenset({"Long-Term Future Fund"})
#: Manifund cause tags that mark a project as AI-risk work.
MANIFUND_AI_CAUSES = frozenset({"tais", "ai-gov"})


def _read(path: Path | str) -> pd.DataFrame:
    return pd.read_csv(path, dtype=str, keep_default_na=False)


def read_coefficient(path: Path | str = DEFAULT_COEFFICIENT_PATH) -> pd.DataFrame:
    raw = _read(path)
    focus = raw["focus_areas"].str.split("; ")
    return pd.DataFrame(
        {
            "source": "coefficient",
            "grant_id": raw["grant_id"],
            "year": pd.to_numeric(raw["award_year"], errors="coerce").astype("Int64"),
            "date": raw["award_date"],
            "funder_program": raw["focus_areas"],
            "grantee": raw["organization"],
            "title": raw["title"],
            # the index carries no description, so the grantee is the main signal
            "text": (raw["organization"] + " — " + raw["title"]).str.strip(" —"),
            "amount_usd": pd.to_numeric(raw["amount_usd"], errors="coerce"),
            "amount_kind": "granted",
            "ai_scope": focus.map(lambda areas: bool(COEFFICIENT_AI_FOCUS_AREAS & set(areas))),
            "url": raw["url"],
        }
    )[COLUMNS]


def read_eafunds(path: Path | str = DEFAULT_EAFUNDS_PATH) -> pd.DataFrame:
    raw = _read(path)
    return pd.DataFrame(
        {
            "source": "eafunds",
            "grant_id": raw["id"],
            "year": pd.to_numeric(raw["year"], errors="coerce").astype("Int64"),
            "date": raw["round"],
            "funder_program": raw["fund"],
            "grantee": raw["grantee"],
            "title": raw["description"],
            "text": (raw["grantee"] + " — " + raw["description"]).str.strip(" —"),
            "amount_usd": pd.to_numeric(raw["amount"], errors="coerce"),
            "amount_kind": "granted",
            "ai_scope": raw["fund"].isin(EAFUNDS_AI_FUNDS),
            "url": "",
        }
    )[COLUMNS]


def read_manifund(path: Path | str = DEFAULT_MANIFUND_PATH) -> pd.DataFrame:
    raw = _read(path)
    causes = raw["causes"].str.split("; ")
    return pd.DataFrame(
        {
            "source": "manifund",
            "grant_id": raw["project_id"],
            "year": pd.to_numeric(raw["created_at"].str[:4], errors="coerce").astype("Int64"),
            "date": raw["created_at"].str[:10],
            "funder_program": raw["stage"],
            "grantee": raw["creator"],
            "title": raw["title"],
            "text": (raw["title"] + "\n" + raw["blurb"] + "\n" + raw["description"]).str.strip(),
            "amount_usd": pd.to_numeric(raw["raised_usd"], errors="coerce"),
            "amount_kind": "raised",
            "ai_scope": causes.map(lambda tags: bool(MANIFUND_AI_CAUSES & set(tags))),
            "url": "https://manifund.org/projects/" + raw["slug"],
        }
    )[COLUMNS]


def read_sff(path: Path | str = DEFAULT_SFF_PATH) -> pd.DataFrame:
    raw = _read(path)
    return pd.DataFrame(
        {
            "source": "sff",
            "grant_id": raw["round"] + "/" + raw.index.astype(str),
            "year": pd.to_numeric(raw["year"], errors="coerce").astype("Int64"),
            "date": raw["round"],
            "funder_program": raw["source"],
            "grantee": raw["organization"],
            "title": raw["purpose"],
            "text": (raw["organization"] + " — " + raw["purpose"]).str.strip(" —"),
            "amount_usd": pd.to_numeric(raw["amount_usd"], errors="coerce"),
            "amount_kind": "recommended",
            # SFF funds AI, bio and other x-risk work from one list; scope is decided
            # per row by the classifier, so nothing is pre-excluded here
            "ai_scope": True,
            "url": "",
        }
    )[COLUMNS]


def read_fli(path: Path | str = DEFAULT_FLI_PATH) -> pd.DataFrame:
    raw = _read(path)
    return pd.DataFrame(
        {
            "source": "fli",
            "grant_id": raw["grant_id"],
            "year": pd.to_numeric(raw["year"], errors="coerce").astype("Int64"),
            "date": raw["year_basis"],
            "funder_program": raw["program"],
            "grantee": raw["grantee"],
            "title": raw["summary"].str.slice(0, 120),
            "text": (raw["grantee"] + " — " + raw["summary"]).str.strip(" —"),
            "amount_usd": pd.to_numeric(raw["amount_usd"], errors="coerce"),
            "amount_kind": "recommended",
            # FLI funds AI, nuclear and other work from the same programmes; like SFF,
            # every row is in scope and the label decides
            "ai_scope": True,
            "url": "https://futureoflife.org/grant-program/" + raw["program"] + "/",
        }
    )[COLUMNS]


def load_grants(
    coefficient_path: Path | str = DEFAULT_COEFFICIENT_PATH,
    eafunds_path: Path | str = DEFAULT_EAFUNDS_PATH,
    manifund_path: Path | str = DEFAULT_MANIFUND_PATH,
    sff_path: Path | str = DEFAULT_SFF_PATH,
    fli_path: Path | str | None = DEFAULT_FLI_PATH,
) -> pd.DataFrame:
    """All sources in one table, `ai_scope` marking the rows the funder itself tags as AI.

    `ai_scope` is the funder's own labelling (focus area, fund, cause tag), not ours; for
    SFF and FLI, which have no such label, every row is in scope and the label decides.
    Grants outside the funder's AI tag can still carry a label — Coefficient's bio and
    GCR funds pay for AI-enabled work — so the money tables count *labelled* grants, not
    `ai_scope` ones.
    """
    frames = [
        read_coefficient(coefficient_path),
        read_eafunds(eafunds_path),
        read_manifund(manifund_path),
        read_sff(sff_path),
    ]
    if fli_path is not None:
        frames.append(read_fli(fli_path))
    return pd.concat(frames, ignore_index=True)


def possible_near_duplicates(
    grants: pd.DataFrame, *, max_days: int = 30
) -> pd.DataFrame:
    """Flag same-source, same-grantee, same-amount records close in time.

    This is an audit signal, not an automatic deduplication rule. Two genuinely
    separate awards can have the same amount, while a duplicated public record can
    have a different title and URL. Callers must keep both rows unless the source or
    grantee confirms that they describe one transfer.
    """
    columns = [
        "source",
        "grantee",
        "amount_usd",
        "days_apart",
        "left_grant_id",
        "right_grant_id",
        "left_date",
        "right_date",
        "left_title",
        "right_title",
    ]
    if max_days < 0:
        raise ValueError("max_days must be non-negative")

    frame = grants.copy()
    frame["parsed_date"] = pd.to_datetime(frame["date"], errors="coerce")
    frame = frame[
        frame["parsed_date"].notna()
        & frame["amount_usd"].notna()
        & frame["amount_usd"].gt(0)
        & frame["grantee"].ne("")
    ].sort_values(["source", "grantee", "amount_usd", "parsed_date"])

    matches: list[dict[str, object]] = []
    keys = ["source", "grantee", "amount_usd"]
    for (source, grantee, amount), group in frame.groupby(keys, sort=False):
        rows = list(group.itertuples(index=False))
        for index, left in enumerate(rows):
            for right in rows[index + 1 :]:
                days = int((right.parsed_date - left.parsed_date).days)
                if days > max_days:
                    break
                matches.append(
                    {
                        "source": source,
                        "grantee": grantee,
                        "amount_usd": float(amount),
                        "days_apart": days,
                        "left_grant_id": left.grant_id,
                        "right_grant_id": right.grant_id,
                        "left_date": left.date,
                        "right_date": right.date,
                        "left_title": left.title,
                        "right_title": right.title,
                    }
                )
    return pd.DataFrame(matches, columns=columns)
