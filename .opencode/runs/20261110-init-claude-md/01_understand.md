# UNDERSTAND

## FACTS
- Existing `CLAUDE.md` is Ruflo/swarm guidance and incorrectly documents `npm run build && npm test` for this Python project (`CLAUDE.md:1-175`).
- Python 3.11+ project; dependencies and pytest configuration are declared in `pyproject.toml:5-23,73-75` and `requirements.txt:5-50`.
- CI installs requirements, runs selected mypy, blocking flake8, pytest+coverage, then formatting/import/full-flake8 checks (`.github/workflows/ci.yml:30-77`).
- Production entrypoint imports `src.api.main:app` and serves port 7860 (`entrypoint.py:7-15`).
- API requires `FASTAPI_API_KEY` and mounts domain routers (`src/api/main.py:24-30,268-279`).
- Live execution is fail-closed behind mode, flag, adapter, and readiness gate (`src/execution/order_manager.py:19-60`; `src/utils/readiness_gate.py:32-70`).
- Central configuration loads process env before `config/.env`/root `.env` (`src/utils/config.py:18-30`).
- No Cursor or Copilot instruction files were found by repository globs.
- User-level Codex and Gemini configs exist; their contents were not read.

## HYPOTHESES
- Future agents benefit from emphasizing wired entrypoints because the repository contains parallel and legacy implementations.
- A concise architecture/data-flow description is more useful than reproducing the README tree.

## UNKNOWNS
- Full-suite baseline result is pending because network-dependent tests exceeded the initial 600-second foreground window.
- Formatter/import checker availability differs from CI; local Python lacks `black`, `isort`, and `flake8` until dev tools are installed.
