# ─────────────────────────────────────────────────────────────────────────────
# Makefile — shortcuts for common developer tasks
#
# What is a Makefile?
#   A Makefile contains "recipes" — named groups of shell commands.
#   Instead of typing long commands, you type: make <recipe-name>
#
# Usage:
#   make setup        → install all dependencies
#   make generate     → generate synthetic data
#   make detect       → run detection pipeline
#   make evaluate     → evaluate detection performance
#   make api          → start the FastAPI backend
#   make frontend     → start the React frontend
#   make test         → run all unit tests
#   make all          → generate + detect + evaluate (full pipeline)
# ─────────────────────────────────────────────────────────────────────────────

# Python executable — change this if your Python is at a different path
PYTHON = python3

# Database path
DB = data/aml.db

.PHONY: setup generate detect evaluate api frontend test all clean help

# Default target — show help
help:
	@echo ""
	@echo "AML Detection System — Make Commands"
	@echo "======================================"
	@echo "  make setup      Install Python and Node.js dependencies"
	@echo "  make generate   Generate 100k synthetic transactions"
	@echo "  make detect     Run detection pipeline (scores all accounts)"
	@echo "  make evaluate   Evaluate detection vs ground truth"
	@echo "  make api        Start FastAPI backend (port 8000)"
	@echo "  make frontend   Start React dashboard (port 5173)"
	@echo "  make test       Run all unit tests"
	@echo "  make all        Run generate + detect + evaluate"
	@echo "  make clean      Remove generated database"
	@echo ""

# Install all dependencies
setup:
	@echo "Installing Python dependencies..."
	pip install -r backend/requirements.txt
	@echo "Installing Node.js dependencies..."
	cd frontend && npm install
	@echo "Setup complete!"

# Generate synthetic data
generate:
	@echo "Generating synthetic AML data..."
	$(PYTHON) scripts/generate_data.py

# Run detection pipeline
detect:
	@echo "Running detection pipeline..."
	$(PYTHON) scripts/run_detection.py --top 20

# Evaluate detection performance
evaluate:
	@echo "Evaluating detection performance..."
	$(PYTHON) scripts/evaluate.py

# Run full pipeline
all: generate detect evaluate
	@echo "Full pipeline complete!"

# Start the FastAPI backend
api:
	@echo "Starting FastAPI backend at http://localhost:8000 ..."
	@echo "API docs available at http://localhost:8000/docs"
	uvicorn backend.api.main:app --reload --host 0.0.0.0 --port 8000

# Start the React frontend
frontend:
	@echo "Starting React dashboard at http://localhost:5173 ..."
	cd frontend && npm run dev

# Run unit tests
test:
	@echo "Running unit tests..."
	$(PYTHON) -m pytest backend/tests/ -v --tb=short

# Remove generated database (fresh start)
clean:
	@echo "Removing generated database..."
	rm -f $(DB)
	@echo "Database removed. Run 'make generate' to regenerate."

# Reset database to a clean state and re-seed system accounts
reset-db:
	@echo "Resetting database (all data will be lost)..."
	$(PYTHON) scripts/reset_db.py --confirm

# Export ground truth labels for evaluation
export-truth:
	@echo "Exporting ground truth labels..."
	$(PYTHON) scripts/export_ground_truth.py

# Run the performance benchmark
benchmark:
	@echo "Running pipeline benchmark..."
	$(PYTHON) scripts/benchmark.py

# Run tests with coverage report
test-cov:
	@echo "Running tests with coverage..."
	$(PYTHON) -m pytest backend/tests/ -v --tb=short --cov=backend --cov-report=term-missing

# Lint Python code
lint:
	@echo "Linting Python code..."
	python -m flake8 backend/ --max-line-length=100 --ignore=E501,W503

# Type-check Python code
typecheck:
	@echo "Type-checking Python code..."
	python -m mypy backend/ --ignore-missing-imports
