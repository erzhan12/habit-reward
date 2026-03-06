# Development Workflows

## Run
```bash
uvicorn asgi:app --reload --port 8000   # Django + FastAPI (web + API)
uv run python src/bot/main.py           # Telegram bot
```

## Lint
```bash
uv run ruff check src/                  # Check
uv run ruff check src/ --fix            # Auto-fix
```

## Test
```bash
uv run pytest tests/ -v                         # All tests
uv run pytest tests/test_file.py -v              # Specific file
uv run pytest --cov=src tests/                   # Coverage
uv run pytest tests/ -v -m "not local_only"      # CI mode
```

## Frontend
```bash
cd frontend && npm run dev              # Dev server
cd frontend && npm run build            # Production build
cd frontend && npx vitest               # Frontend tests
```
