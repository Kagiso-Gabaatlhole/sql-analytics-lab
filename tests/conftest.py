"""Shared pytest fixtures: make ``src/`` importable and build a scratch database."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

import pytest  # noqa: E402

from sql_lab.build_db import DEFAULT_DATA_DIR, build_db  # noqa: E402
from sql_lab.generate_data import generate_dataset  # noqa: E402


@pytest.fixture(scope="session")
def db_path(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Build the star schema once per test session into a temporary directory.

    Regenerates the CSVs into the repo's ``data/`` directory first if they are
    missing (e.g. after a fresh clone without the committed CSVs).
    """
    required = ["customers.csv", "products.csv", "orders.csv", "order_lines.csv"]
    if not all((DEFAULT_DATA_DIR / name).exists() for name in required):
        generate_dataset(DEFAULT_DATA_DIR)
    path = tmp_path_factory.mktemp("db") / "e-commerce.db"
    build_db(db_path=path)
    return path
