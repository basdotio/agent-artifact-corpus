# Contributing to mcp-152fz-anonymizer

First off, thanks for taking the time to contribute! 🎉

The following is a set of guidelines for contributing to this project. These are mostly guidelines, not rules. Use your best judgment, and feel free to propose changes to this document in a pull request.

## Code of Conduct

This project and everyone participating in it is governed by a Code of Conduct. By participating, you are expected to uphold this code. Please report unacceptable behavior to [den.yankees@gmail.com].

## How Can I Contribute?

### Reporting Bugs

This section guides you through submitting a bug report.

- **Use a clear and descriptive title** for the issue to identify the problem.
- **Describe the exact steps to reproduce the problem** in as many details as possible.
- **Provide specific examples** to demonstrate the steps.

### Suggesting Enhancements

This section guides you through submitting an enhancement suggestion, including completely new features and minor improvements to existing functionality.

- **Use a clear and descriptive title** for the issue to identify the suggestion.
- **Provide a step-by-step description of the suggested enhancement** in as many details as possible.
- **Explain why this enhancement would be useful** to most users.

### Pull Requests

1.  Fork the repo and create your branch from `master`.
2.  If you've added code that should be tested, add tests.
3.  If you've changed APIs, update the documentation.
4.  Ensure the test suite passes.
5.  Make sure your code lints.

## Development Setup

1.  Clone the repository:

    ```bash
    git clone https://github.com/Pioneer113-new/mcp-152fz-anonymizer.git
    cd mcp-152fz-anonymizer
    ```

2.  Create virtual environment:

    ```bash
    ./install.sh
    ```

3.  Activate environment:

    ```bash
    source venv/bin/activate
    ```

4.  Run tests:
    ```bash
    python test_anonymizer.py
    ```

## Styleguides

### Git Commit Messages

- Use the present tense ("Add feature" not "Added feature")
- Use the imperative mood ("Move cursor to..." not "Moves cursor to...")
- Limit the first line to 72 characters or less
- Reference issues and pull requests liberally after the first line

### Python Style

- This project follows [PEP 8](https://www.python.org/dev/peps/pep-0008/).
- Use descriptive variable names.
- Add docstrings to public functions and classes.
