# Installation Guide

## System Requirements

- **Operating System**: Linux (64-bit)
- **Python**: 3.10 or higher (required for MCP SDK)
- **Synopsys Verdi**: With NPI (Native Programming Interface) support
- **License**: Valid Synopsys Verdi license

## Step-by-Step Installation

### 1. Verify Verdi Installation

Check that Verdi is installed and VERDI_HOME is set:

```bash
echo $VERDI_HOME
# Should output something like: /opt/verdi or /tools/synopsys/verdi/...
```

If not set:

```bash
export VERDI_HOME=/path/to/your/verdi/installation
```

### 2. Set Up Library Paths

Add Verdi libraries to LD_LIBRARY_PATH:

```bash
export LD_LIBRARY_PATH=$VERDI_HOME/share/NPI/lib/linux64:$VERDI_HOME/platform/linux64/bin:$LD_LIBRARY_PATH
```

### 3. Verify Python Version

Check your Python version:

```bash
python3 --version
```

For best compatibility with MCP SDK, use Python 3.10+:

```bash
# If you need to use a different Python version
python3.10 --version  # or python3.11, python3.12, etc.
```

### 4. Create Virtual Environment

```bash
cd ~/work/fsdb-mcp
python3.10 -m venv venv
source venv/bin/activate
```

### 5. Install MCP SDK

```bash
pip install --upgrade pip
pip install mcp
```

### 6. Verify Installation

Test the FSDB reading functionality:

```bash
python test_fsdb.py
```

Expected output:
```
✓ Successfully imported pynpi and waveform
✓ VERDI_HOME: /opt/verdi
✓ NPI initialized successfully
```

### 7. Test with Sample FSDB File

If you have an FSDB file, test the complete workflow:

```bash
# Copy or link your FSDB file
cp /path/to/your/waveform.fsdb test.fsdb

# Run test
python test_fsdb.py
```

## Troubleshooting

### Issue: "ImportError: No module named 'pynpi'"

**Solution**:
1. Verify VERDI_HOME is set correctly
2. Check that `$VERDI_HOME/share/NPI/python` exists
3. Verify Python can access the path:
   ```bash
   python -c "import sys; sys.path.append('$VERDI_HOME/share/NPI/python'); from pynpi import npisys"
   ```

### Issue: "ImportError: libXXX.so: cannot open shared object file"

**Solution**:
1. Set LD_LIBRARY_PATH:
   ```bash
   export LD_LIBRARY_PATH=$VERDI_HOME/share/NPI/lib/linux64:$VERDI_HOME/platform/linux64/bin:$LD_LIBRARY_PATH
   ```
2. Verify the library exists:
   ```bash
   ls $VERDI_HOME/share/NPI/lib/linux64/
   ```

### Issue: "ERROR: Could not find a version that satisfies the requirement mcp"

**Solution**:
1. Upgrade Python to 3.10+:
   ```bash
   # Using pyenv
   pyenv install 3.10.13
   pyenv local 3.10.13
   
   # Or using system package manager
   sudo apt install python3.10  # Ubuntu/Debian
   sudo yum install python310    # RHEL/CentOS
   ```

2. Or install MCP from source:
   ```bash
   git clone https://github.com/modelcontextprotocol/python-sdk.git
   cd python-sdk
   pip install -e .
   ```

### Issue: License errors when running

**Solution**:
1. Verify Verdi license is available:
   ```bash
   $VERDI_HOME/bin/verdi -version
   ```
2. Check license server configuration
3. Set license environment variables if needed:
   ```bash
   export LM_LICENSE_FILE=port@server
   export SNPSLMD_LICENSE_FILE=port@server
   ```

### Issue: Python version compatibility

The MCP SDK requires Python 3.10 or higher. If you have an older Python version, upgrade using one of these methods:

```bash
# Using pyenv
pyenv install 3.10.13
pyenv local 3.10.13

# Or using system package manager
sudo apt install python3.10  # Ubuntu/Debian
sudo yum install python310    # RHEL/CentOS
```

## Environment Setup Script

Create a setup script for convenience:

```bash
cat > setup_env.sh << 'EOF'
#!/bin/bash
# FSDB MCP Server Environment Setup

# Set Verdi paths (modify as needed)
export VERDI_HOME=/opt/verdi

# Add NPI libraries
export LD_LIBRARY_PATH=$VERDI_HOME/share/NPI/lib/linux64:$VERDI_HOME/platform/linux64/bin:$LD_LIBRARY_PATH

# Activate virtual environment
source venv/bin/activate

echo "Environment configured for FSDB MCP Server"
echo "VERDI_HOME: $VERDI_HOME"
echo "Python: $(python --version)"
EOF

chmod +x setup_env.sh
```

Usage:
```bash
source setup_env.sh
```

## Verifying Complete Installation

Run this comprehensive check:

```bash
# 1. Check environment
echo "VERDI_HOME: $VERDI_HOME"
echo "Python: $(python --version)"

# 2. Test imports
python -c "from pynpi import npisys, waveform; print('✓ pynpi available')"
python -c "import mcp; print('✓ MCP SDK available')"

# 3. Run test script
python test_fsdb.py

# 4. Check server syntax
python -m py_compile server.py
echo "✓ Server syntax OK"
```

All checks should pass before running the MCP server.

## Next Steps

After successful installation:

1. **Configure MCP Client**: Update your MCP client configuration (see `mcp-config-example.json`)
2. **Test with Real Data**: Use actual FSDB files from your simulations
3. **Integrate with AI Assistant**: Connect the server to Claude Desktop or other MCP clients

## Additional Resources

- [MCP Documentation](https://modelcontextprotocol.io)
- [Synopsys Verdi Documentation](https://www.synopsys.com/verification/simulation/verdi.html)
- [Python Virtual Environments](https://docs.python.org/3/tutorial/venv.html)
