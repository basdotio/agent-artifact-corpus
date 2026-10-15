# Contributing to Fabric MCP Server

Thank you for your interest in contributing to the Fabric MCP Server! This document provides guidelines for contributing to this project.

## How to Contribute

### Reporting Issues

If you find a bug or have a suggestion for improvement:

1. **Check existing issues** to avoid duplicates
2. **Create a new issue** with a clear title and description
3. **Include details** such as:
   - Steps to reproduce the issue
   - Expected vs actual behavior
   - Your environment (Python version, OS, etc.)
   - Relevant error messages or logs

### Submitting Changes

1. **Fork the repository** and create a new branch from `main`
2. **Make your changes** following the code style guidelines below
3. **Test your changes** thoroughly
4. **Commit your changes** with clear, descriptive commit messages
5. **Push to your fork** and submit a pull request

### Pull Request Guidelines

- Keep pull requests focused on a single feature or fix
- Update documentation if you're adding or changing functionality
- Add or update tests as needed
- Follow the existing code style and conventions
- Reference any related issues in your PR description

## Code Style Guidelines

### Python Code

- Follow [PEP 8](https://peps.python.org/pep-0008/) style guidelines
- Use meaningful variable and function names
- Add docstrings to functions and classes
- Keep functions focused and modular
- Use type hints where appropriate

### Example:
```python
async def list_workspaces() -> dict:
    """
    List all Microsoft Fabric workspaces accessible to the authenticated user.
    
    Returns:
        dict: A dictionary containing a list of workspace objects with id and name.
    """
    # Implementation here
```

### Documentation

- Update the README.md if adding new features or tools
- Keep documentation clear, concise, and beginner-friendly
- Include code examples where helpful
- Document any new environment variables or configuration options

## Development Setup

1. Clone your fork:
   ```bash
   git clone https://github.com/YOUR_USERNAME/fabric-mcp.git
   cd fabric-mcp
   ```

2. Create a conda environment:
   ```bash
   conda create -p ./env python=3.12 -y
   conda activate ./env
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Set up your `.env` file with your credentials

5. Test your changes:
   ```bash
   python main.py
   ```

## Adding New Tools

When adding new MCP tools for Microsoft Fabric:

1. **Define the tool** in `main.py` using the `@mcp.tool()` decorator
2. **Add proper error handling** and logging
3. **Document the tool** with clear docstrings
4. **Update README.md** with tool description and usage examples
5. **Test the tool** with real Fabric API calls

### Example Tool Structure:
```python
@mcp.tool()
async def your_new_tool(parameter: str) -> dict:
    """
    Brief description of what the tool does.
    
    Args:
        parameter: Description of the parameter
        
    Returns:
        dict: Description of what is returned
    """
    try:
        # Get access token
        token = await get_fabric_token()
        
        # Make API call
        # Process response
        
        return {"result": "data"}
    except Exception as e:
        return {"error": str(e)}
```

## Testing

- Test your changes locally before submitting
- Verify integration with GitHub Copilot in VS Code
- Test error handling and edge cases
- Ensure authentication still works correctly

## Code of Conduct

- Be respectful and inclusive
- Welcome newcomers and help them get started
- Focus on constructive feedback
- Assume good intentions

## Questions?

If you have questions about contributing, feel free to:
- Open an issue for discussion
- Reach out to the maintainers

## License

By contributing to this project, you agree that your contributions will be licensed under the MIT License.

---

Thank you for contributing to making this project better! 🎉
