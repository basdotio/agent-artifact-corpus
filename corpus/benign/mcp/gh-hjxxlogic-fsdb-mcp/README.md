# FSDB MCP Server

A Model Context Protocol (MCP) server for reading and querying FSDB (Fast Signal Database) waveform files. This server provides programmatic access to FSDB files through the MCP protocol, enabling AI assistants and other clients to query waveform data, signals, scopes, and value changes.

## Features

- **Open and manage FSDB files** - Open, close, and get information about FSDB waveform files
- **Browse hierarchy** - Navigate through scope hierarchies and list signals
- **Search functionality** - Search for signals and scopes by name pattern across the hierarchy
- **Query signals** - Get detailed signal information including ranges, types, and properties
- **Read waveform data** - Extract signal values at specific times or get value changes over time ranges
- **Multiple format support** - View values in binary, decimal, hexadecimal, or real formats
- **Smart limits** - Automatic truncation of large results to prevent memory issues (configurable)

## Prerequisites

- **Python 3.10 or higher** (required for MCP SDK compatibility)
- **Synopsys Verdi** with NPI (Native Programming Interface) support
- **VERDI_HOME** environment variable set to your Verdi installation directory
- **pynpi** library (included with Verdi)
- **Valid Verdi license**

> **Note**: The MCP SDK requires Python 3.10 or higher.

## Installation

For detailed installation instructions, see [INSTALL.md](docs/INSTALL.md).

### Quick Start

1. **Set up the environment:**

```bash
export VERDI_HOME=/path/to/verdi
export LD_LIBRARY_PATH=$VERDI_HOME/share/NPI/lib/linux64:$VERDI_HOME/platform/linux64/bin:$LD_LIBRARY_PATH
```

2. **Create and activate virtual environment (Python 3.10+):**

```bash
python3.10 -m venv venv
source venv/bin/activate
```

3. **Install dependencies:**

```bash
pip install --upgrade pip
pip install mcp
```

4. **Test the installation:**

```bash
python test_fsdb.py
```

## Usage

### Running the Server

Start the MCP server:

```bash
python server.py
```

The server communicates via stdin/stdout using the MCP protocol.

### Available Tools

The server provides the following tools:

#### 1. `fsdb_is_fsdb`
Check if a file is a valid FSDB file.

**Parameters:**
- `path` (string): Path to the file to check

**Example:**
```json
{
  "path": "/path/to/waveform.fsdb"
}
```

#### 2. `fsdb_open`
Open an FSDB waveform file.

**Parameters:**
- `path` (string): Path to the FSDB file

**Returns:** File information including time range, version, and properties

#### 3. `fsdb_close`
Close an opened FSDB file.

**Parameters:**
- `path` (string): Path to the FSDB file to close

#### 4. `fsdb_get_info`
Get detailed information about an opened FSDB file.

**Parameters:**
- `path` (string): Path to the FSDB file

**Returns:** File metadata including:
- Time range (min_time, max_time)
- Scale unit
- Version and simulation date
- Flags (has_glitch, has_assertion, etc.)

#### 5. `fsdb_list_scopes`
List scopes in the FSDB file hierarchy.

**Parameters:**
- `path` (string): Path to the FSDB file
- `scope_path` (string, optional): Parent scope path to list children of

**Returns:** List of scopes with name, full_name, def_name, and type

**Example:**
```json
{
  "path": "/path/to/waveform.fsdb",
  "scope_path": "tb_top.cpu"
}
```

#### 6. `fsdb_list_signals`
List signals in a scope.

**Parameters:**
- `path` (string): Path to the FSDB file
- `scope_path` (string, optional): Scope path to list signals from

**Returns:** List of signals with properties

#### 7. `fsdb_get_signal_info`
Get detailed information about a signal.

**Parameters:**
- `path` (string): Path to the FSDB file
- `signal_path` (string): Full signal path (e.g., "top.module1.signal_name")

**Returns:** Signal properties including:
- Name and full name
- Type information (is_real, is_string, etc.)
- Range information (left_range, right_range, range_size)
- Direction and other attributes

#### 8. `fsdb_get_signal_value`
Get signal value at a specific time.

**Parameters:**
- `path` (string): Path to the FSDB file
- `signal_path` (string): Full signal path
- `time` (integer): Time point to query
- `format` (string, optional): Value format - "bin", "dec", "hex", or "real" (default: "hex")

**Returns:** Signal value at the specified time

**Example:**
```json
{
  "path": "/path/to/waveform.fsdb",
  "signal_path": "tb_top.cpu.clk",
  "time": 1000,
  "format": "hex"
}
```

#### 9. `fsdb_get_signal_changes`
Get signal value changes in a time range.

**Parameters:**
- `path` (string): Path to the FSDB file
- `signal_path` (string): Full signal path
- `start_time` (integer): Start time
- `end_time` (integer): End time
- `format` (string, optional): Value format - "bin", "dec", "hex", or "real" (default: "hex")

**Returns:** List of value changes with time and value

**Example:**
```json
{
  "path": "/path/to/waveform.fsdb",
  "signal_path": "tb_top.cpu.data",
  "start_time": 0,
  "end_time": 10000,
  "format": "hex"
}
```

#### 10. `fsdb_search`
Search for signals and scopes by name pattern in the FSDB file.

**Parameters:**
- `path` (string): Path to the FSDB file
- `pattern` (string): Search pattern (case-insensitive substring match)
- `search_type` (string, optional): Type of items to search - "signals", "scopes", or "all" (default: "all")
- `scope_path` (string, optional): Scope path to limit search (e.g., "top.module1"). If not provided, searches entire hierarchy.

**Returns:** Search results with matching signals and/or scopes

**Example:**
```json
{
  "path": "/path/to/waveform.fsdb",
  "pattern": "clk",
  "search_type": "signals",
  "scope_path": "tb_top"
}
```

### Resources

The server exposes opened FSDB files as resources with the URI scheme `fsdb://`. Each opened file can be read as a resource to get its information and top-level scopes.

## Example Workflow

1. **Check if file is FSDB:**
```json
{
  "tool": "fsdb_is_fsdb",
  "arguments": {
    "path": "waveform.fsdb"
  }
}
```

2. **Open the file:**
```json
{
  "tool": "fsdb_open",
  "arguments": {
    "path": "waveform.fsdb"
  }
}
```

3. **List top-level scopes:**
```json
{
  "tool": "fsdb_list_scopes",
  "arguments": {
    "path": "waveform.fsdb"
  }
}
```

4. **List signals in a scope:**
```json
{
  "tool": "fsdb_list_signals",
  "arguments": {
    "path": "waveform.fsdb",
    "scope_path": "tb_top"
  }
}
```

5. **Get signal value changes:**
```json
{
  "tool": "fsdb_get_signal_changes",
  "arguments": {
    "path": "waveform.fsdb",
    "signal_path": "tb_top.clk",
    "start_time": 0,
    "end_time": 1000,
    "format": "bin"
  }
}
```

6. **Close the file:**
```json
{
  "tool": "fsdb_close",
  "arguments": {
    "path": "waveform.fsdb"
  }
}
```

## Architecture

The server is built on:
- **MCP (Model Context Protocol)**: For standardized communication with AI assistants
- **pynpi**: Synopsys NPI Python bindings for FSDB access
- **waveform.py**: High-level Python API for waveform manipulation

## Error Handling

The server provides detailed error messages for common issues:
- File not found
- Invalid FSDB file
- File not opened (must open before querying)
- Signal or scope not found
- Invalid time ranges

## Limitations

- Requires Synopsys Verdi installation with NPI support
- Only supports FSDB format (not VCD, EVCD, etc.)
- Performance depends on FSDB file size and query complexity
- Must have proper VERDI_HOME and LD_LIBRARY_PATH configuration

## Development

### Project Structure

```
fsdb-mcp/
├── server.py                    # Main MCP server implementation
├── requirements.txt             # Python dependencies
├── mcp-config-example.json      # Example MCP configuration
├── update_mcp_config.sh         # Script to update MCP config
├── test.fsdb                    # Example FSDB file for testing
├── waveform.py                  # Symlink to Verdi's waveform module
├── docs/                        # Documentation
│   ├── README.md                # Documentation index
│   ├── INSTALL.md               # Installation guide
│   ├── LIMITS_CONFIG.md         # Return limits configuration
│   ├── TEST_FINAL_REPORT.md     # Complete test report
│   ├── MCP_TEST_SUMMARY.md      # MCP protocol test summary
│   └── README_CN.md             # Chinese README
├── tests/                       # Test scripts
│   ├── README.md                # Test documentation
│   ├── test_server_tools.py     # Direct API tests
│   ├── test_mcp_client.py       # MCP protocol tests
│   └── test_fsdb.py             # Basic FSDB tests
└── venv/                        # Virtual environment
```

### Adding New Features

To add new tools:
{{ ... }}
2. Implement tool logic in `handle_call_tool()`
3. Update documentation

## Configuration

### Return Limits

The server automatically limits the amount of data returned to prevent memory issues:

- **Signals**: Max 1000 per query
- **Scopes**: Max 1000 per query  
- **Value changes**: Max 10000 per query

When results are truncated, the response includes:
```json
{
  "data": [...],
  "total": 5000,
  "returned": 1000,
  "truncated": true
}
```

To adjust limits, edit `server.py`:
```python
MAX_SIGNALS_RETURN = 1000
MAX_SCOPES_RETURN = 1000
MAX_CHANGES_RETURN = 10000
```

See [LIMITS_CONFIG.md](LIMITS_CONFIG.md) for detailed information.

## Troubleshooting

**Issue: "pynpi not available"**
- Ensure VERDI_HOME is set correctly
- Check that pynpi library path is accessible
- Verify LD_LIBRARY_PATH includes Verdi libraries

**Issue: "Failed to open FSDB file"**
- Verify file exists and is readable
- Check file is valid FSDB format using `fsdb_is_fsdb`
- Ensure Verdi license is available

**Issue: "Signal not found"**
- Use `fsdb_list_signals` to see available signals
- Check signal path syntax (use dot notation: "scope.signal")
- Verify scope hierarchy with `fsdb_list_scopes`

## License

This project uses Synopsys Verdi NPI libraries which are subject to Synopsys licensing terms.

## Contributing

Contributions are welcome! Please ensure:
- Code follows existing style
- New tools are documented
- Error handling is comprehensive
- Changes are tested with real FSDB files

## Support

For issues related to:
- **MCP protocol**: See [MCP documentation](https://modelcontextprotocol.io)
- **FSDB/Verdi**: Contact Synopsys support
- **This server**: Open an issue in the repository
