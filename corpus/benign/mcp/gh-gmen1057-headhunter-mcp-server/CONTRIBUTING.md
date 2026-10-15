# Contributing to HeadHunter MCP Server

Thank you for your interest in contributing! 🎉

## How to Contribute

### Reporting Issues

- Check existing issues first to avoid duplicates
- Use a clear and descriptive title
- Include steps to reproduce (if applicable)
- Mention your environment (OS, Python version, etc.)

### Submitting Pull Requests

1. **Fork the repository**

2. **Create a feature branch**
   ```bash
   git checkout -b feature/your-feature-name
   ```

3. **Make your changes**
   - Follow existing code style
   - Add tests if applicable
   - Update documentation

4. **Test your changes**
   ```bash
   python -m pytest  # if tests exist
   ```

5. **Commit your changes**
   ```bash
   git commit -m "Add: brief description of changes"
   ```

6. **Push to your fork**
   ```bash
   git push origin feature/your-feature-name
   ```

7. **Open a Pull Request**
   - Describe what changed and why
   - Reference any related issues

## Code Style

- Follow PEP 8 for Python code
- Use type hints where possible
- Add docstrings for public functions
- Keep functions focused and small

## Development Setup

```bash
# Clone your fork
git clone https://github.com/your-username/headhunter-mcp-server.git
cd headhunter-mcp-server

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Install development dependencies (if any)
pip install -r requirements-dev.txt  # if exists
```

## Testing

Before submitting, ensure:
- [ ] Code runs without errors
- [ ] All existing functionality still works
- [ ] New features are documented
- [ ] No credentials are committed

## Questions?

Feel free to open an issue for discussion before starting work on major changes.

---

Thank you for contributing! 🚀
