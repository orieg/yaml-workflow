# Dependencies

YAML Workflow is designed with modularity in mind, allowing you to install only the dependencies you need for your specific use case.

## Core Dependencies

These dependencies are always installed with the package:

```toml
dependencies = [
    "pyyaml>=6.0,<7.0",    # YAML parsing and writing
    "jinja2>=3.0,<4.0",    # Template processing
    "click>=8.0,<9.0",     # CLI interface
]
```

## Optional Dependencies

### Testing Dependencies

Required for running tests and development:

```toml
[project.optional-dependencies]
test = [
    "pytest>=7.0,<8.0",        # Testing framework
    "pytest-cov>=4.0,<5.0",    # Test coverage
    "mypy>=1.0,<2.0",         # Type checking
    "types-PyYAML>=6.0,<7.0", # Type stubs for PyYAML
]
```

Install with:
```bash
pip install yaml-workflow[test]
```

### Documentation Dependencies

Required for building documentation:

```toml
[project.optional-dependencies]
doc = [
    "mkdocs>=1.6.0,<2.0",                 # Documentation generator
    "mkdocs-material>=9.6.0,<10.0",       # Material theme
    "mkdocstrings[python]>=0.29.0,<1.0",  # Python API documentation
    "griffe>=0.49.0",                     # Code parsing
    "docstring-parser>=0.16.0,<1.0",      # Docstring parsing
    "mkdocs-gen-files>=0.5.0,<1.0",       # File generation
    "mkdocs-literate-nav>=0.6.0,<1.0",    # Navigation
    "mkdocs-section-index>=0.3.0,<1.0"    # Section indexing
]
```

Install with:
```bash
pip install yaml-workflow[doc]
```

### Development Dependencies

Required for development work:

```toml
[project.optional-dependencies]
dev = [
    "black==25.1.0",           # Code formatting
    "isort>=5.0,<6.0",        # Import sorting
    "build>=1.0.0,<2.0.0",    # Package building
    "twine>=4.0.0,<5.0.0"     # Package publishing
]
```

Install with:
```bash
pip install yaml-workflow[dev]
```

## Feature Dependencies

### Basic Features

Core features work with the base installation:
- YAML workflow definition
- Basic task types (echo, shell, etc.)
- Template processing
- File operations
- CLI interface

### Advanced Features

Some advanced features require optional dependencies:

#### Parallel Processing
- Uses Python's built-in `concurrent.futures`
- No additional dependencies required
- Configure with `parallel: true` and `max_workers`

#### State Management
- Uses local file system
- JSON/YAML for state storage
- No additional dependencies required

#### Custom Task Types
- Python module importing
- Dynamic code loading
- Core functionality included

## Python Version Compatibility

YAML Workflow is tested and supported on:
- Python 3.10
- Python 3.11
- Python 3.12
- Python 3.13

## Operating System Support

The package is platform-independent and tested on:
- Linux
- macOS
- Windows

## Installing Multiple Extras

You can combine optional dependencies:

```bash
# Install all development-related packages
pip install yaml-workflow[test,dev,doc]

# Install specific combinations
pip install yaml-workflow[test,dev]
```

## Dependency Management

### Version Constraints
- All dependencies use semantic versioning
- Upper bounds prevent breaking changes
- Lower bounds ensure feature availability

### Updating Dependencies
```bash
# Update all dependencies
pip install --upgrade yaml-workflow[all]

# Update specific group
pip install --upgrade yaml-workflow[dev]
```

### Dependency Conflicts
If you encounter dependency conflicts:
1. Install minimal required dependencies first
2. Add optional dependencies one by one
3. Use `pip freeze` to check versions
4. Report conflicts in GitHub issues 