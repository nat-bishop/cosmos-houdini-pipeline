.PHONY: help install dev test lint format security clean pre-commit

help:  ## Show this help message
	@echo "Available commands:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

install:  ## Install production dependencies
	pip install -r requirements.txt

dev:  ## Install development dependencies
	pip install -r requirements-dev.txt
	pre-commit install

test:  ## Run tests with coverage
	pytest tests/ --cov=cosmos_workflow --cov-report=term-missing --cov-report=html

test-unit:  ## Run unit tests only
	pytest tests/ -m unit -v

test-integration:  ## Run integration tests only
	pytest tests/ -m integration -v

lint:  ## Run linting checks
	ruff check cosmos_workflow/ tests/
	mypy cosmos_workflow/

format:  ## Format code with Ruff
	ruff format cosmos_workflow/ tests/
	ruff check --fix cosmos_workflow/ tests/

security:  ## Run security checks
	bandit -r cosmos_workflow/ -c pyproject.toml
	safety check --json

clean:  ## Clean up cache and build files
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type f -name ".coverage" -delete
	rm -rf htmlcov/
	rm -rf .pytest_cache/
	rm -rf .mypy_cache/
	rm -rf .ruff_cache/
	rm -rf dist/
	rm -rf build/
	rm -rf *.egg-info

pre-commit:  ## Run pre-commit on all files
	pre-commit run --all-files

pre-commit-update:  ## Update pre-commit hooks
	pre-commit autoupdate

requirements:  ## Update requirements files
	pip freeze > requirements-freeze.txt

check-all:  ## Run all checks (lint, security, tests)
	$(MAKE) lint
	$(MAKE) security
	$(MAKE) test