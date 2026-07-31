# Repository Guidelines

## Project Structure & Module Organization

CLARA separates its Python service from its browser client. `loan_pipeline/` contains the application logic: `agents/` for specialist agents, `graph/` for LangGraph state and orchestration, `api/` for FastAPI and SSE endpoints, `llm/` for model access, and `eval/`, `guardrails/`, `review/`, and `data/` for their respective domains. The Next.js interface lives in `web/`. Python tests use `tests/test_*.py`; operational utilities belong in `scripts/`; sample inputs live in `sample_documents/`; documentation belongs in `docs/`.

Keep changes within the module that owns the behavior. Add or update a corresponding test whenever behavior changes.

## Build, Test, and Development Commands

Run these from PowerShell at the repository root:

- `.\.venv\Scripts\python.exe -m pip install -r requirements.txt` installs backend dependencies.
- `.\.venv\Scripts\python.exe -m uvicorn loan_pipeline.api.app:app --reload --port 8000` starts the FastAPI backend.
- `cd web; npm.cmd install; npm.cmd run dev` installs and starts the Next.js UI.
- `.\.venv\Scripts\python.exe -m pytest` runs the complete Python test suite.
- `.\.venv\Scripts\python.exe -m ruff check loan_pipeline tests` runs Python lint checks.
- `cd web; npm.cmd run lint; npm.cmd run build` validates and builds the frontend.
- `docker compose up --build` builds and runs the containerized stack.

## Coding Style & Naming Conventions

Use four-space indentation, type hints, `snake_case` functions/modules, `PascalCase` classes, and uppercase constants in Python. Keep imports Ruff-compatible. In TypeScript, use two spaces, `PascalCase` React components, and `camelCase` variables and hooks. Prefer small, typed functions and structured models over loosely shaped dictionaries.

## Testing Guidelines

Use `pytest`; API tests should use FastAPI's `TestClient`. Name tests `test_<expected_behavior>`. Run focused tests first, for example `pytest tests/test_api_streaming.py`, then the full suite. Graph changes must cover node failures, state validation, parallel branches, and SSE event ordering.

## Commit & Pull Request Guidelines

Use concise conventional prefixes such as `feat:`, `fix:`, `test:`, `docs:`, and `chore:`. Pull requests should describe behavior, risk, verification commands, and configuration changes. Link related issues and include screenshots for UI changes.

## Security & Agent Architecture

Never commit `.env`, API keys, borrower data, or generated review packets. Document new variables in `.env.example`. Treat uploaded documents and model output as untrusted. Preserve schema validation, guardrails, human approval gates, structured errors, and the typed graph-state contract between agents.
