# Makefile for Flow Builder Engine development

.PHONY: install format lint test run-api

# Install dependencies
install:
	pip install -r requirements.txt

# Format code using black and isort
format:
	black backend/flow_engine
	isort backend/flow_engine

# Lint with flake8 and type-check with mypy
lint:
	flake8 backend/flow_engine
	mypy backend/flow_engine

# Run the test suite
test:
	pytest -q backend/flow_engine/tests

# Start the API for local dev (will add app in later step)
run-api:
	uvicorn backend.api:app --reload 