# Contributing to QCA

Thank you for your interest in contributing to QCA! This guide will help you set up your development environment and understand our contribution workflow.

## Development Environment Setup

### Prerequisites

- **Python**: 3.11 or higher (3.12 recommended)
- **Git**: For version control
- **UV** (optional): For faster dependency management

### Initial Setup

1. **Clone the repository**:
   ```bash
   git clone https://github.com/NVIDIA/ising-calibration-agent-cookbook.git qca
   cd qca
   ```

2. **Create a virtual environment**:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. **Install in development mode**:
   ```bash
   pip install -e .
   ```

4. **Install development dependencies**:
   ```bash
   pip install -e ".[test]"
   ```

5. **Set up environment variables**:
   ```bash
   cp .env.example .env
   # Edit .env with your API keys and configuration
   ```

6. **Verify installation**:
   ```bash
   qca --help
   pytest tests/unit/
   ```

### Project Structure

Understanding the project layout:

```
qca/
├── cli.py                  # Main CLI entry point
├── server.py              # FastAPI server (optional)
├── prompt.py              # Agent system prompt
├── config.yaml            # DeepAgents configuration
├── tools/                 # DeepAgents tools
│   ├── lab_tool.py       # Experiment management
│   ├── workflow_tool.py  # Workflow operations
│   └── vlm_tool.py       # Vision language model
├── core/                  # Core library
│   ├── discovery.py      # Experiment discovery
│   ├── runner.py         # Experiment execution
│   ├── storage.py        # Data persistence
│   └── models.py         # Data models
├── scripts/               # Experiment implementations
│   ├── qubit_spectroscopy.py
│   ├── rabi_oscillation.py
│   └── ...
├── tests/                 # Test suite
│   ├── unit/             # Unit tests
│   ├── integration/      # Integration tests
│   └── conftest.py       # Pytest fixtures
└── cookbook/              # Documentation and runtime data
    ├── data/             # Runtime data
    │   ├── experiments/  # Stored experiments
    │   ├── workflows/    # Workflow definitions
    │   └── knowledge/    # Agent knowledge base
    └── ...
```

## Code Style Guidelines

### Python Conventions

We follow PEP 8 with some project-specific conventions:

#### Formatting

- **Line length**: 88 characters (Black default)
- **Indentation**: 4 spaces
- **Quotes**: Double quotes for strings
- **Imports**: Organized by standard library, third-party, local

#### Naming Conventions

- **Functions/variables**: `snake_case`
- **Classes**: `PascalCase`
- **Constants**: `UPPER_SNAKE_CASE`
- **Private members**: `_leading_underscore`

#### Type Hints

Always use type hints for function signatures:

```python
def run_experiment(
    experiment_name: str,
    params: dict[str, Any],
    simulated: bool = False
) -> ExperimentResult:
    """Execute an experiment with given parameters."""
    ...
```

#### Docstrings

Use Google-style docstrings:

```python
def save_experiment(result: ExperimentResult, data_dir: Path) -> str:
    """Save experiment result to storage.

    Args:
        result: The experiment result to save
        data_dir: Directory for data storage

    Returns:
        The experiment ID

    Raises:
        ValueError: If result is invalid
        IOError: If storage operation fails
    """
    ...
```

### Experiment Scripts

Experiment scripts must follow this pattern:

```python
from typing import Annotated

def experiment_name(
    param1: Annotated[float, (min_val, max_val)] = default,
    param2: Annotated[int, (min_val, max_val)] = default,
    param3: Annotated[str, ["option1", "option2"]] = "option1",
) -> dict:
    """Brief description of experiment.

    Detailed explanation of what this experiment does,
    what it measures, and what the results mean.

    Args:
        param1: Description of parameter 1
        param2: Description of parameter 2
        param3: Description of parameter 3

    Returns:
        Dictionary with 'status', 'data', 'arrays', and 'plots'
    """
    # Implementation
    return {
        "status": "success",
        "data": {"result_key": result_value},
        "arrays": {"array_name": array_data},
        "plots": [plot_definition]
    }
```

**Key requirements**:
- Use `Annotated` type hints for all parameters
- Include parameter constraints (ranges or choices)
- Provide default values
- Return dict with standard keys
- Include comprehensive docstring

### Tool Development

Tools must implement the DeepAgents tool interface:

```python
from typing import Any

def tool_action(param1: str, param2: int = 0) -> dict[str, Any]:
    """Action description for the AI agent.

    Args:
        param1: Description visible to agent
        param2: Optional parameter description

    Returns:
        Result dictionary with relevant data
    """
    # Implementation
    return {"status": "success", "data": {...}}
```

**Tool guidelines**:
- Clear, descriptive function names
- Docstrings optimized for AI understanding
- Structured return values
- Proper error handling

## Git Workflow

### Branching Strategy

- **main**: Stable, production-ready code
- **feature/**: New features (`feature/add-experiment-x`)
- **fix/**: Bug fixes (`fix/storage-crash`)
- **docs/**: Documentation updates (`docs/api-reference`)

### Commit Messages

Follow conventional commit format:

```
<type>(<scope>): <subject>

<body>

<footer>
```

**Types**:
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `test`: Adding or updating tests
- `refactor`: Code refactoring
- `perf`: Performance improvements
- `chore`: Maintenance tasks

**Examples**:
```
feat(experiments): add T2 echo measurement

Implements T2 echo experiment with Hahn echo sequence.
Includes parameter validation and result plotting.

Closes #42
```

```
fix(storage): prevent duplicate experiment IDs

Generate unique IDs using timestamp + random suffix.
Adds collision detection and retry logic.
```

### Making Changes

1. **Create a branch**:
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make your changes**:
   - Write code following style guidelines
   - Add or update tests
   - Update documentation if needed

3. **Run tests**:
   ```bash
   pytest tests/
   ```

4. **Check coverage**:
   ```bash
   pytest --cov=core --cov=tools --cov=scripts tests/
   ```

5. **Commit your changes**:
   ```bash
   git add specific_files  # Don't use git add -A
   git commit -m "feat(scope): description"
   ```

6. **Push to remote**:
   ```bash
   git push origin feature/your-feature-name
   ```

## Pull Request Process

### Before Submitting

- [ ] All tests pass
- [ ] Coverage maintained or improved
- [ ] Code follows style guidelines
- [ ] Documentation updated
- [ ] Commit messages are clear
- [ ] Branch is up to date with main

### Creating the PR

1. **Go to GitHub** and create a pull request
2. **Fill out the template**:
   - Summary of changes
   - Related issues
   - Testing performed
   - Screenshots (if UI changes)

3. **Example PR description**:
   ```markdown
   ## Summary
   Adds support for T2 echo measurements using Hahn echo sequence.

   ## Changes
   - New experiment script: `scripts/t2_echo.py`
   - Updated discovery to handle echo parameters
   - Added unit tests with 100% coverage

   ## Testing
   - Unit tests: All passing
   - Manual testing: Verified in simulated mode
   - Coverage: 98% for new script

   ## Related Issues
   Closes #42
   ```

### Review Process

1. **Automated checks run**:
   - Unit tests
   - Integration tests
   - Coverage report

2. **Reviewer provides feedback**:
   - Code quality
   - Test coverage
   - Documentation completeness

3. **Address feedback**:
   - Make requested changes
   - Respond to comments
   - Push updates to same branch

4. **Approval and merge**:
   - Maintainer approves
   - PR merged to main
   - Branch deleted

## Code Review Expectations

### As an Author

- Respond to feedback promptly
- Explain design decisions clearly
- Be open to suggestions
- Keep PRs focused and sized reasonably
- Update based on feedback

### As a Reviewer

- Be respectful and constructive
- Focus on code quality and correctness
- Suggest improvements, don't demand perfection
- Approve when ready, request changes when needed
- Test changes locally if possible

## Issue Guidelines

### Reporting Bugs

Use the bug report template:

```markdown
**Describe the bug**
Clear description of what's wrong.

**To Reproduce**
Steps to reproduce:
1. Run command '...'
2. See error

**Expected behavior**
What should have happened.

**Actual behavior**
What actually happened.

**Environment**
- OS: Ubuntu 22.04
- Python: 3.12
- QCA: v0.1.0

**Additional context**
Error messages, logs, screenshots.
```

### Requesting Features

Use the feature request template:

```markdown
**Feature description**
Clear description of the desired feature.

**Use case**
Why is this needed? What problem does it solve?

**Proposed solution**
How might this be implemented?

**Alternatives considered**
Other approaches you've thought about.
```

### Working on Issues

1. **Comment on the issue** to indicate you're working on it
2. **Reference the issue** in your commits and PR
3. **Update the issue** with progress or blockers

## Development Tips

### Running Specific Tests

```bash
# Single test file
pytest tests/unit/test_discovery.py

# Single test function
pytest tests/unit/test_discovery.py::test_discover_experiments

# Tests matching pattern
pytest -k "discovery"

# With coverage
pytest --cov=core tests/unit/
```

### Debugging

```bash
# Run with verbose output
pytest -v tests/

# Show print statements
pytest -s tests/

# Drop into debugger on failure
pytest --pdb tests/
```

## Testing

QCA uses **pytest** for testing. Run `pytest` to execute all tests, or `pytest --cov=core --cov=tools` for coverage reports. Tests are organized in `tests/unit/` for unit tests and `tests/integration/` for integration tests. Use the fixtures in `tests/conftest.py` for common test setup like temporary directories and sample data.

## Common Contribution Scenarios

### Adding a New Experiment

1. Create script in `scripts/`
2. Use Annotated type hints
3. Write comprehensive docstring
4. Add unit test in `tests/unit/test_scripts.py`
5. Test with simulated execution
6. Update documentation

### Fixing a Bug

1. Write a test that reproduces the bug
2. Fix the bug
3. Verify test now passes
4. Add regression test if needed
5. Document the fix in PR

### Improving Documentation

1. Identify gap or inaccuracy
2. Update relevant .md files
3. Verify examples still work
4. Submit PR with clear description

### Adding a Tool Action

1. Add function to appropriate tool file
2. Follow tool interface pattern
3. Write unit tests
4. Update tool documentation
5. Test with agent interaction

## Getting Help

- **Questions**: Open a discussion on GitHub
- **Bugs**: File an issue with details
- **Ideas**: Start a feature request discussion
- **Urgent**: Contact maintainers directly

## Recognition

Contributors are recognized in:
- Commit history
- Release notes
- Contributors list (planned)

Thank you for contributing to QCA!
