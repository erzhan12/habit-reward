# Repository Guidelines

## Project Structure & Module Organization
The Python 3.13 codebase centers on `src/`, which holds domain-driven packages: `bot/` for Telegram handlers, `services/` for business logic, `airtable/` repositories, `dashboard/` for Streamlit UI, and `habit_reward_project/` for Django transition scaffolding. Shared helpers live in `utils/` and `config.py`. Unit tests mirror this layout inside `tests/`, while operational docs are under `docs/` and reusable CLI helpers live in `commands/` and `scripts/`. Static dashboard artifacts reside in `staticfiles/`.

## Build, Test, and Development Commands
Prefer the Make targets: `make sync` installs dependencies with `uv`, `make bot` runs `uv run python -m src.bot.main`, and `make dashboard` starts Streamlit. Use `make lint`, `make format`, and `make check` for Ruff enforcement. Shell shortcuts `run_bot.sh` and `run_dashboard.sh` are available for quick local smoke checks.

## Coding Style & Naming Conventions
Adhere to PEP 8 with 4-space indentation and descriptive snake_case names for modules, functions, and variables. Services should remain framework-neutral and keep Telegram specifics in `src/bot/` as reinforced by `RULES.md`. All user-facing strings must come from `src/bot/messages.py`, and handlers must follow the user validation pattern documented there. Type hints are expected across new code paths.

## Testing Guidelines
Pytest (with `pytest-asyncio`) powers the suite; keep async tests using the event loop fixtures already defined in `tests/conftest.py`. Name new files `test_<feature>.py` alongside the module they cover. Run `uv run pytest tests/` before every PR and use `uv run pytest --cov=src tests/` to meet the existing coverage baseline. Capture critical bot flows with fixture-backed service mocks rather than Airtable calls.

## Commit & Pull Request Guidelines
Write imperative, present-tense commit subjects capped around 72 characters; prefix with Conventional Commit types (`feat:`, `fix:`, `chore:`) where it clarifies scope, matching recent history. Each PR should explain the business context, list validation steps (e.g., `make test`), and link any relevant docs updates or issues. Attach screenshots or bot transcript snippets when UI or conversational changes are involved.

## Security & Configuration Tips
Secrets stay in `.env`; start from `.env.example` and never commit credentials or database dumps. Review `src/config.py` for the authoritative settings schema before adding new environment flags. If you touch authentication or messaging flows, cross-check `RULES.md` to preserve user gating and multilingual support.
