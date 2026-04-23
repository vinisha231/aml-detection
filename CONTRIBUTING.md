# Contributing to AML Detection System

## Setting up for development

```bash
# Clone the repo
git clone https://github.com/vinisha231/aml-detection.git
cd aml-detection

# Install everything
make setup

# Generate data and run detection
make all

# Start backend (separate terminal)
make api

# Start frontend (another separate terminal)
make frontend
```

## Project conventions

### Python (backend)
- All functions must have docstrings explaining WHAT and WHY
- Use type hints everywhere (Python 3.10+ syntax)
- Run tests before committing: `make test`
- Detection rules go in `backend/detection/rules/`
- Graph signals go in `backend/detection/graph/`
- Each new rule needs a corresponding test in `backend/tests/`

### TypeScript (frontend)
- All components are functional (no class components)
- Use React hooks: `useState`, `useEffect`, `useCallback`
- API calls always go through `src/api/client.ts`

### Commit format
```
<type>(<scope>): <short description>

Types: feat, fix, docs, test, chore, refactor
Scopes: gen, db, rules, graph, api, frontend, scripts, detection

Examples:
  feat(rules): add smurfing variant of structuring rule
  fix(graph): cap cycle detection at MAX_CYCLES_TO_PROCESS
  test(scoring): add pile-up bonus boundary test
  docs(read): add FinCEN advisory summary for 2024
```

## Adding a new typology

1. Add the generator: `backend/generator/typologies/my_typology.py`
2. Import it in `backend/generator/typologies/__init__.py`
3. Call it in `scripts/generate_data.py`
4. Add a detection rule: `backend/detection/rules/my_rule.py`
5. Import the rule in `backend/detection/rules/__init__.py`
6. Call the rule in `backend/pipeline.py`
7. Add tests: `backend/tests/test_my_rule.py`
8. Update the typology table in `README.md`

## Running tests

```bash
make test                           # run all tests
pytest backend/tests/test_scoring.py -v   # run one test file
pytest -k "test_detects" -v         # run tests matching a pattern
```
