import pytest
from agent import available_tools, execute_tool, is_valid_sales_result, is_valid_inventory_result
from database import get_sales_summary, get_inventory_status

def test_sales_summary():
    result = get_sales_summary("PROD-001", 2)

    assert "error" not in result
    assert result["start_month"] == "2026-08"
    assert result["end_month"] == "2026-09"
    assert result["change_percent"] == -40.0


def test_inventory_above_minimum():
    result = get_inventory_status("PROD-001")

    assert result["available_units"] == 120
    assert result["minimum_required_units"] == 100
    assert result["stock_status"] == "above_minimum"


def test_inventory_below_minimum():
    result = get_inventory_status("PROD-002")

    assert result["available_units"] == 45
    assert result["minimum_required_units"] == 50
    assert result["stock_status"] == "below_minimum"


def test_unknown_product():
    result = get_inventory_status("UNKNOWN")

    assert "error" in result


def test_invalid_month_count():
    result = get_sales_summary("PROD-001", 1)

    assert "error" in result


def test_sales_summary_for_second_product():
    result = get_sales_summary("PROD-002", 2)

    assert "error" not in result
    assert result["product_id"] == "PROD-002"
    assert result["start_month"] == "2026-08"
    assert result["start_sales"] == 4500
    assert result["end_month"] == "2026-09"
    assert result["end_sales"] == 4800
    assert result["change_percent"] == 6.67



def test_sales_rejects_empty_product():
    result = get_sales_summary("", 2)
    assert "error" in result


def test_sales_rejects_none_product():
    result = get_sales_summary(None, 2)
    assert "error" in result


def test_sales_rejects_non_integer_months():
    result = get_sales_summary("PROD-001", "2")
    assert "error" in result


def test_sales_rejects_boolean_months():
    result = get_sales_summary("PROD-001", True)
    assert "error" in result


def test_sales_rejects_unknown_product():
    result = get_sales_summary("UNKNOWN", 2)
    assert "error" in result


def test_inventory_rejects_invalid_product():
    result = get_inventory_status(None)
    assert "error" in result


def test_unknown_tool_returns_error():
    result = execute_tool("tool_that_does_not_exist", {})
    assert "error" in str(result).lower() or "desconoc" in str(result).lower()


def test_non_dict_arguments_are_rejected():
    result = execute_tool("get_sales_summary", ["PROD-001", 2])
    assert "error" in str(result).lower() or "argument" in str(result).lower()


def test_invalid_tool_arguments_are_handled():
    result = execute_tool(
        "get_sales_summary",
        {"product_id": "PROD-001", "months": "two"},
    )
    assert result is not None


def test_tool_exception_is_caught(monkeypatch):
    def broken_tool():
        raise RuntimeError("simulated database failure")

    monkeypatch.setitem(available_tools, "broken_tool", broken_tool)

    result = execute_tool("broken_tool", {})

    assert result is not None
    assert "error" in str(result).lower() or "fall" in str(result).lower()


# 1. Producto inexistente
def test_non_existent_product():
    sales_res = get_sales_summary("PROD-999")
    assert "error" in sales_res

    inv_res = get_inventory_status("PROD-999")
    assert "error" in inv_res


# 2. Historial de ventas insuficiente (menos de 2 meses)
def test_insufficient_sales_history():
    # Pedir 1 solo mes debe fallar por requerir al menos 2
    res = get_sales_summary("PROD-001", months=1)
    assert "error" in res


# 3. Ventas iniciales iguales a cero (Caso borde de división por cero)
def test_zero_initial_sales(monkeypatch):
    # Simulamos un resultado de ventas con start_sales = 0
    zero_sales_data = {
        "product_id": "PROD-003",
        "start_month": "2026-08",
        "start_sales": 0,
        "end_month": "2026-09",
        "end_sales": 500,
        "change_percent": None,
        "months_included": 2,
    }
    assert is_valid_sales_result(zero_sales_data) is True


# 4. Inventario exactamente en el mínimo requerido ("at_minimum")
def test_inventory_at_minimum(monkeypatch):
    import sqlite3
    from database import DB_PATH

    # Insertamos temporalmente un producto con stock exacto al mínimo
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            "INSERT OR REPLACE INTO inventory (product_id, available_units, minimum_required_units) VALUES (?, ?, ?)",
            ("PROD-TEST-MIN", 50, 50)
        )

    res = get_inventory_status("PROD-TEST-MIN")
    assert res["stock_status"] == "at_minimum"
    assert is_valid_inventory_result(res) is True

    # Limpieza
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("DELETE FROM inventory WHERE product_id = ?", ("PROD-TEST-MIN",))


# 5. Argumentos inválidos y errores de herramientas
def test_invalid_tool_arguments_and_exceptions():
    # Argumento vacío o tipo incorrecto
    res_empty = get_sales_summary("")
    assert "error" in res_empty

    res_type = get_sales_summary(product_id="PROD-001", months="invalid_type")
    assert "error" in res_type

    # Herramienta desconocida mediante execute_tool
    res_unknown = execute_tool("unknown_tool", {})
    assert res_unknown == {"error": "Unknown tool: unknown_tool"}

    # Argumentos que no son diccionario
    res_not_dict = execute_tool("get_sales_summary", "not_a_dict")
    assert res_not_dict == {"error": "Tool arguments must be a dictionary"}