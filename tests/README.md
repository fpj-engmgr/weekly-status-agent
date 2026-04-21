# Tests

This directory contains tests for the Weekly Status Agent.

## Unit Tests (pytest)

Run with `pytest tests/`:

- **test_auth.py** - Tests for authentication module
- **test_processor.py** - Tests for data processor
- **test_jira_collector.py** - Tests for Jira collector

## Integration Tests (standalone scripts)

Run individually with `python tests/<script_name>.py`:

- **test_gitlab_access.py** - Tests GitLab API connection, lists accessible projects, and fetches sample MRs
- **test_gitlab_prefixes.py** - Tests project prefix matching to verify which projects would be included
- **test_jira_claude.py** - End-to-end test of Jira collection + Claude AI analysis

## Setup Tests

- **scripts/test_setup.py** - Comprehensive setup verification (run from project root: `python scripts/test_setup.py`)

## Running Tests

```bash
# Unit tests
pytest tests/

# Integration tests
python tests/test_gitlab_access.py
python tests/test_gitlab_prefixes.py
python tests/test_jira_claude.py

# Setup verification
python scripts/test_setup.py
```
