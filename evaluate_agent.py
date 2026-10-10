import json
import re
import sys
from pathlib import Path

from agent import run_agent

CASES_PATH = Path(__file__).resolve().parent / "evaluation_cases.json"



def normalize(text: str) -> str:
    """Normalize number formatting and whitespace."""
    text = text.lower().replace("−", "-")

    # Normalize thousands separators: 4.500 -> 4500, 10,000 -> 10000.
    text = re.sub(r"(?<=\d)\.(?=\d{3}(?:\D|$))", "", text)
    text = re.sub(r"(?<=\d),(?=\d{3}(?:\D|$))", "", text)

    # Normalize numeric values such as -40.0 -> -40.
    text = re.sub(r"(?<=\d)\.0\b", "", text)

    return re.sub(r"\s+", "", text)



def evaluate_case(case: dict) -> bool:
    print(f"\n{'=' * 60}")
    print(f"Evaluating: {case['id']}")
    print(f"Question: {case['question']}")

    answer = run_agent(case["question"])
    normalized_answer = normalize(answer)

    # missing = [
    #     fact
    #     for fact in case["expected_facts"]
    #     if normalize(fact) not in normalized_answer
    # ]

    missing = []

    for alternatives in case["expected_facts"]:
        if isinstance(alternatives, str):
            alternatives = [alternatives]

        if not any(
            normalize(fact) in normalized_answer
            for fact in alternatives
        ):
            missing.append(alternatives)


    forbidden = case.get("forbidden_facts", [])
    found_forbidden = [
        phrase
        for phrase in forbidden
        if normalize(phrase) in normalized_answer
    ]

    if missing or found_forbidden:
        if missing:
            print(f"FAIL — missing expected facts: {missing}")
        if found_forbidden:
            print(f"FAIL — forbidden claims found: {found_forbidden}")
        print(f"Answer: {answer}")
        return False

    print("PASS — expected facts found; no forbidden claims detected.")
    return True

def main():
    with CASES_PATH.open(encoding="utf-8") as file:
        cases = json.load(file)

    results = [evaluate_case(case) for case in cases]
    passed = sum(results)

    print(f"\nEvaluation: {passed}/{len(results)} cases passed.")

    if passed != len(results):
        sys.exit(1)


if __name__ == "__main__":
    main()
