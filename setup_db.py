
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
("2025-10", "PROD-001", 7500),
            ("2025-11", "PROD-001", 8000),
            ("2025-12", "PROD-001", 12000), # Pico navideño
            ("2026-01", "PROD-001", 8500),
            ("2026-02", "PROD-001", 8200),
            ("2026-03", "PROD-001", 9000),
            ("2026-04", "PROD-001", 9500),
            ("2026-05", "PROD-001", 10200),
            ("2026-06", "PROD-001", 9800),
            ("2026-07", "PROD-001", 9000),
            ("2026-08", "PROD-001", 10000),
            ("2026-09", "PROD-001", 6000),

            ("2025-11", "PROD-002", 4000),
            ("2025-12", "PROD-002", 3600),
            ("2026-01", "PROD-002", 3800),
            ("2026-02", "PROD-002", 4100),
            ("2026-03", "PROD-002", 4100),
            ("2026-04", "PROD-002", 4800),
            ("2026-05", "PROD-002", 4700),
            ("2026-06", "PROD-002", 4900),
            ("2026-07", "PROD-002", 5000),
            ("2026-08", "PROD-002", 4700),
            ("2026-09", "PROD-002", 4500),

            # PROD-003 (Caso borde: ventas iniciales en cero)
            ("2025-11", "PROD-003", 0),
            ("2025-12", "PROD-003", 0),
            ("2026-01", "PROD-003", 100),
            ("2026-02", "PROD-003", 110),
            ("2026-03", "PROD-003", 130),
            ("2026-04", "PROD-003", 200),
            ("2026-05", "PROD-003", 220),
            ("2026-06", "PROD-003", 300),
            ("2026-07", "PROD-003", 410),
            ("2026-08", "PROD-003", 430),
            ("2026-09", "PROD-003", 500),
        ]

        inventory_data = [
            ("PROD-001", 120, 100),
            ("PROD-002", 45, 50),
            ("PROD-003", 30, 20),
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
