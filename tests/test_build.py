"""Tests for the build pipeline: idempotence, determinism and database shape."""
from __future__ import annotations

import hashlib
import sqlite3
from pathlib import Path

from sql_lab.__main__ import main
from sql_lab.build_db import DEFAULT_DATA_DIR, build_db
from sql_lab.generate_data import generate_dataset

REPO_ROOT = Path(__file__).resolve().parents[1]

#: Golden row counts from the committed seed-42 CSVs.
EXPECTED_COUNTS = {
    "dim_customer": 800,
    "dim_product": 60,
    "dim_order_date": 1096,  # full 2023-2025 calendar
    "fact_order_line": 38665,
}

CSV_NAMES = ["customers.csv", "products.csv", "orders.csv", "order_lines.csv"]


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _total_revenue(db_path: Path) -> float:
    conn = sqlite3.connect(db_path)
    try:
        return conn.execute("SELECT ROUND(SUM(line_revenue), 2) FROM fact_order_line").fetchone()[0]
    finally:
        conn.close()


def test_build_reports_expected_row_counts(db_path: Path) -> None:
    """The session-built database matches the committed CSVs' golden counts."""
    conn = sqlite3.connect(db_path)
    try:
        for table, expected in EXPECTED_COUNTS.items():
            actual = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            assert actual == expected, f"{table}: expected {expected}, got {actual}"
        assert conn.execute("PRAGMA foreign_key_check").fetchall() == []
    finally:
        conn.close()


def test_rebuild_is_idempotent(tmp_path: Path) -> None:
    """Two consecutive builds produce identical tables and identical totals."""
    db_a = tmp_path / "a.db"
    db_b = tmp_path / "b.db"
    counts_a = build_db(db_path=db_a)
    counts_b = build_db(db_path=db_b)
    assert counts_a == counts_b
    assert {k: counts_a[k] for k in EXPECTED_COUNTS} == EXPECTED_COUNTS
    assert _total_revenue(db_a) == _total_revenue(db_b)


def test_rebuild_replaces_a_stale_database_file(tmp_path: Path) -> None:
    """A corrupt/pre-existing file at the target path is discarded, not appended to."""
    db_path = tmp_path / "stale.db"
    db_path.write_bytes(b"this is not a sqlite database")
    counts = build_db(db_path=db_path)
    assert counts["fact_order_line"] == EXPECTED_COUNTS["fact_order_line"]
    assert _total_revenue(db_path) == 48813951.48


def test_committed_csvs_are_reproducible_from_the_generator(tmp_path: Path) -> None:
    """Regenerating with the same seed yields byte-identical CSVs to the committed ones."""
    out_dir = tmp_path / "regen"
    generate_dataset(out_dir)
    for name in CSV_NAMES:
        assert _sha256(out_dir / name) == _sha256(DEFAULT_DATA_DIR / name), name


def test_cli_list_prints_full_catalogue(capsys) -> None:
    assert main(["list"]) == 0
    output = capsys.readouterr().out
    lines = [ln for ln in output.splitlines() if ".sql" in ln]
    assert len(lines) == 15


def test_cli_run_single_query(db_path: Path, capsys) -> None:
    assert main(["run", "1", "--db", str(db_path)]) == 0
    output = capsys.readouterr().out
    assert "(18 rows)" in output
    assert "year_month" in output


def test_cli_run_rejects_bad_selector(db_path: Path, capsys) -> None:
    assert main(["run", "banana", "--db", str(db_path)]) == 1
    assert "Invalid query selector" in capsys.readouterr().out


def test_cli_run_reports_missing_database(tmp_path: Path, capsys) -> None:
    missing = tmp_path / "nope.db"
    assert main(["run", "1", "--db", str(missing)]) == 1
    assert "not found" in capsys.readouterr().out
