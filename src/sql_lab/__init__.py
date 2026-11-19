"""SQL Analytics Lab — a synthetic South African online-retail dataset and star schema.

The package ships a seeded data generator (``generate_data``), a SQLite star-schema
loader (``build_db``), and a small command-line interface (``__main__``) that builds
the database and runs the analytical queries in ``sql/``.

Everything in this project is generated locally from a fixed random seed; no
network access is required at build time or runtime.
"""

__version__ = "1.0.0"
