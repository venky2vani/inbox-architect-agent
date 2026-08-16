---
name: run-tests
description: Run the test suite with coverage reporting and filtering options
allowed-tools: Bash(pytest *)
---

## Test Environment Check

!`cd ${CLAUDE_PROJECT_DIR} && source .venv/bin/activate 2>/dev/null && python -m pytest --version 2>/dev/null || echo "pytest not installed"`

## Available Tests

!`cd ${CLAUDE_PROJECT_DIR} && find tests/ -name "test_*.py" -type f | sed 's|tests/||; s|.py$||' | sort`

## Task

Run tests for the Inbox Architect Agent. Choose your approach:

1. **All tests** — Run complete test suite with coverage
2. **Specific test file** — Run tests in a single module (e.g., test_gmail_connector)
3. **Fail fast** — Stop at first failure for rapid iteration
4. **Coverage report** — Generate HTML coverage report

### All Tests
```bash
cd ${CLAUDE_PROJECT_DIR} && source .venv/bin/activate && python -m pytest tests/ -v
```

### All Tests with Coverage
```bash
cd ${CLAUDE_PROJECT_DIR} && source .venv/bin/activate && python -m pytest tests/ -v --cov=. --cov-report=html
```

### Specific Test File
```bash
cd ${CLAUDE_PROJECT_DIR} && source .venv/bin/activate && python -m pytest tests/test_NAME.py -v
```

### Fail Fast (stop on first failure)
```bash
cd ${CLAUDE_PROJECT_DIR} && source .venv/bin/activate && python -m pytest tests/ -x -v
```

### Watch Mode (rerun on file changes)
```bash
cd ${CLAUDE_PROJECT_DIR} && source .venv/bin/activate && python -m pytest tests/ -v --tb=short -l
```

After a coverage run, open `htmlcov/index.html` to see the report.