# Contributing to yaml-workflow

Thank you for your interest in contributing! This guide will help you get started.

## Development Setup

```bash
# Clone the repository
git clone https://github.com/orieg/yaml-workflow.git
cd yaml-workflow

# Create a virtual environment
python -m venv .venv
source .venv/bin/activate

# Install with all development dependencies
pip install -e ".[dev,test,doc]"
```

## Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=yaml_workflow --cov-report=term-missing

# Run a specific test file
pytest tests/test_engine.py

# Type checking
mypy src/
```

## Code Style

This project uses **Black** for formatting and **isort** for import sorting:

```bash
black src/ tests/
isort src/ tests/
```

All code must pass `black`, `isort`, and `mypy` checks before merging.

## Commit Messages

We follow [Conventional Commits](https://www.conventionalcommits.org/):

- `feat:` New features
- `fix:` Bug fixes
- `docs:` Documentation changes
- `test:` Test additions or fixes
- `refactor:` Code refactoring
- `chore:` Maintenance tasks
- `ci:` CI/CD changes

## Pull Request Process

1. Fork the repository and create a feature branch from `main`
2. Write tests for any new functionality
3. Ensure all tests pass and code style checks are clean
4. Submit a pull request with a clear description of the changes

## Branch Naming

- `feature/` - New features
- `fix/` - Bug fixes
- `docs/` - Documentation
- `refactor/` - Code refactoring
- `test/` - Test improvements

## Detailed Guides

For more detailed development documentation, see:

- [Development Guide](https://orieg.github.io/yaml-workflow/contributing/development/)
- [Testing Guide](https://orieg.github.io/yaml-workflow/contributing/testing/)
- [Coding Standards](https://orieg.github.io/yaml-workflow/contributing/coding-standards/)
- [Pull Request Guidelines](https://orieg.github.io/yaml-workflow/contributing/pull-requests/)
