"""Seeded generator for a synthetic South African online-retail dataset.

The module creates four CSV files in ``data/``:

* ``customers.csv``  — ~800 customers with province and signup date
* ``products.csv``   — ~60 products across eight categories
* ``orders.csv``     — ~20,000 header-level orders across 18 months
* ``order_lines.csv``— line-level facts (quantity, unit price, discount, revenue)

Everything is driven by a single :class:`random.Random` instance seeded with
:data:`SEED`, so regeneration is byte-for-byte reproducible on any machine.
The data is entirely synthetic and is intended for portfolio/demo use only.
"""
from __future__ import annotations

import bisect
import csv
import random
from datetime import date, timedelta
from pathlib import Path

#: Master seed for the whole dataset. Changing this changes every row.
SEED = 42

#: Inclusive date window covered by generated orders.
ORDER_START = date(2024, 1, 1)
ORDER_END = date(2025, 6, 30)  # 18 months inclusive

#: Signup dates may start this far before the order window.
SIGNUP_START = date(2023, 1, 1)

#: The eight real South African provinces, with population-ish order weights.
PROVINCES: list[tuple[str, float]] = [
    ("Gauteng", 0.26),
    ("KwaZulu-Natal", 0.19),
    ("Western Cape", 0.17),
    ("Eastern Cape", 0.11),
    ("Limpopo", 0.08),
    ("Mpumalanga", 0.07),
    ("North West", 0.06),
    ("Free State", 0.04),
    ("Northern Cape", 0.02),
]

#: Seasonal demand multipliers by calendar month (1-12); December peaks.
MONTH_FACTORS: dict[int, float] = {
    1: 0.92, 2: 0.88, 3: 0.95, 4: 0.97, 5: 1.00, 6: 1.05,
    7: 1.00, 8: 1.02, 9: 1.00, 10: 1.05, 11: 1.18, 12: 1.35,
}

#: Demand multipliers by weekday, Monday (0) to Sunday (6).
WEEKDAY_FACTORS: list[float] = [1.12, 0.92, 0.90, 0.92, 0.95, 1.05, 1.18]

#: Approximate orders per day at the start of the window (before factors).
BASE_DAILY_ORDERS = 32

#: Number of customers / products to generate.
N_CUSTOMERS = 800
N_PRODUCTS = 60

#: By construction these customers never place an order and these products are
#: never sold; the anti-join query (sql/11) relies on them existing.
NEVER_ORDER_CUSTOMER_IDS = frozenset(range(796, 801))  # C0796..C0800
NEVER_SOLD_PRODUCT_IDS = frozenset(range(56, 61))      # P056..P060

_FIRST_NAMES = [
    "Thabo", "Naledi", "Sipho", "Zanele", "Kagiso", "Lerato", "Bongani", "Nomsa",
    "Andile", "Precious", "Keanu", "Chloe", "Daniel", "Fatima", "Sibusiso", "Tumi",
    "Ntando", "Raadiyo", "Johan", "Aisha", "Lwazi", "Karabo", "Refilwe", "Ayanda",
    "Grant", "Nandi", "Mduduzi", "Palesa", "Rethabile", "Yusuf",
]

_LAST_NAMES = [
    "Nkosi", "Dlamini", "Ncube", "Mahlangu", "Mokoena", "Zulu", "Guma", "Khumalo",
    "Van Wyk", "Naidoo", "Smith", "Ndlovu", "Mabaso", "Pillay", "Botha", "Molefe",
    "Sithole", "Adams", "Mthembu", "Jacobs", "Ntuli", "Fourie", "Mahlaba", "Oosthuizen",
    "Sibanda", "Chauke", "Ramokgopa", "Segwapa", "Mofokeng", "Hlophe",
]

#: Category name -> (product count, unit-price range in ZAR, sample nouns).
CATEGORY_DEFS: dict[str, tuple[int, tuple[float, float], list[str]]] = {
    "Electronics": (8, (300.0, 3000.0), [
        "Wireless Earbuds", "Power Bank", "Bluetooth Speaker", "Laptop Stand",
        "Webcam", "Smart Watch", "USB-C Cable Set", "Desk Lamp",
    ]),
    "Home & Kitchen": (8, (150.0, 900.0), [
        "Chef Knife", "Non-stick Pan", "Coffee Grinder", "Storage Container Set",
        "Cutting Board", "Electric Kettle", "Blender", "Utensil Holder",
    ]),
    "Clothing": (8, (120.0, 700.0), [
        "Cotton T-Shirt", "Denim Jacket", "Running Shorts", "Hooded Sweatshirt",
        "Chino Trousers", "Summer Dress", "Wool Beanie", "Canvas Sneakers",
    ]),
    "Books": (7, (80.0, 350.0), [
        "Cookbook", "Crime Novel", "Atlas of Africa", "Biography", "Poetry Anthology",
        "Study Guide", "Children's Storybook",
    ]),
    "Beauty": (7, (60.0, 400.0), [
        "Face Cream", "Shampoo", "Sunscreen SPF50", "Lip Balm", "Beard Oil",
        "Body Lotion", "Perfume Roll-on",
    ]),
    "Sports & Outdoors": (7, (100.0, 800.0), [
        "Yoga Mat", "Resistance Bands", "Camping Lantern", "Running Armband",
        "Cricket Set", "Hiking Water Bottle", "Jump Rope",
    ]),
    "Toys & Games": (7, (70.0, 450.0), [
        "Building Blocks", "Card Game", "Puzzle 1000pc", "Toy Dinosaur",
        "Board Game", "Kite", "Colouring Set",
    ]),
    "Grocery": (8, (30.0, 200.0), [
        "Rooibos Tea 200g", "Biltong 250g", "Dried Fruit Mix", "Coffee Beans 500g",
        "Braai Spice Set", "Peanut Butter 750g", "Dried Black Beans 1kg",
    ]),
}

_QUALIFIERS = ["Deluxe", "Essential", "Compact", "Premium", "Classic", "Everyday", "Pro", "Urban"]

CUSTOMER_FIELDS = ["customer_id", "customer_name", "province", "signup_date"]
PRODUCT_FIELDS = ["product_id", "product_name", "category", "unit_price", "unit_cost"]
ORDER_FIELDS = ["order_id", "customer_id", "order_date"]
LINE_FIELDS = [
    "line_id", "order_id", "customer_id", "product_id", "quantity",
    "unit_price", "discount_pct", "discount_amount", "line_revenue", "line_profit",
]


def generate_customers(rng: random.Random) -> list[dict[str, object]]:
    """Generate ``N_CUSTOMERS`` synthetic customers spread over SA provinces.

    Signup dates run from :data:`SIGNUP_START` to the end of the order window.
    Customer IDs are assigned in creation order (``C0001``...).
    """
    provinces = [name for name, _ in PROVINCES]
    weights = [w for _, w in PROVINCES]
    span = (ORDER_END - SIGNUP_START).days
    customers: list[dict[str, object]] = []
    for i in range(1, N_CUSTOMERS + 1):
        name = f"{rng.choice(_FIRST_NAMES)} {rng.choice(_LAST_NAMES)}"
        signup = SIGNUP_START + timedelta(days=rng.randint(0, span))
        customers.append({
            "customer_id": f"C{i:04d}",
            "customer_name": name,
            "province": rng.choices(provinces, weights=weights, k=1)[0],
            "signup_date": signup.isoformat(),
        })
    return customers


def generate_products(rng: random.Random) -> list[dict[str, object]]:
    """Generate ``N_PRODUCTS`` synthetic products with categories and rand prices."""
    products: list[dict[str, object]] = []
    pid = 0
    for category, (count, (lo, hi), nouns) in CATEGORY_DEFS.items():
        for j in range(count):
            pid += 1
            price = round(rng.uniform(lo, hi), 2)
            cost = round(price * rng.uniform(0.55, 0.80), 2)
            name = f"{nouns[j % len(nouns)]} ({_QUALIFIERS[(j + pid) % len(_QUALIFIERS)]})"
            products.append({
                "product_id": f"P{pid:03d}",
                "product_name": name,
                "category": category,
                "unit_price": f"{price:.2f}",
                "unit_cost": f"{cost:.2f}",
            })
    return products


def generate_orders(
    rng: random.Random,
    customers: list[dict[str, object]],
    products: list[dict[str, object]],
) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    """Generate order headers and their line-level facts.

    Daily order volume follows seasonal (December peak), weekday and mild upward
    trend effects. Customers may only order on/after their signup date. The
    customers listed in :data:`NEVER_ORDER_CUSTOMER_IDS` and the products listed
    in :data:`NEVER_SOLD_PRODUCT_IDS` are excluded from every order line so the
    anti-join query always has rows to return.
    """
    eligible = sorted(
        (str(c["signup_date"]), str(c["customer_id"]))
        for c in customers
        if int(str(c["customer_id"])[1:]) not in NEVER_ORDER_CUSTOMER_IDS
    )
    signup_dates = [s for s, _ in eligible]
    eligible_ids = [cid for _, cid in eligible]

    sellable = [p for p in products if int(str(p["product_id"])[1:]) not in NEVER_SOLD_PRODUCT_IDS]
    pop_weights = [rng.randint(1, 10) for _ in sellable]

    qty_choices = [1, 2, 3, 4, 5]
    qty_weights = [0.45, 0.25, 0.15, 0.10, 0.05]
    line_count_choices = [1, 2, 3, 4]
    line_count_weights = [0.42, 0.33, 0.17, 0.08]
    discount_choices = [5.0, 10.0, 15.0, 20.0]
    discount_weights = [0.35, 0.30, 0.20, 0.15]

    orders: list[dict[str, object]] = []
    lines: list[dict[str, object]] = []
    order_seq = 0
    line_seq = 0
    day_index = 0
    total_days = (ORDER_END - ORDER_START).days + 1

    day = ORDER_START
    while day <= ORDER_END:
        expected = (
            BASE_DAILY_ORDERS
            * MONTH_FACTORS[day.month]
            * WEEKDAY_FACTORS[day.weekday()]
            * (1 + 0.0005 * day_index)
            * rng.uniform(0.88, 1.12)
        )
        n_orders = max(1, int(round(expected)))
        for _ in range(n_orders):
            order_seq += 1
            order_id = f"ORD-{order_seq:06d}"
            n_eligible = bisect.bisect_right(signup_dates, day.isoformat())
            customer_id = eligible_ids[rng.randrange(n_eligible)]
            orders.append({
                "order_id": order_id,
                "customer_id": customer_id,
                "order_date": day.isoformat(),
            })
            for _ in range(rng.choices(line_count_choices, weights=line_count_weights, k=1)[0]):
                line_seq += 1
                product = rng.choices(sellable, weights=pop_weights, k=1)[0]
                price = float(str(product["unit_price"]))
                cost = float(str(product["unit_cost"]))
                qty = rng.choices(qty_choices, weights=qty_weights, k=1)[0]
                discount_pct = (
                    rng.choices(discount_choices, weights=discount_weights, k=1)[0]
                    if rng.random() < 0.22 else 0.0
                )
                revenue = round(qty * price * (1 - discount_pct / 100.0), 2)
                gross = round(qty * price, 2)
                lines.append({
                    "line_id": f"LN-{line_seq:06d}",
                    "order_id": order_id,
                    "customer_id": customer_id,
                    "product_id": str(product["product_id"]),
                    "quantity": qty,
                    "unit_price": f"{price:.2f}",
                    "discount_pct": f"{discount_pct:.1f}",
                    "discount_amount": f"{gross - revenue:.2f}",
                    "line_revenue": f"{revenue:.2f}",
                    "line_profit": f"{revenue - qty * cost:.2f}",
                })
        day += timedelta(days=1)
        day_index += 1

    return orders, lines


def write_csv(path: Path, rows: list[dict[str, object]], fieldnames: list[str]) -> None:
    """Write ``rows`` to ``path`` as UTF-8 CSV with LF line endings."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def generate_dataset(data_dir: Path, seed: int = SEED) -> dict[str, int]:
    """Generate all CSVs into ``data_dir`` and return row counts per file.

    Uses a fresh :class:`random.Random` seeded with ``seed``; calling this
    function twice with the same seed produces byte-identical files.
    """
    rng = random.Random(seed)
    customers = generate_customers(rng)
    products = generate_products(rng)
    orders, lines = generate_orders(rng, customers, products)

    data_dir = Path(data_dir)
    write_csv(data_dir / "customers.csv", customers, CUSTOMER_FIELDS)
    write_csv(data_dir / "products.csv", products, PRODUCT_FIELDS)
    write_csv(data_dir / "orders.csv", orders, ORDER_FIELDS)
    write_csv(data_dir / "order_lines.csv", lines, LINE_FIELDS)
    return {
        "customers": len(customers),
        "products": len(products),
        "orders": len(orders),
        "order_lines": len(lines),
    }
