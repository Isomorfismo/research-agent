import time
from ollama import chat
from database import get_sales_summary, get_inventory_status
import json
import re

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

def build_verified_answer(
    question: str,
    tool_results: dict,
) -> str:
    """Build a report directly from verified tool results."""
    sections = []

    sales = tool_results.get("get_sales_summary")
    if sales and "error" not in sales:
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
            f"- Variación: {change:+.2f}% "
            f"({direction})."
        )

    inventory = tool_results.get("get_inventory_status")
    if inventory and "error" not in inventory:
        status = {
            "above_minimum": "por encima del mínimo",
            "below_minimum": "por debajo del mínimo",
            "at_minimum": "exactamente en el mínimo",
        }.get(inventory["stock_status"], "no determinado")

        sections.append(
            f"Inventario de {inventory['product_id']}:\n"
            f"- Unidades disponibles: {inventory['available_units']}.\n"
            f"- Mínimo requerido: {inventory['minimum_required_units']}.\n"
            f"- Estado: {status}."
        )

    causal_terms = (
        "causa", "causada", "causado", "competidor",
        "por qué", "debido a", "razón"
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

def execute_tool(name: str, arguments: dict) -> dict:
    """Execute a registered tool with validated arguments."""
    tool = available_tools.get(name)

    if tool is None:
        return {"error": f"Unknown tool: {name}"}

    if not isinstance(arguments, dict):
        return {"error": "Tool arguments must be a dictionary"}

    try:
        return tool(**arguments)
    except TypeError:
        return {"error": f"Invalid arguments for tool: {name}"}
    except Exception:
        # No expose internal details to the model or user.
        return {"error": f"Tool execution failed: {name}"}



def run_agent(question: str) -> str:

    print(f"\n[INFO] Usando el modelo: {MODEL}")
    
    messages = [
                {
            "role": "system",
            "content": (
                "Eres un agente de análisis de datos empresariales. "
                "Responde siempre en español y de forma concisa. "
                "Utiliza las herramientas disponibles para consultar ventas e inventario. "
                "Para ventas, incluye el mes inicial, las unidades vendidas, "
                "el mes final, las unidades vendidas y el porcentaje de variación. "
                "Para inventario, incluye las unidades disponibles, el mínimo requerido "
                "y si el stock está por encima, igual o por debajo del mínimo. "
                "Incluye todos los resultados relevantes devueltos por las herramientas; "
                "no omitas datos porque se hayan consultado en iteraciones diferentes. "
                "Responde solo con datos verificados o cálculos directos basados en ellos. "
                "No inventes causas ni propongas explicaciones sin evidencia. "
                "Si preguntan por una causa que no puede determinarse con los datos "
                "disponibles, indícalo explícitamente y menciona qué información falta. "
                "Si una pregunta está fuera del alcance de las herramientas, "
                "explica esa limitación sin fingir que has consultado fuentes externas."
        ),
        },
        {"role": "user", "content": question},
    ]

    total_start_time = time.perf_counter()  # Start global timer

    required_tools = get_required_tools(question)
    executed_tools = set()
    tool_results = {}

    for iteration in range(MAX_ITERATIONS):


        iter_start_time = time.perf_counter()  # Start iteration timer
        print(f"\n--- [Iteración {iteration + 1} / {MAX_ITERATIONS}] ---")
        print("Pensando...")

        model_start_time = time.perf_counter()

        if required_tools and set(required_tools).issubset(executed_tools):
            answer = build_verified_answer(question, tool_results)
            print("Respuesta verificada por herramientas:")
            print(answer)
            return answer

        response = chat(
            model=MODEL,
            messages=messages,
            tools=tools,
            # think=False,
            options={
                "num_predict": 256,
                "temperature": 0.1,
            },
        )

        print("Motivo:", response.done_reason)
        print("Tokens de entrada:", response.prompt_eval_count)
        print("Tokens generados:", response.eval_count)
        print("Duración total (s):", response.total_duration / 1e9)

        print("Respuesta del modelo:", repr(response.message.content))
        print("Llamadas a herramientas:", response.message.tool_calls)
        print("Motivo de finalización:", response.done_reason)


        model_duration = time.perf_counter() - model_start_time
        print(f"Tiempo de inferencia del modelo: {model_duration:.2f} s")

        if response.message.content:
            print(f"Modelo dice: {response.message.content}")

        if response.message.tool_calls:
            print(f"Llamadas a herramientas: {len(response.message.tool_calls)}")

        messages.append(response.message)
        tool_calls = response.message.tool_calls or []




        if not tool_calls:

            missing_tools = set(required_tools) - executed_tools

            if missing_tools:
                print(f"Faltan herramientas requeridas: {sorted(missing_tools)}")

                for name in sorted(missing_tools):
                    if name == "get_sales_summary":
                        match = re.search(r"\bPROD-\d+\b", question, re.IGNORECASE)

                        if not match:
                            return (
                                "Necesito el identificador del producto "
                                "para consultar sus ventas."
                            )

                        arguments = {
                            "product_id": match.group(0).upper(),
                            "months": 2,
                        }

                    elif name == "get_inventory_status":
                        match = re.search(r"\bPROD-\d+\b", question, re.IGNORECASE)

                        if not match:
                            return (
                                "Necesito el identificador del producto "
                                "para consultar su inventario."
                            )

                        arguments = {"product_id": match.group(0).upper()}

                    else:
                        continue

                    result = execute_tool(name, arguments)
                    executed_tools.add(name)
                    tool_results[name] = result

                    messages.append({
                        "role": "tool",
                        "tool_name": name,
                        "content": json.dumps(result, ensure_ascii=False),
                    })

                messages.append({
                    "role": "user",
                    "content": (
                        "Ya se han consultado las herramientas requeridas. "
                        "Redacta ahora una única respuesta en español que incluya "
                        "todos los resultados relevantes de las herramientas, "
                        "sin omitir cifras y sin inventar causas. "
                        "Resultados verificados: "
                        + json.dumps(tool_results, ensure_ascii=False)
                    ),
                })

                continue

            if required_tools:
                answer = build_verified_answer(
                    question,
                    tool_results,
                )
            else:
                answer = (response.message.content or "").strip()

            if not answer:
                print("Error: el modelo terminó sin respuesta final.")
                return (
                    "No se pudo generar una respuesta final. "
                    "Intenta de nuevo o revisa los límites de generación."
                )

            elapsed = time.perf_counter() - total_start_time
            print(
                f"El agente ha finalizado. "
                f"Tiempo total: {elapsed:.2f} segundos."
            )
            return answer





        

        for call in tool_calls:
            name = call.function.name
            arguments = call.function.arguments or {}
            
            print(f"-> Ejecutando herramienta: {name}")
            print(f"   Argumentos: {arguments}")
            
            tool_start_time = time.perf_counter()
            result = execute_tool(name, arguments)
            executed_tools.add(name)
            tool_results[name] = result
            tool_duration = time.perf_counter() - tool_start_time

            print(f"<- Resultado obtenido (en {tool_duration:.4f}s): {result}")

            messages.append({
                "role": "tool",
                "tool_name": name,
                "content": str(result),
            })

        iter_duration = time.perf_counter() - iter_start_time
        print(f"Tiempo de la iteración {iteration + 1}: {iter_duration:.2f} segundos.")

    total_duration = time.perf_counter() - total_start_time
    return (
        f"No se obtuvo una respuesta final dentro del límite "
        f"de {MAX_ITERATIONS} iteraciones. (Tiempo transcurrido: {total_duration:.2f}s)"
    )


if __name__ == "__main__":
    question = (
        "Analiza las ventas de PROD-001 durante los dos últimos meses. "
        "Consulta también su inventario. Separa los hallazgos "
        "comprobados de las hipótesis y no inventes causas."
    )

    print("\nIniciando agente...")
    print(run_agent(question))