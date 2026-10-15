import time
from ollama import chat
from database import get_sales_summary, get_inventory_status
import json
import re
from typing import Any, TypedDict
from langgraph.graph import StateGraph, START, END

# MODEL = "qwen3:4b"
MODEL = "qwen2.5:3b-instruct"
MAX_ITERATIONS = 5

tools = [
    get_sales_summary,
    get_inventory_status,
]

available_tools = {
    "get_sales_summary": get_sales_summary,
    "get_inventory_status": get_inventory_status,
}


def get_required_tools(question: str) -> list[str]:
    """Determine which tools are required by the user's request."""
    question_lower = question.lower()
    required = []

    asks_sales = any(
        term in question_lower
        for term in ("venta", "ventas", "vendidas", "vendidos", "caída", "caida")
    )
    asks_inventory = any(
        term in question_lower
        for term in ("inventario", "stock", "existencias")
    )

    if asks_sales:
        required.append("get_sales_summary")

    if asks_inventory:
        required.append("get_inventory_status")

    return required


def is_valid_sales_result(data: dict) -> bool:
    """Check sales result fields and basic numeric consistency."""
    required = {
        "product_id",
        "start_month",
        "start_sales",
        "end_month",
        "end_sales",
        "change_percent",
    }

    if not isinstance(data, dict) or not required.issubset(data):
        return False

    if not isinstance(data["product_id"], str) or not data["product_id"].strip():
        return False

    for field in ("start_month", "end_month"):
        if not isinstance(data[field], str) or not data[field].strip():
            return False

    for field in ("start_sales", "end_sales"):
        value = data[field]
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            return False

    start = data["start_sales"]
    end = data["end_sales"]
    change = data["change_percent"]

    if start == 0:
        return change is None

    if isinstance(change, bool) or not isinstance(change, (int, float)):
        return False

    expected = round((end - start) / start * 100, 2)
    return abs(change - expected) < 0.011


def is_valid_inventory_result(data: dict) -> bool:
    """Check inventory fields and consistency of stock status."""
    required = {
        "product_id",
        "available_units",
        "minimum_required_units",
        "stock_status",
    }

    if not isinstance(data, dict) or not required.issubset(data):
        return False

    if not isinstance(data["product_id"], str) or not data["product_id"].strip():
        return False

    available = data["available_units"]
    minimum = data["minimum_required_units"]

    for value in (available, minimum):
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            return False

    expected_status = (
        "above_minimum" if available > minimum
        else "below_minimum" if available < minimum
        else "at_minimum"
    )

    return data["stock_status"] == expected_status


def build_verified_answer(
    question: str,
    tool_results: dict,
) -> str:
    """Build a report using only complete, verified tool results."""
    sections = []

    sales = tool_results.get("get_sales_summary")

    if isinstance(sales, dict) and (
        "error" in sales
        or (sales and not is_valid_sales_result(sales))
    ):
        sections.append(
            "Ventas: no se pudieron verificar los datos porque la "
            "herramienta falló o devolvió un resultado inválido "
            "o incompleto. No se presentan cifras de ventas."
        )
    elif isinstance(sales, dict) and sales:
        change = sales["change_percent"]

        direction = (
            "aumento" if change > 0
            else "disminución" if change < 0
            else "sin variación"
        )

        sections.append(
            f"Ventas de {sales['product_id']}:\n"
            f"- Mes inicial: {sales['start_month']}: "
            f"{sales['start_sales']:,} unidades.\n"
            f"- Mes final: {sales['end_month']}: "
            f"{sales['end_sales']:,} unidades.\n"
            f"- Variación: {change:+.2f}% ({direction})."
            if change is not None
            else (
                f"Ventas de {sales['product_id']}:\n"
                f"- Mes inicial: {sales['start_month']}: "
                f"{sales['start_sales']:,} unidades.\n"
                f"- Mes final: {sales['end_month']}: "
                f"{sales['end_sales']:,} unidades.\n"
                "- Variación: no calculable porque las ventas "
                "iniciales son cero."
            )
        )

    inventory = tool_results.get("get_inventory_status")

    if isinstance(inventory, dict) and (
        "error" in inventory
        or (inventory and not is_valid_inventory_result(inventory))
    ):
        sections.append(
            "Inventario: no se pudo verificar el estado del stock "
            "porque falló la herramienta o devolvió un resultado "
            "inválido o incompleto."
        )

    elif isinstance(inventory, dict) and inventory:
        status = {
            "above_minimum": "por encima del mínimo",
            "below_minimum": "por debajo del mínimo",
            "at_minimum": "exactamente en el mínimo",
        }[inventory["stock_status"]]

        sections.append(
            f"Inventario de {inventory['product_id']}:\n"
            f"- Unidades disponibles: {inventory['available_units']}.\n"
            f"- Mínimo requerido: {inventory['minimum_required_units']}.\n"
            f"- Estado: {status}."
        )

    causal_terms = (
        "causa", "causada", "causado", "competidor",
        "por qué", "debido a", "razón",
    )

    if any(term in question.lower() for term in causal_terms):
        sections.append(
            "Causa de la variación: no se puede determinar "
            "con la evidencia disponible. Para evaluarla harían "
            "falta datos adicionales, como información de precios "
            "y actividad de competidores durante el mismo período."
        )

    if not sections:
        return "No se obtuvieron resultados válidos de las herramientas."

    return "\n\n".join(sections)


# def execute_tool(name: str, arguments: dict) -> dict:
#     """Execute a registered tool with validated arguments."""
#     tool = available_tools.get(name)

#     if tool is None:
#         return {"error": f"Unknown tool: {name}"}

#     if not isinstance(arguments, dict):
#         return {"error": "Tool arguments must be a dictionary"}

#     try:
#         return tool(**arguments)
#     except TypeError:
#         return {"error": f"Invalid arguments for tool: {name}"}
#     except Exception:
#         # No expose internal details to the model or user.
#         return {"error": f"Tool execution failed: {name}"}


def execute_tool(name: str, arguments: dict) -> dict:
    """Execute a registered tool and return controlled errors."""
    tool = available_tools.get(name)

    if tool is None:
        return {"error": f"Unknown tool: {name}"}

    if not isinstance(arguments, dict):
        return {"error": "Tool arguments must be a dictionary"}

    # Validate the period without silently coercing decimals or booleans.
    if name == "get_sales_summary" and "months" in arguments:
        months = arguments["months"]

        if isinstance(months, bool) or not isinstance(months, int):
            return {
                "error": "Invalid arguments for tool: get_sales_summary"
            }

    try:
        return tool(**arguments)
    except (TypeError, ValueError):
        return {"error": f"Invalid arguments for tool: {name}"}
    except Exception:
        # Do not expose internal exception details.
        return {"error": f"Tool execution failed: {name}"}


class AgentState(TypedDict, total=False):
    question: str
    messages: list[Any]
    required_tools: list[str]
    executed_tools: list[str]
    tool_results: dict[str, dict]
    iterations: int
    tool_calls: list[Any]
    model_content: str
    answer: str


SYSTEM_PROMPT = (
    "Eres un agente de análisis de datos empresariales. "
    "Responde siempre en español y de forma concisa. "
    "Utiliza las herramientas disponibles para consultar ventas e inventario. "
    "Para ventas, incluye los meses inicial y final, las unidades vendidas "
    "y el porcentaje de variación. Para inventario, incluye las unidades "
    "disponibles, el mínimo requerido y el estado del stock. "
    "Utiliza los resultados de las herramientas como fuente de verdad. "
    "No inventes datos ni causas sin evidencia. "
    "Si una causa no puede determinarse, explica qué información falta. "
    "Si una pregunta está fuera del alcance de las herramientas, "
    "explica esa limitación sin fingir que consultaste fuentes externas."
)


def model_node(state: AgentState) -> dict:
    """Ask the local model to answer or request a tool."""
    executed = set(state.get("executed_tools", []))
    required = set(state.get("required_tools", []))

    # If all required tools have run, use the verified report.
    if required and required.issubset(executed):
        return {
            "answer": build_verified_answer(
                state["question"],
                state.get("tool_results", {}),
            ),
            "tool_calls": [],
        }

    if state.get("iterations", 0) >= MAX_ITERATIONS:
        return {
            "answer": (
                f"No se obtuvo una respuesta final dentro del límite "
                f"de {MAX_ITERATIONS} iteraciones."
            ),
            "tool_calls": [],
        }

    response = chat(
        model=MODEL,
        messages=state["messages"],
        tools=tools,
        options={
            "num_predict": 256,
            "temperature": 0.1,
        },
    )

    message = response.message
    calls = message.tool_calls or []

    return {
        "messages": state["messages"] + [message],
        "iterations": state.get("iterations", 0) + 1,
        "tool_calls": calls,
        "model_content": (message.content or "").strip(),
    }


def route_after_model(state: AgentState) -> str:
    """Choose the next graph node."""
    if state.get("answer"):
        return "end"

    if state.get("tool_calls"):
        return "execute_tools"

    missing = (
        set(state.get("required_tools", []))
        - set(state.get("executed_tools", []))
    )

    if missing:
        return "recover_missing"

    return "finalize"


def execute_tools_node(state: AgentState) -> dict:
    """Execute requested tools and add their results to the conversation."""
    executed = list(state.get("executed_tools", []))
    results = dict(state.get("tool_results", {}))
    messages = list(state["messages"])

    for call in state.get("tool_calls", []):
        if not hasattr(call, "function") or not hasattr(call.function, "name"):
            name = "unknown"
            result = {"error": "Malformed tool call: missing function or name"}
        else:
            name = call.function.name
            arguments = getattr(call.function, "arguments", {}) or {}
            if not isinstance(name, str) or not name.strip():
                name = "unknown"
                result = {"error": "Malformed tool call: invalid name"}
            else:
                result = execute_tool(name, arguments)

        results[name] = result
        if name not in executed and name != "unknown":
            executed.append(name)

        messages.append({
            "role": "tool",
            "tool_name": name,
            "content": json.dumps(result, ensure_ascii=False),
        })

    return {
        "messages": messages,
        "executed_tools": executed,
        "tool_results": results,
        "tool_calls": [],
    }


def recover_missing_tools_node(state: AgentState) -> dict:
    """Execute required tools omitted by the model."""
    question = state["question"]
    missing = (
        set(state.get("required_tools", []))
        - set(state.get("executed_tools", []))
    )

    executed = list(state.get("executed_tools", []))
    results = dict(state.get("tool_results", {}))
    messages = list(state["messages"])

    match = re.search(r"\bPROD-\d+\b", question, re.IGNORECASE)

    if not match:
        missing_name = sorted(missing)[0]
        label = (
            "sus ventas"
            if missing_name == "get_sales_summary"
            else "su inventario"
        )
        return {
            "answer": (
                f"Necesito el identificador del producto para consultar {label}."
            ),
        }

    product_id = match.group(0).upper()

    for name in sorted(missing):
        if name == "get_sales_summary":
            arguments = {"product_id": product_id, "months": 2}
        elif name == "get_inventory_status":
            arguments = {"product_id": product_id}
        else:
            continue

        result = execute_tool(name, arguments)
        results[name] = result

        if name not in executed:
            executed.append(name)

        messages.append({
            "role": "tool",
            "tool_name": name,
            "content": json.dumps(result, ensure_ascii=False),
        })

    return {
        "messages": messages,
        "executed_tools": executed,
        "tool_results": results,
    }


def route_after_recovery(state: AgentState) -> str:
    return "end" if state.get("answer") else "model"


def finalize_node(state: AgentState) -> dict:
    """Return a grounded answer for data questions or the model response."""
    required = state.get("required_tools", [])

    if required:
        answer = build_verified_answer(
            state["question"],
            state.get("tool_results", {}),
        )
    else:
        answer = state.get("model_content", "")

    if not answer:
        answer = (
            "No se pudo generar una respuesta final. "
            "Intenta de nuevo o revisa los límites de generación."
        )

    return {"answer": answer}


def build_graph():
    graph = StateGraph(AgentState)

    graph.add_node("model", model_node)
    graph.add_node("execute_tools", execute_tools_node)
    graph.add_node("recover_missing", recover_missing_tools_node)
    graph.add_node("finalize", finalize_node)

    graph.add_edge(START, "model")

    graph.add_conditional_edges(
        "model",
        route_after_model,
        {
            "execute_tools": "execute_tools",
            "recover_missing": "recover_missing",
            "finalize": "finalize",
            "end": END,
        },
    )

    graph.add_edge("execute_tools", "model")

    graph.add_conditional_edges(
        "recover_missing",
        route_after_recovery,
        {
            "model": "model",
            "end": END,
        },
    )

    graph.add_edge("finalize", END)

    return graph.compile()


agent_graph = build_graph()


def run_agent(question: str) -> str:
    """Run the agent through the LangGraph workflow."""
    if not isinstance(question, str) or not question.strip():
        return "La pregunta debe ser un texto no vacío."

    initial_state: AgentState = {
        "question": question,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": question},
        ],
        "required_tools": get_required_tools(question),
        "executed_tools": [],
        "tool_results": {},
        "iterations": 0,
        "tool_calls": [],
        "model_content": "",
        "answer": "",
    }

    print(f"\n[INFO] Usando el modelo: {MODEL}")
    final_state = agent_graph.invoke(initial_state)

    answer = final_state.get("answer", "")
    print("Respuesta final:")
    print(answer)

    return answer


if __name__ == "__main__":
    question = (
        "Analiza las ventas de PROD-001 durante los dos últimos meses. "
        "Consulta también su inventario. Separa los hallazgos "
        "comprobados de las hipótesis y no inventes causas."
    )

    print("\nIniciando agente...")
    run_agent(question)
