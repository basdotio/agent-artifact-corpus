# Development Guide

## Setting Up Development Environment

### Prerequisites
- Python 3.8+
- Git
- Make (optional, for using Makefile)

### Setup Steps

```bash
# Clone repository
git clone https://github.com/youcanautomate-yca/ai-driven-mobile-automation.git
cd ai-driven-mobile-automation

# Create and activate virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install development dependencies
pip install -e ".[dev]"

# Install additional dev tools
pip install build twine pre-commit
```

## Project Structure

```
appium-mcp/
├── server.py                      # Main MCP server
├── command.py                     # Core Appium commands
├── orchestrator.py                # High-level orchestration
├── session_store.py               # Session management
├── config.py                      # Configuration
├── logger.py                      # Logging utilities
├── bedrock_client.py              # AWS Bedrock integration
├── mcp_client.py                  # MCP client utilities
│
├── tools_*.py                     # Tool implementations
│   ├── tools_session.py           # Session tools
│   ├── tools_interactions.py      # Interaction tools
│   ├── tools_navigations.py       # Navigation tools
│   ├── tools_app_management.py    # App management
│   ├── tools_context.py           # Context switching
│   ├── tools_ios.py               # iOS-specific tools
│   ├── tools_documentation.py     # Documentation tools
│   └── tools_test_generation.py   # Test generation
│
├── chatbot.py                     # Interactive chatbot
├── page_objects/                  # Page Object Model classes
├── prompts/                       # AI prompts and templates
├── templates/                     # Code templates
├── generated_tests/               # Auto-generated tests
│
├── pyproject.toml                 # Package configuration
├── setup.py                       # Setup configuration
├── MANIFEST.in                    # Package manifest
├── README.md                      # Main documentation
├── INSTALLATION.md                # Installation guide
├── CHANGELOG.md                   # Version history
└── requirements.txt               # Dependencies
```

## Code Style and Standards

### Code Formatting
```bash
# Format code with black
black .

# Check code style
flake8 .

# Type checking
mypy .
```

### Pre-commit Hooks
```bash
# Install pre-commit
pip install pre-commit

# Install hooks
pre-commit install

# Run manually
pre-commit run --all-files
```

## Testing

### Running Tests
```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=appium_mcp

# Run specific test file
pytest tests/test_session.py

# Run with verbose output
pytest -v -s
```

### Writing Tests
```python
# tests/test_example.py
import pytest
from appium_mcp import YourClass

def test_feature():
    """Test description."""
    result = YourClass().method()
    assert result == expected_value
```

## Building and Publishing

### Local Build
```bash
# Build wheel and sdist
python -m build

# Check built files
ls -la dist/
```

### Test PyPI (Recommended Before Release)
```bash
# Install twine if not already installed
pip install twine

# Upload to TestPyPI
python -m twine upload --repository testpypi dist/*

# Test installation from TestPyPI
pip install --index-url https://test.pypi.org/simple/ appium-mcp

# Verify installation
python -c "import appium_mcp; print('✓ Success')"
```

### PyPI Release
```bash
# Configure PyPI credentials in ~/.pypirc (see INSTALLATION.md)

# Upload to PyPI
python -m twine upload dist/*

# Verify on PyPI
# Visit: https://pypi.org/project/appium-mcp/
```

## Version Management

Version is defined in `pyproject.toml` under `[project] version`.

Semantic Versioning: `MAJOR.MINOR.PATCH`
- MAJOR: Breaking changes
- MINOR: New features (backwards compatible)
- PATCH: Bug fixes

### Release Process
1. Update version in `pyproject.toml`
2. Update `CHANGELOG.md` with changes
3. Commit: `git commit -m "Release v1.0.0"`
4. Tag: `git tag -a v1.0.0 -m "Version 1.0.0"`
5. Push: `git push origin main --tags`
6. Build and publish: `python -m build && twine upload dist/*`

## Useful Commands

```bash
# Check for issues before committing
pre-commit run --all-files

# Format code
black .

# Type checking
mypy . --ignore-missing-imports

# Run security checks
bandit -r . -ll

# Clean build artifacts
rm -rf build/ dist/ *.egg-info .pytest_cache .mypy_cache

# Virtual env management
deactivate              # Exit venv
rm -rf venv             # Remove venv
```

## Documentation

- Use docstrings in Google format
- Add type hints to all functions
- Update README.md for user-facing changes
- Add CHANGELOG.md entries for releases

## Contributing

1. Fork the repository
2. Create feature branch: `git checkout -b feature/my-feature`
3. Commit changes: `git commit -am 'Add feature'`
4. Push to branch: `git push origin feature/my-feature`
5. Create Pull Request

## Debugging

### Enable Debug Logging
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Debug with VS Code
Add to `.vscode/launch.json`:
```json
{
    "version": "0.2.0",
    "configurations": [
        {
            "name": "Python: Module",
            "type": "python",
            "request": "launch",
            "module": "appium_mcp.server",
            "console": "integratedTerminal"
        }
    ]
}
```

## Support and Questions

- GitHub Issues: https://github.com/youcanautomate-yca/ai-driven-mobile-automation/issues
- Discussions: https://github.com/youcanautomate-yca/ai-driven-mobile-automation/discussions
- Email: youcanautomate@gmail.com
