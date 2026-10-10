
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent / "research.db"


def setup_database():
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()

        # Solo para esta base de datos sintética de demostración.
        cursor.execute("DROP TABLE IF EXISTS monthly_sales")
        cursor.execute("DROP TABLE IF EXISTS inventory")

        cursor.execute("""
            CREATE TABLE monthly_sales (
                month TEXT NOT NULL,
                product_id TEXT NOT NULL,
                units_sold INTEGER NOT NULL CHECK (units_sold >= 0),
                PRIMARY KEY (month, product_id)
            )
        """)

        cursor.execute("""
            CREATE TABLE inventory (
                product_id TEXT PRIMARY KEY,
                available_units INTEGER NOT NULL
                    CHECK (available_units >= 0),
                minimum_required_units INTEGER NOT NULL
                    CHECK (minimum_required_units >= 0)
            )
        """)

        sales_data = [
            ("2026-07", "PROD-001", 9000),
            ("2026-08", "PROD-001", 10000),
            ("2026-09", "PROD-001", 6000),
            ("2026-07", "PROD-002", 4000),
            ("2026-08", "PROD-002", 4500),
            ("2026-09", "PROD-002", 4800),
        ]

        inventory_data = [
            ("PROD-001", 120, 100),
            ("PROD-002", 45, 50),
        ]

        cursor.executemany("""
            INSERT INTO monthly_sales (month, product_id, units_sold)
            VALUES (?, ?, ?)
        """, sales_data)

        cursor.executemany("""
            INSERT INTO inventory (
                product_id,
                available_units,
                minimum_required_units
            )
            VALUES (?, ?, ?)
        """, inventory_data)

    print(f"Base de datos creada correctamente: {DB_PATH}")


if __name__ == "__main__":
    setup_database()
