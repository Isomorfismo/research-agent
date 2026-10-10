# Local AI Research Agent

A local AI agent that analyzes sales and inventory data using Python, SQLite, and Ollama. It combines language-model tool calling with database-backed results and verified answers.

## Requirements

- Python 3.11 or a compatible version supported by the project
- [Ollama](https://ollama.com/)
- Git

## Setup

Create and activate a virtual environment:

```bash
python -m venv .venv
source .venv/bin/activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Pull the model used by the agent:

```bash
ollama pull qwen2.5:3b-instruct
```

Ensure Ollama is running before executing the agent.

## Initialize the database

```bash
python setup_db.py
```

This creates the local SQLite database used for sales and inventory queries.

## Run the agent

```bash
python agent.py
```

## Run tests

```bash
pytest -q
```

## Run evaluations

```bash
python evaluate_agent.py
```

## Project structure

- `agent.py` — agent loop, tool execution, and verified-answer construction.
- `database.py` — validated SQLite queries for sales and inventory.
- `setup_db.py` — local database initialization and sample data.
- `tests/` — automated unit and integration-simulation tests.
- `evaluation_cases.json` — expected facts and prohibited claims for evaluation.
- `evaluate_agent.py` — evaluation runner.
- `research.db` — generated local database; excluded from version control.

## Current status

The agent has automated tests for database operations, argument validation, tool execution, and verified-answer construction. The evaluation suite checks whether responses contain expected facts and avoid unsupported causal claims.

## Design principles

- Run inference locally with Ollama.
- Use SQLite as the source of truth for sales and inventory.
- Validate tool inputs before querying the database.
- Prefer evidence-backed answers over unsupported model-generated claims.
- Test behavior before adding orchestration complexity.
