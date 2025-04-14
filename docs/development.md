# Development Guide

## Setup

1. Install development dependencies:
```bash
pip install -e ".[dev]"
```

2. Format code:
```bash
# Format Python files
black src/ tests/  # Code formatting
isort --profile black src/ tests/  # Import sorting (using black-compatible settings)

# Run both formatters in one command
black src/ tests/ && isort --profile black src/ tests/
```

3. Type checking:
```bash
mypy src/
```

## Building and Distribution

1. Ensure you have the latest build tools:
```bash
python -m pip install --upgrade pip
python -m pip install --upgrade build twine
```

2. Build both source distribution (sdist) and wheel:
```bash
# This will create both sdist and wheel in the dist/ directory
python -m build

# Or build them separately:
python -m build --sdist  # Create source distribution
python -m build --wheel  # Create wheel
```

3. Check your distribution files:
```bash
# Validate distribution files
twine check dist/*
```

4. Upload to TestPyPI first (recommended):
```bash
# Upload to TestPyPI
twine upload --repository testpypi dist/*

# Install from TestPyPI to test
pip install --index-url https://test.pypi.org/simple/ yaml-workflow
```

5. Upload to PyPI:
```bash
# Upload to PyPI
twine upload dist/*
```

## Running Tests

```bash
# Install test dependencies
pip install -e ".[test]"

# Run tests
pytest tests/

# Run tests with coverage
pytest tests/ --cov=yaml_workflow
```

## Testing Releases

### Method 1: Local Build Testing

1. Install development dependencies (includes build tools):
```bash
# This will install all development dependencies including build and twine
pip install -e ".[dev]"
```

2. Clean previous builds:
```bash
rm -rf dist/ build/ *.egg-info
```

3. Build the package:
```bash
python -m build
```

4. Check the distribution files:
```bash
twine check dist/*
```

5. Install the built package locally:
```bash
# Create a new virtual environment for testing
python -m venv test-venv
source test-venv/bin/activate  # On Unix/macOS
# On Windows use: test-venv\Scripts\activate

# Install and test the package
pip install dist/*.whl
yaml-workflow init --example hello_world
yaml-workflow run workflows/hello_world.yaml name=Test
```

### Method 2: Using TestPyPI

1. Register an account on TestPyPI:
   - Go to https://test.pypi.org/account/register/
   - Create an account
   - Generate an API token

2. Create a `.pypirc` file in your home directory:
```ini
[distutils]
index-servers =
    testpypi

[testpypi]
repository = https://test.pypi.org/legacy/
username = __token__
password = your-test-pypi-token
```

3. Build and upload to TestPyPI:
```bash
# Clean previous builds
rm -rf dist/ build/ *.egg-info

# Build the package
python -m build

# Upload to TestPyPI
twine upload --repository testpypi dist/*
```

4. Test installation from TestPyPI:
```bash
# Create a new virtual environment for testing
python -m venv test-venv
source test-venv/bin/activate  # On Unix/macOS
# On Windows use: test-venv\Scripts\activate

# Install from TestPyPI
pip install --index-url https://test.pypi.org/simple/ \
    --extra-index-url https://pypi.org/simple/ \
    yaml-workflow

# Test the package
yaml-workflow init --example hello_world
yaml-workflow run workflows/hello_world.yaml name=Test
```

Note: The `--extra-index-url` is needed because TestPyPI doesn't have all the dependencies.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests and ensure all checks pass
5. Submit a pull request

## Package Configuration

The package uses `pyproject.toml` for configuration. Here's the minimum required configuration:

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "yaml-workflow"
version = "0.1.0"
description = "A powerful and flexible workflow engine that executes tasks defined in YAML configuration files"
readme = "README.md"
authors = [
    { name = "Your Name", email = "your.email@example.com" }
]
license = { file = "LICENSE" }
classifiers = [
    "Programming Language :: Python :: 3",
    "License :: OSI Approved :: MIT License",
    "Operating System :: OS Independent",
]
dependencies = [
    "pyyaml>=6.0",
    "jinja2>=3.0",
]

[project.optional-dependencies]
test = [
    "pytest>=7.0",
    "pytest-cov>=4.0",
]
dev = [
    "black>=23.0",
    "isort>=5.0",
    "mypy>=1.0",
]

[project.urls]
Homepage = "https://github.com/yourusername/yaml-workflow"
Issues = "https://github.com/yourusername/yaml-workflow/issues"

[project.scripts]
yaml-workflow = "yaml_workflow.cli:main"

[tool.isort]
profile = "black"
multi_line_output = 3
include_trailing_comma = true
force_grid_wrap = 0
use_parentheses = true
ensure_newline_before_comments = true
line_length = 88  # Match black's line length
``` 