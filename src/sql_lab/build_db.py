"""Build the SQLite star schema from the generated CSV files.

``build_db`` is idempotent: the database file is deleted and recreated from
scratch on every run, so the result only ever depends on the CSVs (which in
turn only depend on the generator's seed).
"""
from __future__ import annotations

import csv
import sqlite3
from datetime import date, timedelta
from pathlib import Path

#: Repository root (three levels up from this file: src/sql_lab/build_db.py).
REPO_ROOT = Path(__file__).resolve().parents[2]

#: Default locations relative to the repository root.
DEFAULT_DATA_DIR = REPO_ROOT / "data"
DEFAULT_DB_PATH = REPO_ROOT / "e-commerce.db"
SCHEMA_PATH = REPO_ROOT / "sql" / "schema.sql"


def _read_csv(path: Path) -> list[dict[str, str]]:
    """Read a UTF-8 CSV into a list of dictionaries keyed by column name."""
    with path.open("r", encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


def load_dimensions(conn: sqlite3.Connection, data_dir: Path) -> dict[str, int]:
    """Load the three dimension tables from CSV and return row counts."""
    customers = _read_csv(data_dir / "customers.csv")
    products = _read_csv(data_dir / "products.csv")

    conn.executemany(
        "INSERT INTO dim_customer (customer_id, customer_name, province, signup_date)"
        " VALUES (?, ?, ?, ?)",
        [(c["customer_id"], c["customer_name"], c["province"], c["signup_date"]) for c in customers],
    )
    conn.executemany(
        "INSERT INTO dim_product (product_id, product_name, category, unit_price, unit_cost)"
        " VALUES (?, ?, ?, ?, ?)",
        [
            (p["product_id"], p["product_name"], p["category"], float(p["unit_price"]), float(p["unit_cost"]))
            for p in products
        ],
    )

    # Conform a full calendar (2023-2025) into dim_order_date.
    date_rows: list[tuple[str, int, int, int, int, str, int]] = []
    day = date(2023, 1, 1)
    end = date(2025, 12, 31)
    month_names = [
        "January", "February", "March", "April", "May", "June",
        "July", "August", "September", "October", "November", "December",
    ]
    while day <= end:
        date_rows.append((
            day.isoformat(), day.year, day.month, day.day, day.isocalendar()[1],
            month_names[day.month - 1], 1 if day.weekday() >= 5 else 0,
        ))
        day += timedelta(days=1)
    conn.executemany(
        "INSERT INTO dim_order_date (date_key, year, month, day_of_month, iso_week,"
        " month_name, is_weekend) VALUES (?, ?, ?, ?, ?, ?, ?)",
        date_rows,
    )
    return {"dim_customer": len(customers), "dim_product": len(products), "dim_order_date": len(date_rows)}


def load_facts(conn: sqlite3.Connection, data_dir: Path) -> dict[str, int]:
    """Derive and load ``fact_order_line`` from the staging order CSVs."""
    orders = _read_csv(data_dir / "orders.csv")
    lines = _read_csv(data_dir / "order_lines.csv")
    order_lookup = {o["order_id"]: o for o in orders}

    fact_rows = []
    for line in lines:
        order = order_lookup[line["order_id"]]
        fact_rows.append((
            line["line_id"], line["order_id"], order["order_date"], order["customer_id"],
            line["product_id"], int(line["quantity"]), float(line["unit_price"]),
            float(line["discount_pct"]), float(line["discount_amount"]),
            float(line["line_revenue"]), float(line["line_profit"]),
        ))
    conn.executemany(
        "INSERT INTO fact_order_line (line_id, order_id, date_key, customer_id, product_id,"
        " quantity, unit_price, discount_pct, discount_amount, line_revenue, line_profit)"
        " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        fact_rows,
    )
    return {"staging_orders": len(orders), "fact_order_line": len(fact_rows)}


def build_db(
    db_path: Path = DEFAULT_DB_PATH,
    data_dir: Path = DEFAULT_DATA_DIR,
    schema_path: Path = SCHEMA_PATH,
) -> dict[str, int]:
    """(Re)create the star schema at ``db_path`` from the CSVs in ``data_dir``.

    Any existing database file is deleted first, making the build idempotent.
    Returns a dictionary of table name -> loaded row count.
    """
    db_path = Path(db_path)
    data_dir = Path(data_dir)
    if db_path.exists():
        db_path.unlink()

    conn = sqlite3.connect(db_path)
    try:
        conn.executescript(Path(schema_path).read_text(encoding="utf-8"))
        counts = {}
        counts.update(load_dimensions(conn, data_dir))
        counts.update(load_facts(conn, data_dir))
        violations = conn.execute("PRAGMA foreign_key_check").fetchall()
        if violations:
            raise RuntimeError(f"foreign key violations: {violations}")
        conn.commit()
    finally:
        conn.close()
    return counts
