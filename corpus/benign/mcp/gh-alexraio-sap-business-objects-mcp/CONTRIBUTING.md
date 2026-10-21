# Contributing to SAP BusinessObjects FastMCP Server

Thank you for your interest in contributing to the **SAP BusinessObjects FastMCP Server** project! We welcome contributions, bug reports, feature suggestions, and documentation improvements.

---

## Code of Conduct

This project is dedicated to providing a respectful, welcoming, and harassment-free environment for everyone. Please be considerate and respectful in all discussions, issues, and code reviews.

---

## Getting Started

### Prerequisites

- **Python**: `>= 3.13`
- **Package Manager**: [uv](https://github.com/astral-sh/uv) (recommended) or standard `pip` / `venv`
- **Git**

### Local Setup

1. **Fork and clone the repository**:
   ```bash
   git clone https://github.com/alexraio/sap-business-objects-mcp.git
   cd sap-business-objects-mcp
   ```

2. **Initialize the virtual environment & install dependencies**:
   ```bash
   uv sync --dev
   ```

3. **Activate the virtual environment**:
   - macOS / Linux:
     ```bash
     source .venv/bin/activate
     ```
   - Windows:
     ```powershell
     .venv\Scripts\Activate.ps1
     ```

4. **Verify your setup**:
   ```bash
   # Run the offline test suite (45 unit tests, ~0.5s execution)
   uv run pytest

   # Run code formatting and lint checks
   uv run ruff check .
   uv run ruff format --check .
   ```

---

## Branching Strategy

We follow a **Trunk-Based Development** model with short-lived feature branches:

1. Always branch off the latest `main`:
   ```bash
   git checkout main
   git pull origin main
   git checkout -b feat/your-feature-name
   ```
2. Use descriptive branch prefixes:
   - `feat/` for new features or MCP tools
   - `fix/` for bug fixes
   - `docs/` for documentation updates
   - `refactor/` for code restructuring without behavior changes
   - `test/` for new or updated tests
   - `ci/` for CI/CD workflow enhancements

---

## Development & Architecture Guidelines

### Modular Architecture
All tools and capabilities are organized into modular domain services located in `services/`:
- `core/`: HTTP client (`BOEClient`), authentication, exception handling, and logon token lifecycle.
- `services/`: Domain services (`WebiService`, `UniverseService`, `AdminService`, `ScheduleService`, `InfostoreService`).
- `server.py`: FastMCP entrypoint registering tools via clean service delegations.

When adding new SAP BusinessObjects features:
1. Implement the API logic in the appropriate service class in `services/`.
2. Keep `core/client.py` focused purely on transport, headers, tokens, and typed exception handling.
3. Expose the capability in `server.py` using `@mcp.tool()`.

### Tool Definitions for LLMs
All `@mcp.tool()` definitions in `server.py` **must**:
- Include comprehensive docstrings explaining the exact business purpose, input arguments, and expected output format.
- Have typed parameter annotations with sensible defaults where applicable.
- Return structured dictionaries, JSON strings, or descriptive markdown summaries designed for LLM consumption.

### Code Style & Formatting
- Code is formatted and linted using [Ruff](https://github.com/astral-sh/ruff) with target Python 3.13 and max line length 120.
- Check formatting and linting:
  ```bash
  uv run ruff check --fix .
  uv run ruff format .
  ```

---

## Testing Policy

**Offline-First & Zero Network Dependencies**:
- Because SAP BusinessObjects Enterprise requires an on-premise multi-tier installation and commercial licenses, **CI tests must run completely offline**.
- All unit tests must use mock fixtures (`MockBOEClient`, `pytest-mock`, `unittest.mock`) defined in `tests/conftest.py`.
- Never commit tests that make live HTTP requests or depend on external SAP servers.
- Ensure test coverage remains high when adding new features:
  ```bash
  uv run pytest --cov=core --cov=services --cov=server --cov-report=term-missing
  ```

---

## Commit Guidelines

We encourage [Conventional Commits](https://www.conventionalcommits.org/):
```text
feat(webi): add export document to PDF tool
fix(client): handle trailing slashes in custom base URLs
docs(readme): add contributing guide
test(universe): add unit test for UNV related reports
```

---

## Submitting a Pull Request

1. Push your branch to GitHub:
   ```bash
   git push origin feat/your-feature-name
   ```
2. Open a Pull Request targeting the `main` branch.
3. Ensure the PR description details:
   - What changes were made and why.
   - Any new MCP tools added.
   - Confirmation that all unit tests and lint checks pass.
4. The automated GitHub Actions CI workflow will validate:
   - Ruff linting and format checks.
   - The complete PyTest test suite on Python 3.13.
5. Once reviewed and approved, your PR will be squash-merged into `main`.

---

## Questions or Suggestions?

Open an issue on GitHub to discuss proposed architecture changes or new MCP tools before starting major implementations.
