"""Command-line interface for the SQL Analytics Lab.

Usage (from the repository root)::

    python -m sql_lab build           # generate CSVs + (re)build e-commerce.db
    python -m sql_lab list            # print the numbered query catalogue
    python -m sql_lab run 7           # run a single query
    python -m sql_lab run all         # run every query
"""
from __future__ import annotations

import argparse
import re
import sqlite3
import sys
from pathlib import Path

from .build_db import DEFAULT_DATA_DIR, DEFAULT_DB_PATH, REPO_ROOT, build_db
from .generate_data import generate_dataset

SQL_DIR = REPO_ROOT / "sql"
_QUERY_FILE_RE = re.compile(r"^(\d{2})_[a-z0-9_]+\.sql$")


def discover_queries(sql_dir: Path = SQL_DIR) -> list[tuple[int, Path, str]]:
    """Return ``(number, path, business_question)`` for every ``NN_*.sql`` file.

    The business question is taken from the file's first line, which must be a
    ``--`` comment.
    """
    queries: list[tuple[int, Path, str]] = []
    for path in sorted(Path(sql_dir).glob("*.sql")):
        if path.name == "schema.sql":
            continue
        match = _QUERY_FILE_RE.match(path.name)
        if not match:
            continue
        first_line = path.read_text(encoding="utf-8").splitlines()[0]
        question = first_line.lstrip("- ").strip()
        queries.append((int(match.group(1)), path, question))
    queries.sort(key=lambda q: q[0])
    return queries


def _render_table(columns: list[str], rows: list[tuple]) -> str:
    """Format rows as a plain-text table with a header separator."""
    str_rows = [["" if v is None else str(v) for v in row] for row in rows]
    widths = [len(c) for c in columns]
    for row in str_rows:
        for i, cell in enumerate(row):
            widths[i] = max(widths[i], len(cell))
    header = " | ".join(c.ljust(widths[i]) for i, c in enumerate(columns))
    sep = "-+-".join("-" * w for w in widths)
    body = [" | ".join(cell.ljust(widths[i]) for i, cell in enumerate(row)) for row in str_rows]
    return "\n".join([header, sep, *body])


def run_query(db_path: Path, number: int) -> int | None:
    """Execute query ``number`` and print its result table.

    Returns the number of rows returned, or ``None`` if the query number does
    not exist.
    """
    matches = [(n, path, q) for n, path, q in discover_queries() if n == number]
    if not matches:
        print(f"No query numbered {number:02d}. Use 'list' to see available queries.")
        return None
    _, path, question = matches[0]
    sql = path.read_text(encoding="utf-8")
    print(f"\n[{number:02d}] {path.name}")
    print(f"Q: {question}")
    conn = sqlite3.connect(db_path)
    try:
        cur = conn.execute(sql)
        columns = [d[0] for d in cur.description] if cur.description else []
        rows = cur.fetchall() if columns else []
    finally:
        conn.close()
    if columns:
        print(_render_table(columns, rows))
    print(f"({len(rows)} row{'s' if len(rows) != 1 else ''})")
    return len(rows)


def cmd_build(_args: argparse.Namespace) -> int:
    """Generate the CSVs, then rebuild the SQLite database from scratch."""
    print("Generating synthetic dataset (seed fixed)...")
    counts = generate_dataset(DEFAULT_DATA_DIR)
    for name, n in counts.items():
        print(f"  {name:<14} {n:>7,} rows -> data/{name}.csv")
    print("Building star schema...")
    table_counts = build_db()
    for name, n in table_counts.items():
        print(f"  {name:<16} {n:>7,} rows")
    print(f"Done: {DEFAULT_DB_PATH}")
    return 0


def cmd_list(_args: argparse.Namespace) -> int:
    """Print the numbered query catalogue."""
    print(f"{'No.':<4} {'File':<32} Business question")
    print("-" * 100)
    for number, path, question in discover_queries():
        print(f"{number:<4} {path.name:<32} {question}")
    return 0


def cmd_run(args: argparse.Namespace) -> int:
    """Run one query (by number) or all of them."""
    db_path = Path(args.db)
    if not db_path.exists():
        print(f"{db_path} not found. Run 'python -m sql_lab build' first.")
        return 1
    if args.query == "all":
        for number, _, _ in discover_queries():
            run_query(db_path, number)
        return 0
    try:
        number = int(args.query)
    except ValueError:
        print(f"Invalid query selector {args.query!r}: use a number or 'all'.")
        return 1
    run_query(db_path, number)
    return 0


def main(argv: list[str] | None = None) -> int:
    """Entry point for ``python -m sql_lab``."""
    parser = argparse.ArgumentParser(
        prog="python -m sql_lab",
        description="Build and query the SQL Analytics Lab retail star schema.",
    )
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("build", help="generate CSVs and rebuild e-commerce.db")
    sub.add_parser("list", help="print the numbered query catalogue")
    run_parser = sub.add_parser("run", help="run a query by number, or 'all'")
    run_parser.add_argument("query", help="query number (1-15) or 'all'")
    run_parser.add_argument(
        "--db", type=Path, default=DEFAULT_DB_PATH,
        help="path to the SQLite database (default: e-commerce.db in the repo root)",
    )

    args = parser.parse_args(argv)
    if args.command == "build":
        return cmd_build(args)
    if args.command == "list":
        return cmd_list(args)
    if args.command == "run":
        return cmd_run(args)
    parser.error(f"unknown command {args.command}")  # pragma: no cover
    return 2  # pragma: no cover


if __name__ == "__main__":
    sys.exit(main())
