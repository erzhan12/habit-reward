.PHONY: help install sync dev-install test test-cov bot dashboard clean lint format check

# Default target - show help
help:
	@echo "Habit Reward System - Available Commands"
	@echo "========================================"
	@echo ""
	@echo "Setup & Installation:"
	@echo "  make install      - Install uv and sync dependencies"
	@echo "  make sync         - Sync dependencies with uv"
	@echo "  make dev-install  - Install development dependencies (pytest, ruff, etc.)"
	@echo ""
	@echo "Running Services:"
	@echo "  make bot          - Run the Telegram bot"
	@echo "  make dashboard    - Run the Streamlit dashboard"
	@echo ""
	@echo "Testing:"
	@echo "  make test         - Run all tests"
	@echo "  make test-cov     - Run tests with coverage report"
	@echo ""
	@echo "Code Quality:"
	@echo "  make lint         - Run linter (ruff)"
	@echo "  make format       - Format code (ruff)"
	@echo "  make check        - Run format check without modifying files"
	@echo ""
	@echo "Cleanup:"
	@echo "  make clean        - Remove cache files and build artifacts"

# Install uv (if needed) and sync dependencies
install:
	@echo "Installing dependencies with uv..."
	@command -v uv >/dev/null 2>&1 || { echo "Installing uv..."; curl -LsSf https://astral.sh/uv/install.sh | sh; }
	uv sync

# Sync dependencies
sync:
	@echo "Syncing dependencies..."
	uv sync

# Install development dependencies
dev-install:
	@echo "Installing development dependencies..."
	uv add --dev ruff pytest pytest-asyncio pytest-cov
	@echo "Development dependencies installed!"

# Run tests
test:
	@echo "Running tests..."
	uv run pytest tests/

# Run tests with coverage
test-cov:
	@echo "Running tests with coverage..."
	uv run pytest --cov=src tests/
	@echo ""
	@echo "For detailed HTML coverage report, run:"
	@echo "  uv run pytest --cov=src --cov-report=html tests/"

# Run Telegram bot
bot:
	@echo "Starting Telegram bot..."
	uv run python -m src.bot.main

# Run Streamlit dashboard
dashboard:
	@echo "Starting Streamlit dashboard..."
	uv run streamlit run src/dashboard/app.py

# Lint code
lint:
	@echo "Linting code..."
	@if uv run ruff --version >/dev/null 2>&1; then \
		uv run ruff check src/ tests/; \
	else \
		echo "❌ ruff is not installed. Run 'make dev-install' to install development tools."; \
		exit 1; \
	fi

# Format code
format:
	@echo "Formatting code..."
	@if uv run ruff --version >/dev/null 2>&1; then \
		uv run ruff format src/ tests/; \
	else \
		echo "❌ ruff is not installed. Run 'make dev-install' to install development tools."; \
		exit 1; \
	fi

# Check formatting without modifying
check:
	@echo "Checking code format..."
	@if uv run ruff --version >/dev/null 2>&1; then \
		uv run ruff check src/ tests/ --diff; \
	else \
		echo "❌ ruff is not installed. Run 'make dev-install' to install development tools."; \
		exit 1; \
	fi

# Clean cache and build artifacts
clean:
	@echo "Cleaning cache and build artifacts..."
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	find . -type f -name "*.pyo" -delete 2>/dev/null || true
	find . -type d -name ".coverage" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name ".coverage" -delete 2>/dev/null || true
	find . -type d -name "htmlcov" -exec rm -rf {} + 2>/dev/null || true
	@echo "Clean complete!"

