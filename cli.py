import argparse
import sys
from agent import agent_graph as graph, AgentState
from database import get_sales_summary, get_inventory_status


def run_agent_query(question: str):
    """Ejecuta el agente LangGraph con una pregunta dada."""
    print(f"\n[AGENTE] Analizando pregunta: \"{question}\"")
    print("-" * 60)

    initial_state: AgentState = {
        "messages": [{"role": "user", "content": question}],
        "question": question,
        "iterations": 0,
        "tool_calls": [],
        "tool_results": {},
        "executed_tools": [],
        "required_tools": [],
        "answer": "",
    }

    try:
        final_state = graph.invoke(initial_state)
        print("\nRespuesta final:")
        print(final_state.get("answer", "No se obtuvo respuesta."))
    except Exception as e:
        print(f"\n[ERROR] Ocurrió un error al ejecutar el grafo: {e}", file=sys.stderr)
    print("-" * 60)

def main():
    parser = argparse.ArgumentParser(
        description="CLI para el Agente de Investigación de Ventas e Inventario."
    )
    subparsers = parser.add_subparsers(dest="command", help="Comandos disponibles")

    # Comando para hacer una pregunta al agente
    ask_parser = subparsers.add_parser("ask", help="Realizar una pregunta al agente.")
    ask_parser.add_argument("question", type=str, help="Pregunta o instrucción para el agente.")

    # Comando para consultar ventas directamente
    sales_parser = subparsers.add_parser("sales", help="Consultar resumen de ventas de un producto.")
    sales_parser.add_argument("--product", type=str, default="PROD-001", help="ID del producto (ej. PROD-001).")
    sales_parser.add_argument("--months", type=int, default=2, help="Número de meses a consultar.")

    # Comando para consultar inventario directamente
    inv_parser = subparsers.add_parser("inventory", help="Consultar estado del inventario de un producto.")
    inv_parser.add_argument("--product", type=str, default="PROD-001", help="ID del producto (ej. PROD-001).")

    args = parser.parse_args()

    if args.command == "ask":
        run_agent_query(args.question)
    elif args.command == "sales":
        result = get_sales_summary(product_id=args.product, months=args.months)
        print(f"\nResultado de Ventas ({args.product}):")
        for k, v in result.items():
            print(f"  - {k}: {v}")
    elif args.command == "inventory":
        result = get_inventory_status(product_id=args.product)
        print(f"\nResultado de Inventario ({args.product}):")
        for k, v in result.items():
            print(f"  - {k}: {v}")
    else:
        parser.print_help()

if __name__ == "__main__":
    main()