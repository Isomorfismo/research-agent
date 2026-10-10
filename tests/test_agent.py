from agent import build_verified_answer, get_required_tools


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
