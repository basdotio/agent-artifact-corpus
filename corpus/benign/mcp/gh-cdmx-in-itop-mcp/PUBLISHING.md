# Publishing Guide for iTop MCP Server

This guide explains how to publish the iTop MCP Server to PyPI.

## Prerequisites

1. **PyPI Account**: Create accounts on both [PyPI](https://pypi.org) and [TestPyPI](https://test.pypi.org)
2. **API Tokens**: Generate API tokens for both services
3. **uv configured**: Configure uv with your credentials

## Configure uv for Publishing

### 1. Configure PyPI Credentials

Create or update your `~/.pypirc` file:

```ini
[distutils]
index-servers = 
    pypi
    testpypi

[pypi]
repository = https://upload.pypi.org/legacy/
username = __token__
password = <your-pypi-api-token>

[testpypi]
repository = https://test.pypi.org/legacy/
username = __token__
password = <your-testpypi-api-token>
```

### 2. Configure API Tokens

#### Environment Variables (Recommended):
```bash
# For TestPyPI
export UV_PUBLISH_TOKEN="pypi-your-testpypi-token-here"

# For PyPI (production)  
export UV_PUBLISH_TOKEN="pypi-your-pypi-token-here"
```

#### Or use uv configuration file (`~/.config/uv/uv.toml`):
```toml
[publish.testpypi]
url = "https://test.pypi.org/legacy/"
password = "pypi-your-testpypi-token-here"

[publish.pypi]
password = "pypi-your-pypi-token-here"
```

📋 **See PYPI_TOKEN_SETUP.md for detailed token setup instructions**

## Publishing Process

### Step 1: Test Build

```bash
make build
```

This will:
- Clean previous builds
- Build both wheel and source distribution
- Show the created files

### Step 2: Publish to TestPyPI (Recommended First)

```bash
make publish-test
```

This will:
- Build the package
- Upload to TestPyPI for testing
- Provide a link to check the uploaded package

### Step 3: Test Installation from TestPyPI

```bash
# Install from TestPyPI to test
pip install --index-url https://test.pypi.org/simple/ itop-mcp

# Test the installation
itop-mcp --help
```

### Step 4: Publish to Production PyPI

```bash
make publish
```

This will:
- Build the package
- Ask for confirmation (since it's production)
- Upload to PyPI
- Provide a link to the live package

## Version Management

### Updating Version

1. Update version in `pyproject.toml`:
   ```toml
   version = "1.0.1"
   ```

2. Update version in `__init__.py`:
   ```python
   __version__ = "1.0.1"
   ```

3. Commit the changes:
   ```bash
   git add pyproject.toml __init__.py
   git commit -m "bump: version 1.0.1"
   git tag v1.0.1
   ```

4. Build and publish:
   ```bash
   make publish
   ```

## Package Information

- **Package Name**: `itop-mcp`
- **Import Name**: Import the main module directly
- **Entry Point**: `itop-mcp` command (from main:main)
- **Python Support**: 3.10+
- **License**: MIT

## Post-Publication

### 1. Update Documentation

- Add PyPI installation instructions to README
- Update version badges if using any
- Document new features in CHANGELOG

### 2. GitHub Release

```bash
# Create and push tag
git tag v1.0.0
git push origin v1.0.0

# Create GitHub release with changelog
```

### 3. Announce

- Update project documentation
- Announce in relevant communities
- Add to awesome lists if applicable

## Troubleshooting

### Common Issues

1. **Authentication Errors**:
   - Check API token is correct
   - Ensure token has correct permissions
   - Verify ~/.pypirc format

2. **Package Name Conflicts**:
   - Package name must be unique on PyPI
   - Check availability: https://pypi.org/project/itop-mcp/

3. **Build Errors**:
   - Check pyproject.toml syntax
   - Ensure all required files are included
   - Verify dependencies are available

4. **Upload Errors**:
   - Cannot upload same version twice
   - Increment version number for new uploads
   - Check file size limits

### Getting Help

- [PyPI Help](https://pypi.org/help/)
- [uv Documentation](https://docs.astral.sh/uv/)
- [Python Packaging Guide](https://packaging.python.org/)

## Security Notes

- Never commit API tokens to version control
- Use environment variables or secure credential storage
- Regularly rotate API tokens
- Use TestPyPI for testing uploads
