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



import pytest

from agent import available_tools, execute_tool


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
