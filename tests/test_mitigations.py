"""Two kinds of test here.

The synthetic ones build miniature CSVs with the same shape as the export — BOM and all —
and pin the traps listed in `snapshots/README.md`: the four catch-all codes, an empty
`Action Definition`, a duplicate `Action ID`, an `Action Source` with no document.

The rest check control numbers on the committed snapshot, which is in git and needs no
download and no network.
"""

from __future__ import annotations

import json

import pandas as pd
import pytest

from riskdlab.mitigations import (
    DEFAULT_TAXONOMY_PATH,
    check_bibliography,
    describe_subcategories,
    load_mitigations,
    read_documents,
    read_mitigations,
    read_taxonomy,
    source_counts,
    split_mitigation_code,
    subcategory_counts,
)

# --- synthetic fixtures -----------------------------------------------------------

MITIGATION_ROWS = [
    # Action ID, Action Name, Action Definition, Action Source, MitigationCode
    ("A0001_Bengio2025", "Audits", "External review.", "Bengio2025", "3.1 Testing & Auditing"),
    ("A0002_Bengio2025", "Red teaming", "", "Bengio2025", "3.1 Testing & Auditing"),
    ("A0003_NIST2024", "Risk register", "A register.", "NIST2024", "1.2 Risk Management"),
    ("A0004_NIST2024", "Odds and ends", "", "NIST2024", "1.X Governance & Oversight Control not otherwise categorized"),
    ("A0005_NIST2024", "Unclassifiable", "Nothing fits.", "NIST2024", "X.X Control not otherwise categorized"),
]

DOCUMENT_ROWS = [
    ("Bengio2025", "1", "International AI Safety Report", "https://example.org/a", "10.0/a"),
    ("NIST2024", "2", "AI RMF", "https://example.org/b", ""),
]


def write_csv(path, header, rows, bom=True):
    """The real export is UTF-8 with a BOM; the fixtures repeat that by default."""
    text = ",".join(header) + "\n"
    for row in rows:
        text += ",".join(f'"{value}"' for value in row) + "\n"
    path.write_text(text, encoding="utf-8-sig" if bom else "utf-8")
    return path


@pytest.fixture
def mitigations_csv(tmp_path):
    header = ["Action ID", "Action Name", "Action Definition", "Action Source", "MitigationCode"]
    return write_csv(tmp_path / "mitigations.csv", header, MITIGATION_ROWS)


@pytest.fixture
def documents_csv(tmp_path):
    header = ["ShortRef", "DocumentID", "Title", "URL", "DOI"]
    return write_csv(tmp_path / "documents.csv", header, DOCUMENT_ROWS)


@pytest.fixture
def taxonomy_json(tmp_path):
    snapshot = {
        "source": "https://example.org/taxonomy",
        "retrieved": "2026-08-20",
        "categories": [
            {
                "code": "1",
                "name": "Governance & Oversight Controls",
                "description": "Structures.",
                "subcategories": [
                    {"code": "1.2", "name": "Risk Management", "description": "Systematic methods.", "examples": "Risk registers"},
                ],
            },
            {
                "code": "3",
                "name": "Operational Process Controls",
                "description": "Processes.",
                "subcategories": [
                    {"code": "3.1", "name": "Testing & Auditing", "description": "Evaluations.", "examples": "Red teaming"},
                ],
            },
        ],
    }
    path = tmp_path / "taxonomy.json"
    path.write_text(json.dumps(snapshot), encoding="utf-8")
    return path


# --- the traps --------------------------------------------------------------------


def test_the_bom_does_not_end_up_in_the_first_column_name(mitigations_csv):
    frame = read_mitigations(mitigations_csv)
    assert list(frame.columns)[0] == "Action ID"
    assert not any(column.startswith("﻿") for column in frame.columns)


@pytest.mark.parametrize(
    "code, expected",
    [
        ("3.1 Testing & Auditing", ("3", "3.1", "Testing & Auditing")),
        ("1.X Governance & Oversight Control not otherwise categorized",
         ("1", "1.X", "Governance & Oversight Control not otherwise categorized")),
        ("X.X Control not otherwise categorized", ("X", "X.X", "Control not otherwise categorized")),
        ("4.6", ("4", "4.6", "")),
    ],
)
def test_split_mitigation_code_accepts_every_bucket(code, expected):
    assert split_mitigation_code(code) == expected


@pytest.mark.parametrize("code", ["", "3", "3.", "Testing & Auditing", "Y.1 Something"])
def test_split_mitigation_code_rejects_what_is_not_a_code(code):
    with pytest.raises(ValueError, match="not a mitigation code"):
        split_mitigation_code(code)


def test_catch_all_rows_survive_and_are_flagged(mitigations_csv):
    frame = read_mitigations(mitigations_csv)
    assert len(frame) == len(MITIGATION_ROWS)  # nothing dropped
    assert frame.set_index("Action ID").loc["A0005_NIST2024", "subcategory"] == "X.X"
    assert frame["uncategorized"].tolist() == [False, False, False, True, True]


def test_an_unreadable_code_is_an_error_naming_the_row(tmp_path):
    header = ["Action ID", "Action Name", "Action Definition", "Action Source", "MitigationCode"]
    rows = [*MITIGATION_ROWS, ("A0006_NIST2024", "Broken", "", "NIST2024", "no code here")]
    path = write_csv(tmp_path / "broken.csv", header, rows)
    with pytest.raises(ValueError, match="A0006_NIST2024"):
        read_mitigations(path)


def test_an_empty_action_definition_is_kept_as_an_empty_string(mitigations_csv):
    frame = read_mitigations(mitigations_csv).set_index("Action ID")
    assert frame.loc["A0002_Bengio2025", "Action Definition"] == ""


def test_a_duplicate_action_id_is_an_error(tmp_path):
    header = ["Action ID", "Action Name", "Action Definition", "Action Source", "MitigationCode"]
    rows = [*MITIGATION_ROWS, MITIGATION_ROWS[0]]
    path = write_csv(tmp_path / "duplicate.csv", header, rows)
    with pytest.raises(ValueError, match="duplicate Action ID"):
        read_mitigations(path)


def test_a_missing_column_is_an_error_not_a_key_error(tmp_path):
    path = write_csv(tmp_path / "thin.csv", ["Action ID"], [("A0001_Bengio2025",)])
    with pytest.raises(ValueError, match="missing column"):
        read_mitigations(path)


# --- the bibliography link --------------------------------------------------------


def test_bibliography_matches_both_ways(mitigations_csv, documents_csv):
    check = check_bibliography(read_mitigations(mitigations_csv), read_documents(documents_csv))
    assert check.ok
    assert check.n_sources == check.n_documents == 2
    assert "both ways" in check.summary()


def test_bibliography_reports_a_source_with_no_document(mitigations_csv, tmp_path):
    documents = write_csv(
        tmp_path / "short.csv",
        ["ShortRef", "DocumentID", "Title", "URL", "DOI"],
        [DOCUMENT_ROWS[0]],
    )
    check = check_bibliography(read_mitigations(mitigations_csv), read_documents(documents))
    assert not check.ok
    assert check.sources_without_document == ("NIST2024",)
    assert "NIST2024" in check.summary()


def test_bibliography_reports_a_document_nothing_cites(mitigations_csv, tmp_path):
    documents = write_csv(
        tmp_path / "long.csv",
        ["ShortRef", "DocumentID", "Title", "URL", "DOI"],
        [*DOCUMENT_ROWS, ("Ghost2026", "3", "Uncited", "https://example.org/c", "")],
    )
    check = check_bibliography(read_mitigations(mitigations_csv), read_documents(documents))
    assert not check.ok
    assert check.documents_without_mitigation == ("Ghost2026",)


def test_bibliography_reports_an_action_id_that_does_not_name_its_source(tmp_path, documents_csv):
    header = ["Action ID", "Action Name", "Action Definition", "Action Source", "MitigationCode"]
    rows = [*MITIGATION_ROWS, ("A0007_Bengio2025", "Mislabelled", "", "NIST2024", "3.1 Testing & Auditing")]
    path = write_csv(tmp_path / "mislabelled.csv", header, rows)
    check = check_bibliography(read_mitigations(path), read_documents(documents_csv))
    assert not check.ok
    assert check.malformed_action_ids == ("A0007_Bengio2025",)


# --- the taxonomy reference -------------------------------------------------------


def test_taxonomy_is_a_lookup_from_code_to_name_and_description(taxonomy_json):
    taxonomy = read_taxonomy(taxonomy_json)
    assert taxonomy.index.name == "subcategory"
    assert taxonomy.loc["3.1", "name"] == "Testing & Auditing"
    assert taxonomy.loc["3.1", "description"] == "Evaluations."
    assert taxonomy.loc["3.1", "category_name"] == "Operational Process Controls"


def test_a_catch_all_code_keeps_its_row_with_an_empty_description(taxonomy_json):
    described = describe_subcategories(["3.1", "X.X"], read_taxonomy(taxonomy_json))
    assert list(described.index) == ["3.1", "X.X"]
    assert described.loc["X.X", "description"] == ""


def test_load_mitigations_joins_the_taxonomy_without_losing_catch_alls(
    mitigations_csv, taxonomy_json
):
    frame = load_mitigations(mitigations_csv, taxonomy_json).set_index("Action ID")
    assert len(frame) == len(MITIGATION_ROWS)
    assert frame.loc["A0001_Bengio2025", "subcategory_name"] == "Testing & Auditing"
    assert frame.loc["A0005_NIST2024", "subcategory_name"] == ""


def test_load_mitigations_can_skip_the_taxonomy(mitigations_csv):
    frame = load_mitigations(mitigations_csv, taxonomy_path=None)
    assert "subcategory_name" not in frame.columns


def test_counts_fall_back_to_the_csv_label_for_a_catch_all(mitigations_csv, taxonomy_json):
    frame = load_mitigations(mitigations_csv, taxonomy_json)
    counts = subcategory_counts(frame, read_taxonomy(taxonomy_json))
    assert counts.loc["3.1", "n_mitigations"] == 2
    assert counts.loc["X.X", "name"] == "Control not otherwise categorized"
    assert counts.loc["X.X", "category"] == "X"


def test_source_counts_are_largest_first(mitigations_csv):
    counts = source_counts(read_mitigations(mitigations_csv))
    assert counts.index.name == "source"
    assert counts.index[0] == "NIST2024"
    assert counts["NIST2024"] == 3


# --- control numbers on the committed snapshot ------------------------------------


@pytest.fixture(scope="module")
def snapshot() -> pd.DataFrame:
    return load_mitigations()


def test_the_snapshot_holds_831_mitigations_with_unique_ids(snapshot):
    assert len(snapshot) == 831
    assert snapshot["Action ID"].nunique() == 831


def test_the_snapshot_holds_13_documents(snapshot):
    documents = read_documents()
    assert len(documents) == 13
    assert documents["ShortRef"].nunique() == 13


def test_the_snapshot_bibliography_closes_both_ways(snapshot):
    assert check_bibliography(snapshot, read_documents()).ok


@pytest.mark.parametrize(
    "code, n", [("3.1", 127), ("1.2", 125), ("3.2", 57), ("3.5", 50), ("4.2", 44)]
)
def test_the_largest_subcategories_keep_their_counts(snapshot, code, n):
    assert int((snapshot["subcategory"] == code).sum()) == n


def test_the_snapshot_has_27_codes_of_which_4_are_catch_alls(snapshot):
    codes = set(snapshot["subcategory"])
    assert len(codes) == 27
    assert {"1.X", "2.X", "3.X", "X.X"} <= codes
    assert int(snapshot["uncategorized"].sum()) == 16


def test_the_11_uncategorised_mitigations_are_still_there(snapshot):
    assert int((snapshot["subcategory"] == "X.X").sum()) == 11


def test_the_taxonomy_snapshot_describes_the_23_named_subcategories(snapshot):
    taxonomy = read_taxonomy()
    assert len(taxonomy) == 23
    assert taxonomy["description"].str.len().gt(0).all()
    named = {code for code in snapshot["subcategory"] if not code.endswith(".X")}
    assert named == set(taxonomy.index)


def test_the_taxonomy_names_agree_with_the_labels_in_the_csv(snapshot):
    taxonomy = read_taxonomy()
    named = snapshot[~snapshot["uncategorized"]]
    labels = named.set_index("subcategory")["subcategory_label"].drop_duplicates()
    assert labels.sort_index().tolist() == taxonomy["name"].sort_index().tolist()


def test_the_taxonomy_snapshot_records_where_it_came_from():
    snapshot = json.loads(DEFAULT_TAXONOMY_PATH.read_text(encoding="utf-8"))
    assert snapshot["source"].startswith("https://")
    assert snapshot["retrieved"]
    assert len(snapshot["source_sha256"]) == 64
