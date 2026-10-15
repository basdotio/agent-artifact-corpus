# PyPI Token Setup Guide

## 🔐 Setting Up PyPI Tokens

### Step 1: Create PyPI Accounts

1. **PyPI (Production)**: https://pypi.org/account/register/
2. **TestPyPI (Testing)**: https://test.pypi.org/account/register/

### Step 2: Generate API Tokens

#### For TestPyPI (Testing):
1. Go to https://test.pypi.org/account/login/
2. Log in to your account
3. Go to Account Settings → API tokens
4. Click "Add API token"
5. Give it a name like "itop-mcp-testing"
6. Set scope to "Entire account" (or specific project if it exists)
7. Copy the token (starts with `pypi-`)

#### For PyPI (Production):
1. Go to https://pypi.org/account/login/
2. Log in to your account
3. Go to Account Settings → API tokens
4. Click "Add API token"
5. Give it a name like "itop-mcp-production"
6. Set scope to "Entire account" (or specific project after first upload)
7. Copy the token (starts with `pypi-`)

### Step 3: Configure Tokens

#### Option 1: Environment Variables (Recommended for CI/CD)
```bash
# For TestPyPI
export UV_PUBLISH_TOKEN="pypi-your-testpypi-token-here"
export UV_PUBLISH_URL="https://test.pypi.org/legacy/"

# For PyPI (production)
export UV_PUBLISH_TOKEN="pypi-your-pypi-token-here"
# No URL needed for PyPI (it's the default)
```

#### Option 2: Add to your shell profile (persistent)
```bash
# Add to ~/.bashrc or ~/.zshrc
echo 'export UV_PUBLISH_TOKEN_TESTPYPI="pypi-your-testpypi-token-here"' >> ~/.bashrc
echo 'export UV_PUBLISH_TOKEN_PYPI="pypi-your-pypi-token-here"' >> ~/.bashrc
source ~/.bashrc
```

#### Option 3: uv configuration file
Create `~/.config/uv/uv.toml`:
```toml
[publish]
username = "__token__"

[publish.testpypi]
url = "https://test.pypi.org/legacy/"
password = "pypi-your-testpypi-token-here"

[publish.pypi]
password = "pypi-your-pypi-token-here"
```

### Step 4: Publishing Commands

#### Test Publishing (TestPyPI):
```bash
# Set token for this session
export UV_PUBLISH_TOKEN="pypi-your-testpypi-token-here"

# Publish to TestPyPI
make publish-test

# Or manually:
UV_PUBLISH_URL=https://test.pypi.org/legacy/ UV_PUBLISH_TOKEN="pypi-your-token" uv publish dist/*
```

#### Production Publishing (PyPI):
```bash
# Set token for this session
export UV_PUBLISH_TOKEN="pypi-your-pypi-token-here"

# Publish to PyPI
make publish

# Or manually:
UV_PUBLISH_TOKEN="pypi-your-token" uv publish dist/*
```

### Step 5: Test Installation

#### From TestPyPI:
```bash
pip install --index-url https://test.pypi.org/simple/ itop-mcp
```

#### From PyPI:
```bash
pip install itop-mcp
```

## 🔒 Security Best Practices

1. **Never commit tokens to git**
2. **Use environment variables or secure config files**
3. **Regenerate tokens if compromised**
4. **Use project-scoped tokens when possible**
5. **Different tokens for testing vs production**

## 🐛 Troubleshooting

### Common Errors:

1. **403 Forbidden**: Wrong token or insufficient permissions
2. **Package already exists**: Version already published (increment version)
3. **Invalid credentials**: Check token format (should start with `pypi-`)

### Debug Commands:
```bash
# Test with verbose output
UV_PUBLISH_TOKEN="your-token" uv publish --verbose dist/*

# Check what files will be uploaded
ls -la dist/
```

## 🎯 Quick Start

1. Register accounts on PyPI and TestPyPI
2. Generate API tokens
3. Set environment variable:
   ```bash
   export UV_PUBLISH_TOKEN="pypi-your-testpypi-token-here"
   ```
4. Test publish:
   ```bash
   make publish-test
   ```
5. If successful, use production token and:
   ```bash
   make publish
   ```
