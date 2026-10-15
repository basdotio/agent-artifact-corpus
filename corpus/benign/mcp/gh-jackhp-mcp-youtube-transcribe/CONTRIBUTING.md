# Contributing to YouTubeTranscriber

G'day, thank you for considering contributing to this project! Every contribution, no matter how small, is valuable.
This document provides guidelines to help you through the contribution process.

## Code of Conduct

This project and everyone participating in it is governed by our [Code of Conduct](CODE_OF_CONDUCT.md). By
participating, you are expected to uphold this code. Please report unacceptable behavior.

## How Can I Contribute?

There are many ways to contribute, from writing code and documentation to reporting bugs and suggesting new features.

### Reporting Bugs

If you find a bug, please ensure it hasn't already been reported by searching
the [Issues](https://github.com/your-username/your-repository/issues) on GitHub.
If you can't find an existing issue, please create a new one. Be sure to include:

- A **clear and descriptive title**.
- A **detailed description** of the problem.
- **Steps to reproduce** the bug.
- The **expected behavior** and what **actually happened**.
- Your **environment details** (e.g., operating system, Python version).

### Suggesting Enhancements

If you have an idea for a new feature or an improvement to an existing one:

1. Check the [Issues](https://github.com/your-username/your-repository/issues) to see if the enhancement has already
   been suggested.
2. If not, create a new issue. Provide a clear title and a detailed explanation of the proposed feature and why it would
   be beneficial.

### Your First Code Contribution

Ready to contribute code? Here’s how to set up your environment and submit your changes.

#### 1. Prerequisites

Before you begin, ensure you have the following installed on your system:

- Python 3.12+
- **[uv](https://github.com/astral-sh/uv)**: The project's package installer.
- **[FFmpeg](https://ffmpeg.org/download.html)**: Required for audio processing by Whisper.

#### 2. Set Up Your Local Environment

1. **Fork the repository** on GitHub.
2. **Clone your fork** locally:

``` bash
    git clone https://github.com/your-username/YouTubeTranscriber.git
    cd YouTubeTranscriber
```

1. **Create and activate a virtual environment** using `uv`. This command creates a directory and activates it. `.venv`

``` bash
    uv venv
```

1. **Install the project and its dependencies** from the file. `pyproject.toml`

``` bash
    uv sync
```

#### 3. Make Your Changes

1. **Create a new branch** for your changes. Use a descriptive name.

``` bash
    git checkout -b feature/my-awesome-feature
    # or for a bug fix:
    git checkout -b fix/resolve-that-bug
```

1. **Write your code**. Make sure to adhere to the project's coding standards.
2. **Commit your changes** with a clear and concise commit message.

``` bash
    git add .
    git commit -m "feat: Add my awesome feature"
    # Use prefixes like 'feat:', 'fix:', 'docs:', 'style:', 'refactor:'
```

#### 4. Submit Your Contribution

1. **Push your branch** to your fork on GitHub:

``` bash
    git push origin feature/my-awesome-feature
```

1. Go to your repository on GitHub and **open a Pull Request** (PR).
2. Fill out the PR template, providing a clear description of your changes and linking to any relevant issues (e.g.,
   `Closes #123`).
3. We will review your PR as soon as possible. Thank you for your patience!

## Coding Standards

- **Style:** Please follow the [PEP 8 Style Guide for Python Code](https://www.python.org/dev/peps/pep-0008/).
- **Documentation:** If you add a new function or class, please include a docstring explaining what it does.
- **Tests:** If you add a new feature, please add tests to verify it works as expected. The project has existing tests
  in and that you can use as a reference. `simple.py``test_mcp.py`

