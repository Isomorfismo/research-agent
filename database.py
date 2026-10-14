import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent / "research.db"


def get_sales_summary(
    product_id: str = "PROD-001",
    months: int = 2,
) -> dict:
    """Summarize sales for a product over the latest months."""
    if not isinstance(product_id, str) or not product_id.strip():
        return {"error": "product_id must be a non-empty string"}

    if isinstance(months, bool) or not isinstance(months, int):
        return {"error": "months must be an integer"}

    if not 2 <= months <= 24:
        return {"error": "months must be between 2 and 24"}

    with sqlite3.connect(DB_PATH) as conn:
        rows = conn.execute(
            """
            SELECT month, units_sold
            FROM monthly_sales
            WHERE product_id = ?
            ORDER BY month DESC
            LIMIT ?
            """,
            (product_id, months),
        ).fetchall()

    if len(rows) < 2:
        return {
            "error": (
                f"Insufficient sales history for {product_id}: "
                "at least two months are required"
            )
        }

    rows.reverse()
    first_month, first_sales = rows[0]
    latest_month, latest_sales = rows[-1]

    change_percent = (
        (latest_sales - first_sales) / first_sales * 100
        if first_sales != 0
        else None
    )

    return {
        "product_id": product_id,
        "start_month": first_month,
        "start_sales": first_sales,
        "end_month": latest_month,
        "end_sales": latest_sales,
        "change_percent": (
            round(change_percent, 2)
            if change_percent is not None
            else None
        ),
        "months_included": len(rows),
    }


def get_inventory_status(product_id: str = "PROD-001") -> dict:
    """Return stock levels for a product."""
    if not isinstance(product_id, str) or not product_id.strip():
        return {"error": "product_id must be a non-empty string"}

    with sqlite3.connect(DB_PATH) as conn:
        row = conn.execute(
            """
            SELECT product_id, available_units, minimum_required_units
            FROM inventory
            WHERE product_id = ?
            """,
            (product_id,),
        ).fetchone()

    if row is None:
        return {"error": f"Product {product_id} was not found"}

    product_id, available, minimum = row

    return {
        "product_id": product_id,
        "available_units": available,
        "minimum_required_units": minimum,
        "stock_status": (
            "above_minimum" if available > minimum
            else "below_minimum" if available < minimum
            else "at_minimum"
        ),
    }
