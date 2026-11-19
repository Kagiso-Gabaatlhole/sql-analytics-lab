# SQL Analytics Lab

A SQL and data-modelling portfolio project: a synthetic South African online-retail
dataset (~20,000 orders over 18 months), loaded into a dimensional star schema in
SQLite, with 15 analytical queries, a small CLI, and a pytest suite whose
golden-value assertions are computed from the deterministic seed-42 data. It exists
to demonstrate practical SQL skills — aggregation, joins, window functions, CTEs,
cohort retention and RFM segmentation — in a repository anyone can clone, rebuild
and verify end to end.

## Features

- **Seeded synthetic data generator** — `src/sql_lab/generate_data.py` produces
  customers, products, orders and order lines from a single fixed seed (`SEED=42`).
  Regeneration is byte-for-byte reproducible; no network access anywhere.
- **Star schema** — `sql/schema.sql` defines `dim_customer`, `dim_product`,
  `dim_order_date` and `fact_order_line`, plus two reporting views
  (`v_monthly_revenue`, `v_customer_rfm`).
- **15 analytical queries** — `sql/01_*.sql` … `sql/15_*.sql`, each headed by the
  business question it answers (see the catalogue below).
- **CLI** — `python -m sql_lab build | list | run <n|all>` with plain-text tables.
- **Tested** — 31 pytest tests, including golden values (exact revenue totals,
  known top products, RFM bucket counts) and window-function checks on a
  hand-built fixture table.

## Star schema at a glance

```
 dim_order_date        dim_customer         dim_product
+----------------+   +----------------+   +----------------+
| PK date_key    |   | PK customer_id |   | PK product_id  |
| year / month   |   | customer_name  |   | product_name   |
| month_name     |   | province       |   | category       |
| is_weekend     |   | signup_date    |   | unit_price     |
+----------------+   +----------------+   | unit_cost      |
        ^                    ^            +----------------+
        |                    |                   ^
        |    +--------------------------+        |
        +----| fact_order_line          |--------+
             | (grain: one order line)  |
             +--------------------------+
                  PK  line_id
                  FK  date_key, customer_id, product_id
                  qty unit_price, discount_pct/amount
                  line_revenue, line_profit

Views:  v_monthly_revenue -> revenue, orders, units per month
        v_customer_rfm    -> recency/frequency/monetary + NTILE(4) scores + segment
```

## Quickstart

Requires Python 3.10+ (developed on 3.12, Windows). No network access is needed at
any point; the CSVs in `data/` are committed, and `build` regenerates them
identically from the seed.

```powershell
python -m pip install -e .
python -m sql_lab build
python -m sql_lab run all
```

`build` regenerates `data/*.csv` from the seed and rebuilds `e-commerce.db` from
scratch (idempotent — any existing file is discarded first). `run` executes a
single query by number (`python -m sql_lab run 9`) or all 15 in order.

## Query catalogue

| # | File | Business question | SQL concepts |
|---|------|-------------------|--------------|
| 1 | `sql/01_monthly_revenue.sql` | Which months produced the most revenue? | aggregation, `COUNT(DISTINCT)`, join to date dimension |
| 2 | `sql/02_revenue_by_province.sql` | Which provinces generate the most revenue, and what is each one's share? | multi-table join, `GROUP BY`, window aggregate over groups |
| 3 | `sql/03_top_products.sql` | Which ten products earned the most revenue? | join, `ORDER BY` + `LIMIT` (top-N) |
| 4 | `sql/04_category_having_filter.sql` | Which categories earn plenty *and* attract many customers? | `GROUP BY` + `HAVING` with two conditions |
| 5 | `sql/05_running_revenue.sql` | How did cumulative revenue build up month by month? | CTE, `SUM() OVER (… ROWS UNBOUNDED PRECEDING)` running total |
| 6 | `sql/06_mom_growth.sql` | What was the month-on-month % change in revenue? | CTE, `LAG()` window function, percent change |
| 7 | `sql/07_rank_products_per_category.sql` | Which products rank top three in each category? | `ROW_NUMBER() OVER (PARTITION BY …)`, rank-within-group |
| 8 | `sql/08_top_categories_per_province.sql` | Which are the top two categories in every province? | `DENSE_RANK()` per partition (top-N per group), three-way join |
| 9 | `sql/09_cohort_retention.sql` | How many customers from each cohort were still ordering months later? | chained CTEs, cohort/month index arithmetic on date strings |
| 10 | `sql/10_rfm_segments.sql` | How many customers fall into each RFM segment? | view over CTE + `NTILE(4)` quartile scoring, `CASE` segmentation |
| 11 | `sql/11_never_ordered.sql` | Which customers/products never contributed revenue? | `LEFT JOIN` anti-join, `COALESCE`, `HAVING … = 0` NULL handling |
| 12 | `sql/12_weekday_patterns.sql` | How do volume and revenue differ by weekday? | `strftime()` date functions, `GROUP BY` on derived columns |
| 13 | `sql/13_discount_analysis.sql` | How heavy is discounting per category? | `CASE` inside aggregates, conditional sums |
| 14 | `sql/14_top_customers.sql` | Who are the ten highest-spending customers? | aggregation + `MIN`/`MAX` dates, top-N |
| 15 | `sql/15_moving_average_view.sql` | What does a 3-month moving average of revenue look like? | view-based report, `AVG() OVER (… ROWS 2 PRECEDING)` |

## Data provenance

**All data in this repository is synthetic.** It was generated locally by
`src/sql_lab/generate_data.py` from a single fixed random seed (`SEED=42`) and
does not describe any real company, customer or transaction. There is no network
fetch at build time or runtime: the CSVs in `data/` are committed to the repo, and
re-running the generator reproduces them byte-for-byte (this is asserted by
`tests/test_build.py::test_committed_csvs_are_reproducible_from_the_generator`).

Dataset shape (as produced by the seed):

| File | Rows | Contents |
|------|------|----------|
| `data/customers.csv` | 800 | customer id, name, one of the 9 real SA provinces, signup date |
| `data/products.csv` | 60 | product id, name, 1 of 8 categories, unit price/cost in ZAR |
| `data/orders.csv` | 20,230 | order header: order id, customer id, order date (2024-01 → 2025-06) |
| `data/order_lines.csv` | 38,665 | line facts: quantity, unit price, discount, revenue, profit |

Realistic touches are simulated deliberately: December demand spikes, weekend
uplift, a mild upward trend over the window, province popularity weights loosely
mirroring SA population distribution, and a small set of customers/products that
never transact (so the anti-join query always has rows). All of that is
*simulated behaviour of the generator*, not measured business reality.

## Running the tests

```powershell
python -m pip install -e ".[dev]"   # or: pip install -r requirements.txt
python -m pytest tests -q
```

The suite (31 tests) checks:

- **Golden values** computed from the deterministic data — e.g. exact total
  revenue of R48,813,951.48 across 38,665 order lines, the top product
  (`P006`, Smart Watch), the top category (Electronics) and province (Gauteng),
  the exact RFM segment counts, and that December 2024 is the peak revenue month.
- **Window functions on a fixture** — a tiny hand-built table with hand-computed
  running sums, `ROW_NUMBER` ranks and `LAG` values.
- **Build idempotence** — rebuilding twice produces identical counts and totals,
  a stale/corrupt database file is replaced rather than appended to, and the
  committed CSVs are byte-identical to a fresh regeneration.
- **CLI smoke tests** — `list` prints all 15 queries; `run` handles good and bad
  input; every one of the 15 shipped SQL files executes and returns rows.

Every number quoted in this README comes from running the code in this repo.

## Design decisions

- **Why a star schema?** Analytical queries over retail events are mostly
  "aggregate facts by (a few) dimensions". A `fact_order_line` table at one-row-
  per-line grain with conformed dimensions keeps the fact table narrow, makes
  `GROUP BY province` / `GROUP BY month` trivial joins instead of string parsing,
  and mirrors how the same question would be modelled in a warehouse. The date
  dimension carries calendar attributes (`is_weekend`, `month_name`, ISO week) so
  queries never re-derive them.
- **Why SQLite?** It is built into Python, needs zero setup or server, runs the
  full window-function/CTE feature set this project demonstrates, and keeps the
  whole pipeline reproducible from a clean checkout with one command. The `.db`
  file is a build artifact (gitignored); `python -m sql_lab build` recreates it.
- **Why commit the CSVs *and* the generator?** Committing the data makes the repo
  browsable and the tests runnable without a build step; shipping the generator
  documents exactly how every column was produced and guarantees the data can be
  reproduced, audited or re-seeded.
- **RFM scoring** uses `NTILE(4)` quartiles over recency, frequency and monetary
  value, combined by simple `CASE` rules into seven segments. The rules are
  illustrative heuristics, not a calibrated marketing model.

## Limitations

- The data is synthetic; no business conclusion drawn from it should be presented
  as a real-world finding.
- All SQL uses standard SQLite syntax. Window functions, CTEs and views used here
  are portable, but date functions (`strftime`, `printf`) and `NTILE` behaviour
  are SQLite-flavoured; a Postgres port would swap those for `date_part`/`to_char`
  and `NTILE` over `ORDER BY` with an explicit tiebreaker.
- Single-node, single-file database; no incremental loading, orchestration or
  data-quality framework (this is a portfolio project, not a production system).
- The RFM segments and cohort windows (0–6 months) are illustrative choices.

## Suggested extensions

- **Postgres port** — load the same CSVs with `COPY`, swap the date functions,
  and add surrogate keys generated by a sequence.
- **dbt project** — turn `sql/schema.sql` and the 15 queries into dbt models with
  staging → intermediate → marts layers, sources and tests.
- **Bigger data** — raise `SEED`-driven volumes via CLI flags, partition the fact
  table by month, and add indexes/materialised views for the hot reports.
- **CI** — a GitHub Actions workflow that runs `python -m sql_lab build` and
  `pytest` on push to prove the repo stays reproducible.

## Repository layout

```
├── README.md
├── LICENSE                 # MIT
├── pyproject.toml          # package metadata; editable install + `sql-lab` script
├── requirements.txt        # test dependency (pytest); runtime is stdlib-only
├── .gitignore
├── data/                   # committed seed-42 CSVs (regenerated by `build`)
├── sql/
│   ├── schema.sql          # star schema + views
│   └── 01..15_*.sql        # analytical queries, each with its business question
├── src/sql_lab/
│   ├── generate_data.py    # seeded synthetic data generator
│   ├── build_db.py         # CSV -> SQLite star schema loader (idempotent)
│   └── __main__.py         # CLI: build | list | run
└── tests/
    ├── conftest.py         # builds a scratch database per test session
    ├── test_build.py       # idempotence, determinism, CLI smoke tests
    └── test_queries.py     # golden values + window-function fixture tests
```

## License

MIT — see [LICENSE](LICENSE). Copyright (c) 2026 Kagiso Gabaatlhole.
