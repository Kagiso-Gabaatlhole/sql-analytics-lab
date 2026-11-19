"""Golden-value tests for the analytical queries.

Every constant here was measured by running this repository's own code
(``python -m sql_lab build`` + the queries in ``sql/``) against the
seed-42 synthetic dataset. If the generator or schema changes, these
tests fail loudly — which is the point.
"""
from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from sql_lab.__main__ import discover_queries

# --- Golden values measured from the seed-42 dataset --------------------------

TOTAL_REVENUE = 48813951.48
TOTAL_PROFIT = 15895921.72
TOTAL_QUANTITY = 79088
TOTAL_ORDER_LINES = 38665
DISTINCT_ORDERS = 20230
ORDERING_CUSTOMERS = 777  # 800 customers exist; 23 never place an order

TOP_PRODUCT = ("P006", "Smart Watch (Premium)", "Electronics", 4675167.21)
TOP_CATEGORY = ("Electronics", 25361102.77)
TOP_PROVINCE = ("Gauteng", 12283414.54)
TOP_CUSTOMER = ("C0543", "Palesa Molefe", 157526.21)

Q04_PASSING_CATEGORIES = [
    "Electronics",
    "Sports & Outdoors",
    "Home & Kitchen",
    "Clothing",
    "Toys & Games",
]

RFM_SEGMENT_COUNTS = {
    "At Risk": 49,
    "Big Spenders": 99,
    "Champions": 101,
    "Hibernating": 206,
    "Loyal": 96,
    "Needs Attention": 134,
    "New & Promising": 92,
}

Q07_ELECTRONICS_TOP3 = [("P006", 1), ("P007", 2), ("P004", 3)]
Q11_ENTITY_COUNTS = {"customer": 23, "product": 5}


SQL_DIR = Path(__file__).resolve().parents[1] / "sql"


def _run(db_path: Path, filename: str) -> list[tuple]:
    """Execute one of the shipped SQL files and return all rows."""
    sql_path = SQL_DIR / filename
    conn = sqlite3.connect(db_path)
    try:
        return conn.execute(sql_path.read_text(encoding="utf-8")).fetchall()
    finally:
        conn.close()


def _scalar(db_path: Path, sql: str):
    conn = sqlite3.connect(db_path)
    try:
        return conn.execute(sql).fetchone()[0]
    finally:
        conn.close()


# --- Dataset-level golden values ----------------------------------------------


def test_total_revenue(db_path: Path) -> None:
    assert _scalar(db_path, "SELECT ROUND(SUM(line_revenue), 2) FROM fact_order_line") == TOTAL_REVENUE


def test_total_profit(db_path: Path) -> None:
    assert _scalar(db_path, "SELECT ROUND(SUM(line_profit), 2) FROM fact_order_line") == TOTAL_PROFIT


def test_order_and_line_counts(db_path: Path) -> None:
    assert _scalar(db_path, "SELECT COUNT(*) FROM fact_order_line") == TOTAL_ORDER_LINES
    assert _scalar(db_path, "SELECT COUNT(DISTINCT order_id) FROM fact_order_line") == DISTINCT_ORDERS
    assert _scalar(db_path, "SELECT SUM(quantity) FROM fact_order_line") == TOTAL_QUANTITY
    assert _scalar(db_path, "SELECT COUNT(DISTINCT customer_id) FROM fact_order_line") == ORDERING_CUSTOMERS


def test_top_product_category_and_province(db_path: Path) -> None:
    top_product = _run(db_path, "03_top_products.sql")[0]
    assert top_product[:3] == TOP_PRODUCT[:3]
    assert top_product[4] == pytest.approx(TOP_PRODUCT[3])

    category = _scalar(
        db_path,
        "SELECT p.category FROM fact_order_line f JOIN dim_product p ON p.product_id = f.product_id"
        " GROUP BY p.category ORDER BY SUM(f.line_revenue) DESC, p.category LIMIT 1",
    )
    assert category == TOP_CATEGORY[0]

    province = _scalar(
        db_path,
        "SELECT c.province FROM fact_order_line f JOIN dim_customer c ON c.customer_id = f.customer_id"
        " GROUP BY c.province ORDER BY SUM(f.line_revenue) DESC, c.province LIMIT 1",
    )
    assert province == TOP_PROVINCE[0]


def test_top_customer(db_path: Path) -> None:
    row = _run(db_path, "14_top_customers.sql")[0]
    assert row[0] == TOP_CUSTOMER[0]
    assert row[1] == TOP_CUSTOMER[1]
    assert row[6] == pytest.approx(TOP_CUSTOMER[2])


# --- Per-query behaviour -------------------------------------------------------


def test_q01_returns_18_months_desc_by_revenue(db_path: Path) -> None:
    rows = _run(db_path, "01_monthly_revenue.sql")
    assert len(rows) == 18
    revenues = [r[5] for r in rows]
    assert revenues == sorted(revenues, reverse=True)
    assert sum(revenues) == pytest.approx(TOTAL_REVENUE)


def test_q02_revenue_shares_sum_to_100(db_path: Path) -> None:
    rows = _run(db_path, "02_revenue_by_province.sql")
    assert len(rows) == 9  # the nine South African provinces
    assert sum(r[3] for r in rows) == pytest.approx(100.0, abs=0.05)
    assert rows[0][0] == TOP_PROVINCE[0]


def test_q04_having_filters_categories(db_path: Path) -> None:
    rows = _run(db_path, "04_category_having_filter.sql")
    assert [r[0] for r in rows] == Q04_PASSING_CATEGORIES


def test_q05_running_revenue_ends_at_total(db_path: Path) -> None:
    rows = _run(db_path, "05_running_revenue.sql")
    assert len(rows) == 18
    # Monotonically increasing, ending exactly at the dataset total.
    running = [r[2] for r in rows]
    assert running == sorted(running)
    assert running[-1] == pytest.approx(TOTAL_REVENUE)


def test_q06_mom_growth_values(db_path: Path) -> None:
    rows = _run(db_path, "06_mom_growth.sql")
    assert len(rows) == 18
    assert rows[0][3] is None  # first month has no prior month to compare against
    by_month = {r[0]: r[3] for r in rows}
    assert by_month["2025-03"] == pytest.approx(30.62)
    assert by_month["2024-02"] == pytest.approx(-11.21)


def test_q07_rank_within_category(db_path: Path) -> None:
    rows = _run(db_path, "07_rank_products_per_category.sql")
    electronics = [(r[1], r[4]) for r in rows if r[0] == "Electronics"]
    assert electronics == Q07_ELECTRONICS_TOP3
    # Every category contributes at most three products.
    per_category: dict[str, int] = {}
    for row in rows:
        per_category[row[0]] = per_category.get(row[0], 0) + 1
    assert all(n <= 3 for n in per_category.values())


def test_q08_two_categories_per_province(db_path: Path) -> None:
    rows = _run(db_path, "08_top_categories_per_province.sql")
    assert len(rows) == 18  # 9 provinces x top-2 categories
    assert {r[3] for r in rows} == {1, 2}


def test_q09_cohort_month_zero_is_cohort_size(db_path: Path) -> None:
    rows = _run(db_path, "09_cohort_retention.sql")
    assert rows
    # At month 0 every cohort member is active by definition, so the counts
    # across cohorts must sum to the number of ordering customers.
    month_zero_total = sum(r[2] for r in rows if r[1] == 0)
    assert month_zero_total == ORDERING_CUSTOMERS


def test_q10_rfm_segment_counts(db_path: Path) -> None:
    rows = _run(db_path, "10_rfm_segments.sql")
    counts = {r[0]: r[1] for r in rows}
    assert counts == RFM_SEGMENT_COUNTS
    assert sum(counts.values()) == ORDERING_CUSTOMERS


def test_q11_never_ordered_includes_reserved_entities(db_path: Path) -> None:
    rows = _run(db_path, "11_never_ordered.sql")
    counts: dict[str, int] = {}
    for entity_type, entity_id, *_rest, revenue in rows:
        counts[entity_type] = counts.get(entity_type, 0) + 1
        assert revenue == 0.0
    assert counts == Q11_ENTITY_COUNTS
    ids = {r[1] for r in rows}
    # The generator guarantees these five customers and five products are dormant.
    assert {f"C{i:04d}" for i in range(796, 801)} <= ids
    assert {f"P{i:03d}" for i in range(56, 61)} <= ids


def test_q12_weekday_rows(db_path: Path) -> None:
    rows = _run(db_path, "12_weekday_patterns.sql")
    assert len(rows) == 7
    assert [r[2] for r in rows] == list(range(7))


def test_q13_discount_revenue_split(db_path: Path) -> None:
    rows = _run(db_path, "13_discount_analysis.sql")
    assert len(rows) == 8
    for _cat, _pct, _avg, discounted, full_price in rows:
        assert discounted + full_price > 0


def test_q15_moving_average_final_row(db_path: Path) -> None:
    rows = _run(db_path, "15_moving_average_view.sql")
    assert len(rows) == 18
    # The final 3-month moving average covers 2025-04..2025-06.
    expected = (2739524.78 + 3133398.81 + 3216719.43) / 3
    assert rows[-1][4] == pytest.approx(round(expected, 2))


# --- Seasonality and view sanity ----------------------------------------------


def test_december_2024_is_peak_month(db_path: Path) -> None:
    peak = _scalar(
        db_path,
        "SELECT year_month FROM v_monthly_revenue ORDER BY revenue DESC LIMIT 1",
    )
    assert peak == "2024-12"


def test_v_monthly_revenue_agrees_with_fact_table(db_path: Path) -> None:
    view_total = _scalar(db_path, "SELECT ROUND(SUM(revenue), 2) FROM v_monthly_revenue")
    assert view_total == TOTAL_REVENUE


def test_v_customer_rfm_covers_all_ordering_customers(db_path: Path) -> None:
    assert _scalar(db_path, "SELECT COUNT(*) FROM v_customer_rfm") == ORDERING_CUSTOMERS


# --- Window functions on a controlled fixture ----------------------------------


def test_window_functions_on_fixture() -> None:
    """Running sums, ranks and LAG behave as expected on a tiny hand-built table."""
    conn = sqlite3.connect(":memory:")
    conn.executescript(
        """
        CREATE TABLE sales (region TEXT, month TEXT, revenue REAL);
        INSERT INTO sales VALUES
            ('North', '2024-01', 100),
            ('North', '2024-02', 150),
            ('North', '2024-03',  50),
            ('South', '2024-01', 200),
            ('South', '2024-02',  80),
            ('South', '2024-03', 120);
        """
    )
    rows = conn.execute(
        """
        SELECT region, month, revenue,
               SUM(revenue) OVER (PARTITION BY region ORDER BY month)              AS running,
               ROW_NUMBER() OVER (PARTITION BY region ORDER BY revenue DESC)       AS rn,
               LAG(revenue) OVER (PARTITION BY region ORDER BY month)              AS prev
        FROM sales
        ORDER BY region, month
        """
    ).fetchall()
    conn.close()
    assert rows == [
        ("North", "2024-01", 100.0, 100.0, 2, None),
        ("North", "2024-02", 150.0, 250.0, 1, 100.0),
        ("North", "2024-03", 50.0, 300.0, 3, 150.0),
        ("South", "2024-01", 200.0, 200.0, 1, None),
        ("South", "2024-02", 80.0, 280.0, 3, 200.0),
        ("South", "2024-03", 120.0, 400.0, 2, 80.0),
    ]


# --- Every shipped query must execute cleanly ----------------------------------


def test_all_shipped_queries_execute(db_path: Path) -> None:
    queries = discover_queries()
    assert len(queries) == 15
    conn = sqlite3.connect(db_path)
    try:
        for number, path, _question in queries:
            sql = path.read_text(encoding="utf-8")
            cur = conn.execute(sql)
            rows = cur.fetchall()
            assert rows, f"query {number:02d} ({path.name}) returned no rows"
    finally:
        conn.close()
