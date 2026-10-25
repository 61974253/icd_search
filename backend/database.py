
import sqlite3
import re
import sys
from pathlib import Path
from difflib import get_close_matches
from functools import lru_cache


# ==================================================
# DATABASE PATH
# ==================================================

if getattr(sys, "frozen", False):
    ROOT = Path(sys._MEIPASS)
else:
    ROOT = Path(__file__).resolve().parent.parent

DB_PATH = ROOT / "icd.db"


# ==================================================
# ABBREVIATIONS
# ==================================================

ABBREVIATIONS = {
    "HTN": ["hypertension", "hypertensive"],
    "CKD": ["chronic kidney disease", "renal disease"],
    "DM": ["diabetes mellitus", "diabetic"],
    "T2DM": ["type 2 diabetes mellitus"],
    "DM2": ["type 2 diabetes mellitus"],
    "COPD": ["chronic obstructive pulmonary disease"],
    "CHF": ["congestive heart failure", "heart failure"],
    "CAD": ["coronary artery disease"],
    "UTI": ["urinary tract infection"],
    "AKI": ["acute kidney injury"],
    "ESRD": ["end stage renal disease"],
    "HLD": ["hyperlipidemia", "high cholesterol"],
    "CVA": ["cerebrovascular accident", "stroke"],
    "GERD": ["gastroesophageal reflux disease"],
    "AF": ["atrial fibrillation"],
    "MI": ["myocardial infarction"],
}


# ==================================================
# HELPER FUNCTIONS
# ==================================================

def normalize_code(value):
    return re.sub(r"[^A-Z0-9]", "", str(value or "").upper())


def words(value):
    return re.findall(r"[a-z0-9]+", str(value or "").lower())


def get_connection():
    """Open the packaged SQLite database safely."""
    if not DB_PATH.is_file():
        raise FileNotFoundError(
            f"ICD database not found: {DB_PATH}"
        )

    connection = sqlite3.connect(str(DB_PATH))
    connection.row_factory = sqlite3.Row
    return connection


# ==================================================
# LOAD DIAGNOSES VOCABULARY
# ==================================================

@lru_cache(maxsize=1)
def load_diagnoses():
    """Load diagnosis descriptions once for typo matching."""
    connection = get_connection()

    try:
        rows = connection.execute(
            "SELECT code, description FROM diagnoses"
        ).fetchall()

        vocabulary = set()

        for code, description in rows:
            vocabulary.update(words(description))

        return rows, sorted(vocabulary)

    finally:
        connection.close()


# ==================================================
# SPELLING CORRECTION
# ==================================================

def correct_word(word, vocabulary):
    """Correct likely spelling mistakes."""
    if len(word) < 4 or word in vocabulary:
        return word

    matches = get_close_matches(
        word,
        vocabulary,
        n=1,
        cutoff=0.78
    )

    return matches[0] if matches else word


def expand_term(term, vocabulary):
    upper = term.upper()

    if upper in ABBREVIATIONS:
        return ABBREVIATIONS[upper]

    corrected = correct_word(term.lower(), vocabulary)

    return list(dict.fromkeys([
        term.lower(),
        corrected
    ]))


# ==================================================
# SEARCH DIAGNOSES
# ==================================================

def search_diagnoses(query: str, limit: int = 5000):
    query = str(query or "").strip()

    if not query:
        return []

    try:
        limit = max(1, min(int(limit), 5000))
    except (TypeError, ValueError):
        limit = 5000

    connection = get_connection()

    try:
        results = {}

        # ------------------------------------------
        # 1. ICD CODE SEARCH
        # ------------------------------------------

        normalized_query = normalize_code(query)

        if normalized_query:
            code_rows = connection.execute(
                """
                SELECT
                    code AS id,
                    description AS document
                FROM diagnoses
                WHERE REPLACE(UPPER(code), '.', '') LIKE ?
                ORDER BY
                    CASE
                        WHEN REPLACE(UPPER(code), '.', '') = ?
                        THEN 0
                        ELSE 1
                    END,
                    code
                LIMIT ?
                """,
                (
                    f"{normalized_query}%",
                    normalized_query,
                    limit,
                ),
            ).fetchall()

            for row in code_rows:
                results[row["id"]] = dict(row)

        # ------------------------------------------
        # 2. DESCRIPTION SEARCH
        # ------------------------------------------

        _, vocabulary = load_diagnoses()

        terms = words(query)
        conditions = []
        params = []

        for term in terms:
            alternatives = expand_term(term, vocabulary)
            term_conditions = []

            for alternative in alternatives:
                term_conditions.append(
                    "description LIKE ? COLLATE NOCASE"
                )
                params.append(f"%{alternative}%")

            conditions.append(
                "(" + " OR ".join(term_conditions) + ")"
            )

        # Every typed word must match, in any order.
        if conditions:
            sql = """
                SELECT
                    code AS id,
                    description AS document
                FROM diagnoses
                WHERE
            """ + " AND ".join(conditions) + """
                ORDER BY code
                LIMIT ?
            """

            params.append(limit)

            rows = connection.execute(
                sql,
                params
            ).fetchall()

            for row in rows:
                results[row["id"]] = dict(row)

        return list(results.values())[:limit]

    finally:
        connection.close()


# ==================================================
# DATABASE VALIDATION
# ==================================================

def validate_database():
    """Check database availability and required columns."""
    connection = get_connection()

    try:
        columns = connection.execute(
            "PRAGMA table_info(diagnoses)"
        ).fetchall()

        column_names = {
            row["name"] for row in columns
        }

        required_columns = {"code", "description"}
        missing_columns = required_columns - column_names

        if not columns:
            raise RuntimeError(
                "The diagnoses table does not exist in icd.db."
            )

        if missing_columns:
            raise RuntimeError(
                "Missing diagnoses columns: "
                + ", ".join(sorted(missing_columns))
            )

        return True

    finally:
        connection.close()
