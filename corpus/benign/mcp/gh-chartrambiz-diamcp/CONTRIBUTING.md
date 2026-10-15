# Contributing to diaMCP

Thank you for your interest in contributing!

## How to Contribute

### Reporting Bugs

1. Check existing issues first
2. Create a detailed issue with:
   - Expected behavior
   - Actual behavior
   - Steps to reproduce
   - Environment details (OS, Docker version, etc.)

### Suggesting Features

1. Check existing issues/discussions
2. Open a discussion with your feature proposal
3. Include use cases and examples

### Pull Requests

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/my-feature`
3. Make your changes
4. Test thoroughly
5. Commit with clear messages: `git commit -m "Add feature: description"`
6. Push: `git push origin feature/my-feature`
7. Open a Pull Request

### Code Style

- Follow PEP 8
- Use meaningful variable/function names
- Add docstrings for functions
- Keep functions focused and small

### Documentation

- Update README.md for user-facing changes
- Add code comments for complex logic
- Update docstrings when changing function behavior

## Development Setup

```bash
# Clone your fork
git clone https://github.com/YOUR_USERNAME/diamcp.git
cd diamcp

# Build and run
docker compose up --build

# Run tests (when available)
docker compose exec diamcp pytest
```

## Questions?

Open a GitHub Discussion for questions about contributing.
