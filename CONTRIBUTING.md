# Contributing to The Sentinel

Thank you for your interest in contributing to The Sentinel! 🛡️

## Development Setup

### Prerequisites

- Python 3.9 or higher
- Chrome browser
- Git

### Local Development

1. **Clone the repository**
   ```bash
   git clone https://github.com/godhiraj-code/sentinel.git
   cd sentinel
   ```

2. **Create a virtual environment**
   ```bash
   python -m venv .venv
   
   # Windows
   .venv\Scripts\activate
   
   # macOS/Linux
   source .venv/bin/activate
   ```

3. **Install development dependencies**
   ```bash
   pip install -e ".[dev]"
   ```

4. **Verify installation**
   ```bash
   sentinel doctor
   ```

---

## Project Structure

```
the-sentinel/
├── sentinel/               # Main package
│   ├── __init__.py         # Public API exports
│   ├── cli/                # Command-line interface
│   │   └── main.py         # Click-based CLI
│   ├── core/               # Core orchestration
│   │   ├── orchestrator.py # Main controller
│   │   └── driver_factory.py # Driver creation
│   ├── layers/             # Functional layers
│   │   ├── sense/          # DOM mapping, visual analysis
│   │   ├── action/         # Execution, teleportation
│   │   ├── intelligence/   # Decision making
│   │   └── validation/     # UI mutation testing
│   └── reporters/          # Report generation
├── tests/                  # Test suite
│   ├── unit/               # Unit tests
│   └── integration/        # Integration tests
├── examples/               # Usage examples
├── docs/                   # Documentation
└── pyproject.toml          # Project configuration
```

---

## Coding Standards

### Python Style

- Follow **PEP 8** conventions
- Use **type hints** for function signatures
- Write **docstrings** for all public functions/classes

```python
def create_driver(
    headless: bool = False,
    stealth_mode: bool = False,
) -> WebDriver:
    """
    Create a WebDriver instance with optional enhancements.
    
    Args:
        headless: Run browser in headless mode
        stealth_mode: Enable bot detection bypass
    
    Returns:
        Enhanced WebDriver instance
    
    Example:
        >>> driver = create_driver(stealth_mode=True)
        >>> driver.get("https://example.com")
    """
```

### Formatting

We use the following tools (run before committing):

```bash
# Format code
black sentinel/ tests/

# Sort imports
isort sentinel/ tests/

# Lint
flake8 sentinel/ tests/

# Type check
mypy sentinel/
```

---

## Testing

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=sentinel

# Run specific test file
pytest tests/unit/test_dom_mapper.py

# Run only fast tests
pytest -m "not slow"
```

### Writing Tests

```python
# tests/unit/test_decision_engine.py

import pytest
from sentinel.layers.intelligence import DecisionEngine, Decision

class TestDecisionEngine:
    """Tests for the DecisionEngine class."""
    
    @pytest.fixture
    def engine(self):
        """Create a decision engine in mock mode."""
        return DecisionEngine(mock_mode=True)
    
    def test_decide_click_action(self, engine):
        """Test that 'click' goals produce click decisions."""
        # Arrange
        elements = [MockElement(tag="BUTTON", text="Submit")]
        
        # Act
        decision = engine.decide("Click the submit button", elements, [])
        
        # Assert
        assert decision.action == "click"
        assert decision.confidence > 0.5
    
    def test_decide_type_action(self, engine):
        """Test that 'type' goals produce type decisions."""
        elements = [MockElement(tag="INPUT", text="")]
        
        decision = engine.decide("Type 'hello' in the input", elements, [])
        
        assert decision.action == "type"
        assert "hello" in decision.value
```

---

## Pull Request Process

### Before Submitting

1. **Create an issue** first for significant changes
2. **Fork the repository** and create a feature branch
3. **Write tests** for new functionality
4. **Update documentation** if needed
5. **Run the test suite** and ensure it passes

### Branch Naming

- `feature/description` - New features
- `fix/description` - Bug fixes
- `docs/description` - Documentation updates
- `refactor/description` - Code refactoring

### Commit Messages

Use conventional commits:

```
feat: add support for custom decision engines
fix: handle shadow DOM elements without text
docs: update installation instructions
test: add integration test for stealth mode
refactor: simplify ActionExecutor retry logic
```

### PR Template

```markdown
## Description
Brief description of changes

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Documentation update
- [ ] Refactoring

## Testing
- [ ] Unit tests added/updated
- [ ] Integration tests added/updated
- [ ] Manual testing performed

## Checklist
- [ ] Code follows project style guidelines
- [ ] Documentation updated
- [ ] Tests pass locally
```

---

## Architecture Guidelines

### Adding New Features

When adding new features, consider:

1. **Layer placement**: Where does it belong?
   - Sense layer: Understanding the page
   - Action layer: Executing commands
   - Intelligence layer: Making decisions
   - Validation layer: Testing reliability

2. **Graceful degradation**: What happens if a dependency is missing?
   ```python
   try:
       from optional_library import feature
       HAS_FEATURE = True
   except ImportError:
       HAS_FEATURE = False
   ```

3. **Observability**: Log important events
   ```python
   self._recorder.log_event("custom_event", {"data": value})
   ```

### Adding New Libraries

To integrate a new library:

1. Add to `pyproject.toml` as optional dependency
2. Create wrapper in appropriate layer
3. Update `doctor` command to check for it
4. Handle ImportError gracefully
5. Add tests and documentation

---

## Release Process

1. Update version in `pyproject.toml`
2. Update `CHANGELOG.md`
3. Create release PR
4. After merge, tag the release
5. GitHub Actions will publish to PyPI

---

## Community

- **Issues**: Use GitHub Issues for bugs and feature requests
- **Discussions**: Use GitHub Discussions for questions
- **Security**: Email security issues privately

---

## License

By contributing, you agree that your contributions will be licensed under the MIT License.

---

Thank you for contributing! 🙏
