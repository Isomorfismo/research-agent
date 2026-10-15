from agent import build_verified_answer, get_required_tools, recover_missing_tools_node, route_after_model, execute_tool, available_tools, model_node, MAX_ITERATIONS
import pytest

def test_verified_answer_includes_sales_data():
    results = {
        "get_sales_summary": {
            "product_id": "PROD-001",
            "start_month": "2026-08",
            "start_sales": 10000,
            "end_month": "2026-09",
            "end_sales": 6000,
            "change_percent": -40.0,
            "months_included": 2,
        }
    }

    answer = build_verified_answer(
        "Analiza las ventas de PROD-001",
        results,
    )

    assert "PROD-001" in answer
    assert "2026-08" in answer
    assert "10,000" in answer
    assert "2026-09" in answer
    assert "6,000" in answer
    assert "-40.00%" in answer


def test_verified_answer_includes_inventory_status():
    results = {
        "get_inventory_status": {
            "product_id": "PROD-002",
            "available_units": 45,
            "minimum_required_units": 50,
            "stock_status": "below_minimum",
        }
    }

    answer = build_verified_answer(
        "Consulta el inventario de PROD-002",
        results,
    )

    assert "45" in answer
    assert "50" in answer
    assert "por debajo del mínimo" in answer


def test_verified_answer_does_not_invent_cause():
    results = {
        "get_sales_summary": {
            "product_id": "PROD-001",
            "start_month": "2026-08",
            "start_sales": 10000,
            "end_month": "2026-09",
            "end_sales": 6000,
            "change_percent": -40.0,
            "months_included": 2,
        }
    }

    question = (
        "¿La caída fue causada por un competidor "
        "que lanzó un producto más barato?"
    )

    answer = build_verified_answer(question, results)
    answer_lower = answer.lower()

    assert "no se puede determinar" in answer_lower
    assert "competidor" not in answer_lower.split(
        "causa de la variación:", 1
    )[0]


def test_get_required_tools_for_sales_and_inventory():
    question = (
        "Analiza las ventas de PROD-001 "
        "y consulta su inventario"
    )

    required = get_required_tools(question)

    assert "get_sales_summary" in required
    assert "get_inventory_status" in required


def test_get_required_tools_for_weather():
    required = get_required_tools(
        "¿Qué tiempo hará mañana en Ciudad de México?"
    )

    assert required == []


def test_verified_answer_handles_missing_results():
    answer = build_verified_answer(
        "Analiza las ventas de PROD-001",
        {},
    )

    assert answer == (
        "No se obtuvieron resultados válidos de las herramientas."
    )


from types import SimpleNamespace

import agent


def make_sales_result():
    return {
        "product_id": "PROD-001",
        "start_month": "2026-08",
        "start_sales": 10000,
        "end_month": "2026-09",
        "end_sales": 6000,
        "change_percent": -40.0,
        "months_included": 2,
    }


def make_inventory_result():
    return {
        "product_id": "PROD-001",
        "available_units": 120,
        "minimum_required_units": 100,
        "stock_status": "above_minimum",
    }


def make_response(content="", tool_calls=None):
    message = SimpleNamespace(
        content=content,
        tool_calls=tool_calls,
    )
    return SimpleNamespace(
        message=message,
        done_reason="stop",
        prompt_eval_count=10,
        eval_count=5,
        total_duration=1_000_000,
    )


def make_tool_call(name, arguments):
    return SimpleNamespace(
        function=SimpleNamespace(
            name=name,
            arguments=arguments,
        )
    )


def test_run_agent_returns_verified_answer_after_tool_calls(monkeypatch):
    question = (
        "Analiza las ventas de PROD-001 y consulta su inventario"
    )

    response = make_response(
        tool_calls=[
            make_tool_call(
                "get_sales_summary",
                {"product_id": "PROD-001", "months": 2},
            ),
            make_tool_call(
                "get_inventory_status",
                {"product_id": "PROD-001"},
            ),
        ]
    )

    monkeypatch.setattr(agent, "chat", lambda **kwargs: response)

    def fake_execute_tool(name, arguments):
        if name == "get_sales_summary":
            return make_sales_result()
        if name == "get_inventory_status":
            return make_inventory_result()
        return {"error": f"Unknown tool: {name}"}

    monkeypatch.setattr(agent, "execute_tool", fake_execute_tool)

    answer = agent.run_agent(question)

    assert "10,000" in answer
    assert "6,000" in answer
    assert "-40.00%" in answer
    assert "120" in answer
    assert "100" in answer
    assert "por encima del mínimo" in answer


def test_run_agent_executes_required_tools_if_model_omits_them(monkeypatch):
    question = (
        "Analiza las ventas de PROD-001 y consulta su inventario"
    )
    chat_calls = []

    def fake_chat(**kwargs):
        chat_calls.append(kwargs)
        return make_response(content="No tengo resultados.")

    monkeypatch.setattr(agent, "chat", fake_chat)

    executed = []

    def fake_execute_tool(name, arguments):
        executed.append(name)

        if name == "get_sales_summary":
            return make_sales_result()
        if name == "get_inventory_status":
            return make_inventory_result()
        return {"error": f"Unknown tool: {name}"}

    monkeypatch.setattr(agent, "execute_tool", fake_execute_tool)

    answer = agent.run_agent(question)

    assert len(chat_calls) == 1
    assert "get_sales_summary" in executed
    assert "get_inventory_status" in executed
    assert "10,000" in answer
    assert "6,000" in answer
    assert "120" in answer
    assert "100" in answer


def test_build_verified_answer_reports_sales_tool_error():
    from agent import build_verified_answer

    answer = build_verified_answer(
        "Analiza las ventas de PROD-001",
        {
            "get_sales_summary": {"error": "Tool execution failed"}
        },
    )

    assert "no se pudieron verificar" in answer
    assert "No se presentan cifras de ventas" in answer


def test_build_verified_answer_reports_inventory_tool_error():
    from agent import build_verified_answer

    answer = build_verified_answer(
        "Consulta el inventario de PROD-001",
        {
            "get_inventory_status": {"error": "Tool execution failed"}
        },
    )

    assert "no se pudo verificar" in answer
    assert "falló la herramienta" in answer


def test_build_verified_answer_handles_missing_tool_results():
    from agent import build_verified_answer

    answer = build_verified_answer(
        "Analiza las ventas de PROD-001",
        {},
    )

    assert answer == "No se obtuvieron resultados válidos de las herramientas."


def test_execute_tool_rejects_unknown_tool():
    from agent import execute_tool

    result = execute_tool("unknown_tool", {})

    assert "error" in result
    assert "Unknown tool" in result["error"]


def test_execute_tool_rejects_non_dictionary_arguments():
    from agent import execute_tool

    result = execute_tool("get_sales_summary", [])

    assert "error" in result
    assert result["error"] == "Tool arguments must be a dictionary"

def test_build_verified_answer_handles_incomplete_sales_result():
    from agent import build_verified_answer

    answer = build_verified_answer(
        "Analiza las ventas de PROD-001",
        {
            "get_sales_summary": {
                "product_id": "PROD-001",
                "start_month": "2026-08",
            }
        },
    )

    assert "no se pudieron verificar" in answer
    assert "No se presentan cifras de ventas" in answer


def test_build_verified_answer_handles_incomplete_inventory_result():
    from agent import build_verified_answer

    answer = build_verified_answer(
        "Consulta el inventario de PROD-001",
        {
            "get_inventory_status": {
                "product_id": "PROD-001",
                "available_units": 120,
            }
        },
    )

    assert "no se pudo verificar" in answer
    assert "falló la herramienta" in answer




def test_execute_tool_rejects_decimal_months(monkeypatch):
    result = agent.execute_tool(
        "get_sales_summary",
        {"product_id": "PROD-001", "months": 2.7},
    )

    assert result == {
        "error": "Invalid arguments for tool: get_sales_summary"
    }


def test_execute_tool_rejects_boolean_months():
    result = agent.execute_tool(
        "get_sales_summary",
        {"product_id": "PROD-001", "months": True},
    )

    assert result == {
        "error": "Invalid arguments for tool: get_sales_summary"
    }


def test_execute_tool_does_not_expose_internal_errors(monkeypatch):
    def broken_tool(**kwargs):
        raise RuntimeError("internal database details")

    monkeypatch.setitem(
        agent.available_tools,
        "get_inventory_status",
        broken_tool,
    )

    result = agent.execute_tool(
        "get_inventory_status",
        {"product_id": "PROD-001"},
    )

    assert result == {
        "error": "Tool execution failed: get_inventory_status"
    }
    assert "internal database details" not in str(result)


def test_execute_tools_node_handles_malformed_tool_call():
    from agent import execute_tools_node

    # Llamada sin atributo function
    malformed_call = SimpleNamespace()
    state = {
        "messages": [],
        "tool_calls": [malformed_call],
        "executed_tools": [],
        "tool_results": {},
    }

    next_state = execute_tools_node(state)
    assert "unknown" in next_state["tool_results"]
    assert "error" in next_state["tool_results"]["unknown"]


def test_execute_tools_node_handles_invalid_function_name():
    from agent import execute_tools_node

    # Llamada con función cuyo nombre no es válido
    invalid_call = SimpleNamespace(
        function=SimpleNamespace(name="", arguments={})
    )
    state = {
        "messages": [],
        "tool_calls": [invalid_call],
        "executed_tools": [],
        "tool_results": {},
    }

    next_state = execute_tools_node(state)
    assert "unknown" in next_state["tool_results"]
    assert "error" in next_state["tool_results"]["unknown"]



from agent import (
    is_valid_sales_result,
    is_valid_inventory_result,
    finalize_node,
    route_after_recovery,
    run_agent,
)


@pytest.mark.parametrize(
    "invalid_result",
    [
        None,
        [],
        {},
        {"product_id": ""},
        {"product_id": "PROD-001", "start_month": ""},
        {"product_id": "PROD-001", "start_month": "2026-08"},
    ],
)
def test_sales_validator_rejects_invalid_results(invalid_result):
    assert is_valid_sales_result(invalid_result) is False


@pytest.mark.parametrize(
    "invalid_value",
    [True, -1, 1.5, "100"],
)
def test_sales_validator_rejects_invalid_sales_values(invalid_value):
    result = {
        "product_id": "PROD-001",
        "start_month": "2026-08",
        "start_sales": invalid_value,
        "end_month": "2026-09",
        "end_sales": 100,
        "change_percent": 0.0,
    }

    assert is_valid_sales_result(result) is False


@pytest.mark.parametrize(
    "invalid_value",
    [True, -1, 1.5, "100"],
)
def test_inventory_validator_rejects_invalid_unit_values(invalid_value):
    result = {
        "product_id": "PROD-001",
        "available_units": invalid_value,
        "minimum_required_units": 100,
        "stock_status": "above_minimum",
    }

    assert is_valid_inventory_result(result) is False


def test_inventory_validator_rejects_inconsistent_status():
    result = {
        "product_id": "PROD-001",
        "available_units": 40,
        "minimum_required_units": 50,
        "stock_status": "above_minimum",
    }

    assert is_valid_inventory_result(result) is False


def test_finalize_node_returns_model_content_without_required_tools():
    result = finalize_node({
        "required_tools": [],
        "model_content": "Respuesta general.",
    })

    assert result["answer"] == "Respuesta general."


def test_finalize_node_returns_fallback_for_empty_answer():
    result = finalize_node({
        "required_tools": [],
        "model_content": "",
    })

    assert "No se pudo generar una respuesta final" in result["answer"]


def test_route_after_recovery_ends_when_answer_exists():
    assert route_after_recovery({"answer": "Respuesta lista"}) == "end"


def test_route_after_recovery_continues_without_answer():
    assert route_after_recovery({}) == "model"


@pytest.mark.parametrize("question", ["", "   ", None, 123])
def test_run_agent_rejects_invalid_questions(question):
    result = run_agent(question)

    assert result == "La pregunta debe ser un texto no vacío."



@pytest.mark.parametrize(
    ("required_tool", "expected_text"),
    [
        ("get_sales_summary", "sus ventas"),
        ("get_inventory_status", "su inventario"),
    ],
)
def test_recovery_requests_product_id_when_missing(
    required_tool, expected_text
):
    result = recover_missing_tools_node({
        "question": "Analiza el producto",
        "required_tools": [required_tool],
        "executed_tools": [],
        "tool_results": {},
        "messages": [],
    })

    assert expected_text in result["answer"]


def test_recovery_skips_unknown_missing_tool():
    result = recover_missing_tools_node({
        "question": "Analiza PROD-001",
        "required_tools": ["unknown_tool"],
        "executed_tools": [],
        "tool_results": {},
        "messages": [],
    })

    assert "answer" not in result
    assert result["executed_tools"] == []
    assert result["tool_results"] == {}



def test_execute_tool_handles_type_error(monkeypatch):
    def broken_tool():
        raise TypeError("internal details")

    monkeypatch.setitem(
        available_tools,
        "broken_type_tool",
        broken_tool,
    )

    result = execute_tool("broken_type_tool", {})

    assert result == {
        "error": "Invalid arguments for tool: broken_type_tool"
    }



def test_model_node_stops_at_iteration_limit():
    result = model_node({
        "question": "Analiza PROD-001",
        "required_tools": [],
        "executed_tools": [],
        "tool_results": {},
        "iterations": MAX_ITERATIONS,
        "messages": [],
    })

    assert "answer" in result
    assert str(MAX_ITERATIONS) in result["answer"]
    assert result["tool_calls"] == []


def test_finalize_node_uses_verified_answer(monkeypatch):
    import agent

    def fake_verified_answer(question, results):
        return "Respuesta verificada de prueba."

    monkeypatch.setattr(
        agent,
        "build_verified_answer",
        fake_verified_answer,
    )

    result = agent.finalize_node({
        "question": "Analiza PROD-001",
        "required_tools": ["get_sales_summary"],
        "tool_results": {},
    })

    assert result["answer"] == "Respuesta verificada de prueba."



def test_route_after_model_ends_when_answer_exists():
    state = {
        "answer": "Respuesta lista",
        "tool_calls": [{"name": "get_sales_summary"}],
        "required_tools": ["get_sales_summary"],
        "executed_tools": [],
    }

    assert route_after_model(state) == "end"


def test_route_after_model_executes_tool_calls():
    state = {
        "answer": "",
        "tool_calls": [{"name": "get_sales_summary"}],
        "required_tools": ["get_sales_summary"],
        "executed_tools": [],
    }

    assert route_after_model(state) == "execute_tools"


def test_route_after_model_recovers_missing_tools():
    state = {
        "answer": "",
        "tool_calls": [],
        "required_tools": ["get_sales_summary", "get_inventory_status"],
        "executed_tools": ["get_sales_summary"],
    }

    assert route_after_model(state) == "recover_missing"


def test_route_after_model_finalizes_when_no_tools_are_missing():
    state = {
        "answer": "",
        "tool_calls": [],
        "required_tools": ["get_sales_summary"],
        "executed_tools": ["get_sales_summary"],
    }

    assert route_after_model(state) == "finalize"


def test_sales_validator_rejects_non_string_product_id():
    result = {
        "product_id": 123,
        "start_month": "2026-08",
        "start_sales": 100,
        "end_month": "2026-09",
        "end_sales": 110,
        "change_percent": 10.0,
    }

    assert is_valid_sales_result(result) is False


def test_sales_validator_rejects_blank_month():
    result = {
        "product_id": "PROD-001",
        "start_month": "   ",
        "start_sales": 100,
        "end_month": "2026-09",
        "end_sales": 110,
        "change_percent": 10.0,
    }

    assert is_valid_sales_result(result) is False


def test_sales_validator_rejects_non_numeric_change():
    result = {
        "product_id": "PROD-001",
        "start_month": "2026-08",
        "start_sales": 100,
        "end_month": "2026-09",
        "end_sales": 110,
        "change_percent": "10%",
    }

    assert is_valid_sales_result(result) is False


def test_inventory_validator_rejects_non_string_product_id():
    result = {
        "product_id": 123,
        "available_units": 100,
        "minimum_required_units": 50,
        "stock_status": "above_minimum",
    }

    assert is_valid_inventory_result(result) is False