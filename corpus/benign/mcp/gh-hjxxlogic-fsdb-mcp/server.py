#!/usr/bin/env python3
"""
FSDB MCP Server - Model Context Protocol server for reading FSDB waveform files.

This server provides access to FSDB (Fast Signal Database) files through the MCP protocol,
allowing clients to query waveform data, signals, scopes, and value changes.
"""

import os
import sys
import json
import logging
import contextlib
import tempfile
import uuid
from typing import Any, Optional, Dict, List
from pathlib import Path

# Global NPI variables
NPI_AVAILABLE = False
npisys = None
waveform = None

# Setup VERDI environment if needed
if "VERDI_HOME" in os.environ:
    rel_lib_path = os.environ["VERDI_HOME"] + "/share/NPI/python"
    sys.path.append(os.path.abspath(rel_lib_path))
    
    # Add LD_LIBRARY_PATH if needed
    if "LD_LIBRARY_PATH" in os.environ:
        os.environ['LD_LIBRARY_PATH'] = (
            os.environ['VERDI_HOME'] + '/share/NPI/lib/linux64:' +
            os.environ['VERDI_HOME'] + '/platform/linux64/bin:' +
            os.environ['LD_LIBRARY_PATH']
        )
        
def LoadNPI():
    global NPI_AVAILABLE, npisys, waveform
    # 清除 pynpi 相关缓存（允许重试）
    for name in list(sys.modules.keys()):
        if name == 'pynpi' or name.startswith('pynpi.'):
            sys.modules.pop(name, None)
    try:
        # Temporarily redirect stdout during pynpi import to avoid log pollution
        _old_stdout = sys.stdout
        sys.stdout = sys.stderr
        try:
            import pynpi.npisys as npisys_module
            import pynpi.waveform as waveform_module
            npisys = npisys_module
            waveform = waveform_module
            NPI_AVAILABLE = True
            # Note: logger not available yet during initial load
        finally:
            sys.stdout = _old_stdout
    except ImportError as e:
        NPI_AVAILABLE = False
        # Note: logger not available yet during initial load
        logging.warning(f"pynpi not available - FSDB reading will not work. Error: {e}")
    except Exception as e:
        NPI_AVAILABLE = False
        logging.error(f"Unexpected error loading NPI: {e}")
from mcp.server.models import InitializationOptions
from mcp.server import NotificationOptions, Server
import mcp.server.stdio
import mcp.types as types


# Create unique temporary working directory for this server instance
temp_base = Path(tempfile.gettempdir()) / "fsdb-mcp-server"
temp_base.mkdir(exist_ok=True)
temp_work_dir = temp_base / f"session-{uuid.uuid4().hex[:8]}"
temp_work_dir.mkdir(exist_ok=True)
os.chdir(temp_work_dir)


# Configure logging - write to file to avoid interfering with MCP stdio communication
# Use absolute path based on server.py location to ensure logs are written correctly

log_dir = temp_work_dir / "logs"
log_dir.mkdir(exist_ok=True)
log_file = log_dir / "fsdb_mcp_server.log"

logging.basicConfig(
    level=logging.ERROR,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file, mode='a'),
        logging.StreamHandler(sys.stderr)  # Also log to stderr (not stdout)
    ]
)
logger = logging.getLogger("fsdb-mcp-server")
logger.info("=" * 60)
logger.info("FSDB MCP Server starting...")
logger.info(f"Server script: {__file__}")
logger.info(f"Log file: {log_file.absolute()}")
logger.info(f"VERDI_HOME: {os.environ.get('VERDI_HOME', 'NOT SET')}")
logger.info(f"LD_LIBRARY_PATH: {os.environ.get('LD_LIBRARY_PATH', 'NOT SET')}")
logger.info(f"PYTHONPATH: {os.environ.get('PYTHONPATH', 'NOT SET')}")
logger.info(f"Created temporary working directory: {temp_work_dir}")
logger.info(f"Changed working directory to: {os.getcwd()}")

# Configuration constants
MAX_SIGNALS_RETURN = 10  # Maximum number of signals to return
MAX_SCOPES_RETURN = 10   # Maximum number of scopes to return
MAX_CHANGES_RETURN = 10 # Maximum number of value changes to return

# Global state
server = Server("fsdb-mcp-server")
opened_files: Dict[str, Any] = {}  # path -> FileHandle
npi_initialized = False
temp_work_dir: Optional[Path] = None  # Temporary working directory for this session


@contextlib.contextmanager
def suppress_npi_stdout():
    """Suppress NPI stdout output to avoid interfering with MCP JSON-RPC communication."""
    # Save the original stdout file descriptor
    old_stdout_fd = os.dup(1)
    old_stdout = sys.stdout
    try:
        # Redirect file descriptor 1 (stdout) to stderr (fd 2)
        # This catches output from C libraries that write directly to fd 1
        os.dup2(2, 1)
        sys.stdout = sys.stderr
        yield
    finally:
        # Restore original stdout
        os.dup2(old_stdout_fd, 1)
        os.close(old_stdout_fd)
        sys.stdout = old_stdout


def ensure_npi_init():
    """Ensure NPI system is initialized."""
    global npi_initialized
    global NPI_AVAILABLE
    
    logger.debug(f"ensure_npi_init called - NPI_AVAILABLE: {NPI_AVAILABLE}, npi_initialized: {npi_initialized}")
    
    if not NPI_AVAILABLE:
        logger.warning("NPI not available, attempting to load...")
        LoadNPI()
        logger.debug(f"After LoadNPI - NPI_AVAILABLE: {NPI_AVAILABLE}")
    
    if NPI_AVAILABLE and not npi_initialized:
        try:
            logger.info("Initializing NPI system...")
            with suppress_npi_stdout():
                npisys.init(['fsdb-mcp-server'])
            npi_initialized = True
            logger.info("NPI system initialized successfully")
        except Exception as e:
            logger.exception(f"Failed to initialize NPI: {e}")
            raise
    elif not NPI_AVAILABLE:
        logger.error("NPI is not available - cannot initialize")
    else:
        logger.debug("NPI already initialized")


def format_file_info(file_handle: Any) -> Dict[str, Any]:
    """Format file information into a dictionary."""
    info = {
        "name": file_handle.name(),
        "min_time": file_handle.min_time(),
        "max_time": file_handle.max_time(),
        "scale_unit": file_handle.scale_unit(),
        "version": file_handle.version(),
        "sim_date": file_handle.sim_date(),
        "is_completed": file_handle.is_completed(),
        "has_glitch": file_handle.has_glitch(),
        "has_assertion": file_handle.has_assertion(),
        "has_force_tag": file_handle.has_force_tag(),
        "has_reason_code": file_handle.has_reason_code(),
        "has_power_info": file_handle.has_power_info(),
        "has_gate_tech": file_handle.has_gate_tech(),
        "has_seq_num": file_handle.has_seq_num(),
        "dump_off_range": file_handle.dump_off_range(),
    }
    return info


def format_scope_info(scope: Any) -> Dict[str, Any]:
    """Format scope information into a dictionary."""
    info = {
        "name": scope.name(),
        "full_name": scope.full_name(),
        "def_name": scope.def_name(),
        "type": scope.type(False),  # Get string representation
    }
    return info


def format_signal_info(signal: Any) -> Dict[str, Any]:
    """Format signal information into a dictionary."""
    info = {
        "name": signal.name(),
        "full_name": signal.full_name(),
        "is_real": signal.is_real(),
        "has_member": signal.has_member(),
        "left_range": signal.left_range(),
        "right_range": signal.right_range(),
        "range_size": signal.range_size(),
        "is_string": signal.is_string(),
        "direction": signal.direction(False),
        "is_packed": signal.is_packed(),
        "has_reason_code": signal.has_reason_code(),
        "is_param": signal.is_param(),
        "has_enum": signal.has_enum(),
        "has_force_tag": signal.has_force_tag(),
    }
    return info


# Helper functions for optimization
def get_file_handle(path: str) -> Any:
    """Get file handle with error checking."""
    if path not in opened_files:
        raise ValueError(f"File not opened: {path}. Use fsdb_open first.")
    return opened_files[path]


def get_signal(file_handle: Any, signal_path: str) -> Any:
    """Get signal object with error checking."""
    signal = file_handle.sig_by_name(signal_path)
    if signal is None:
        raise ValueError(f"Signal not found: {signal_path}")
    return signal


def parse_format(fmt: str) -> Any:
    """Parse format string to VctFormat_e enum."""
    format_map = {
        "bin": waveform.VctFormat_e.BinStrVal,
        "dec": waveform.VctFormat_e.DecStrVal,
        "hex": waveform.VctFormat_e.HexStrVal,
        "real": waveform.VctFormat_e.RealVal,
    }
    return format_map.get(fmt, waveform.VctFormat_e.HexStrVal)


@server.list_resources()
async def handle_list_resources() -> list[types.Resource]:
    """List available FSDB file resources."""
    resources = []
    for path, file_handle in opened_files.items():
        resources.append(
            types.Resource(
                uri=f"fsdb://{path}",
                name=f"FSDB: {Path(path).name}",
                description=f"FSDB waveform file at {path}",
                mimeType="application/x-fsdb",
            )
        )
    return resources


@server.read_resource()
async def handle_read_resource(uri: str) -> str:
    """Read FSDB file information."""
    if not uri.startswith("fsdb://"):
        raise ValueError(f"Invalid URI scheme: {uri}")
    
    path = uri[7:]  # Remove "fsdb://" prefix
    
    if path not in opened_files:
        raise ValueError(f"File not opened: {path}")
    
    file_handle = opened_files[path]
    info = format_file_info(file_handle)
    
    # Get top-level scopes
    top_scopes = []
    for scope in file_handle.top_scope_list():
        top_scopes.append(format_scope_info(scope))
    
    info["top_scopes"] = top_scopes
    
    return json.dumps(info, indent=2)


@server.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    """List available FSDB tools."""
    return [
        types.Tool(
            name="fsdb_open",
            description="Open an FSDB waveform file",
            inputSchema={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Path to the FSDB file",
                    },
                },
                "required": ["path"],
            },
        ),
        types.Tool(
            name="fsdb_close",
            description="Close an opened FSDB file",
            inputSchema={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Absolute path to the FSDB file to close",
                    },
                },
                "required": ["path"],
            },
        ),
        types.Tool(
            name="fsdb_list_scopes",
            description="List scopes in the FSDB file hierarchy",
            inputSchema={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Absolute path to the FSDB file",
                    },
                    "scope_path": {
                        "type": "string",
                        "description": "Optional scope path to list children of (e.g., 'top.module1')",
                    },
                },
                "required": ["path"],
            },
        ),
        types.Tool(
            name="fsdb_list_signals",
            description="List signals in a scope",
            inputSchema={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Absolute path to the FSDB file",
                    },
                    "scope_path": {
                        "type": "string",
                        "description": "Scope path to list signals from (e.g., 'top.module1')",
                    },
                },
                "required": ["path"],
            },
        ),
        types.Tool(
            name="fsdb_get_signal_info",
            description="Get detailed information about a signal",
            inputSchema={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Absolute path to the FSDB file",
                    },
                    "signal_path": {
                        "type": "string",
                        "description": "Full signal path (e.g., 'top.module1.signal_name')",
                    },
                },
                "required": ["path", "signal_path"],
            },
        ),
        types.Tool(
            name="fsdb_get_signal_value",
            description="Get values of multiple signals at a specific time (batch query)",
            inputSchema={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Absolute path to the FSDB file",
                    },
                    "signal_paths": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of full signal paths to query",
                    },
                    "time": {
                        "type": "integer",
                        "description": "Time point to query",
                    },
                    "format": {
                        "type": "string",
                        "description": "Value format: bin, dec, hex, real",
                        "enum": ["bin", "dec", "hex", "real"],
                    },
                },
                "required": ["path", "signal_paths", "time"],
            },
        ),
        types.Tool(
            name="fsdb_get_signal_changes",
            description="Get value changes of multiple signals in a time range (batch query)",
            inputSchema={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Absolute path to the FSDB file",
                    },
                    "signal_paths": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of full signal paths to query",
                    },
                    "start_time": {
                        "type": "integer",
                        "description": "Start time",
                    },
                    "end_time": {
                        "type": "integer",
                        "description": "End time",
                    },
                    "format": {
                        "type": "string",
                        "description": "Value format: bin, dec, hex, real",
                        "enum": ["bin", "dec", "hex", "real"],
                    },
                },
                "required": ["path", "signal_paths", "start_time", "end_time"],
            },
        ),
        types.Tool(
            name="fsdb_is_fsdb",
            description="Check if a file is a valid FSDB file",
            inputSchema={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Absolute path to the file to check",
                    },
                },
                "required": ["path"],
            },
        ),
        types.Tool(
            name="fsdb_search",
            description="Search for signals and scopes by name pattern in the FSDB file",
            inputSchema={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Absolute path to the FSDB file",
                    },
                    "pattern": {
                        "type": "string",
                        "description": "Search pattern (case-insensitive substring match)",
                    },
                    "search_type": {
                        "type": "string",
                        "description": "Type of items to search: 'signals', 'scopes', or 'all'",
                        "enum": ["signals", "scopes", "all"],
                    },
                    "scope_path": {
                        "type": "string",
                        "description": "Optional scope path to limit search (e.g., 'top.module1'). If not provided, searches entire hierarchy.",
                    },
                },
                "required": ["path", "pattern"],
            },
        ),
        types.Tool(
            name="fsdb_find_signal_value",
            description="Find when multiple signals have specific values (forward or backward search, batch query)",
            inputSchema={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Absolute path to the FSDB file",
                    },
                    "signal_paths": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of full signal paths to search",
                    },
                    "values": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of values to search for (in string format), one per signal",
                    },
                    "start_time": {
                        "type": "integer",
                        "description": "Starting time for search",
                    },
                    "direction": {
                        "type": "string",
                        "description": "Search direction",
                        "enum": ["forward", "backward"],
                    },
                    "format": {
                        "type": "string",
                        "description": "Value format: bin, dec, hex, real",
                        "enum": ["bin", "dec", "hex", "real"],
                    },
                },
                "required": ["path", "signal_paths", "values", "start_time"],
            },
        ),
        types.Tool(
            name="fsdb_get_signal_statistics",
            description="Get statistics about value changes of multiple signals in a time range (batch query)",
            inputSchema={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Absolute path to the FSDB file",
                    },
                    "signal_paths": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of full signal paths to analyze",
                    },
                    "start_time": {
                        "type": "integer",
                        "description": "Start time",
                    },
                    "end_time": {
                        "type": "integer",
                        "description": "End time",
                    },
                },
                "required": ["path", "signal_paths", "start_time", "end_time"],
            },
        ),
        types.Tool(
            name="fsdb_find_x_values",
            description="Find when multiple signals have X (unknown/undefined) values (batch query)",
            inputSchema={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Absolute path to the FSDB file",
                    },
                    "signal_paths": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of full signal paths to search",
                    },
                    "start_time": {
                        "type": "integer",
                        "description": "Starting time for search",
                    },
                    "direction": {
                        "type": "string",
                        "description": "Search direction",
                        "enum": ["forward", "backward"],
                    },
                    "format": {
                        "type": "string",
                        "description": "Value format: bin, dec, hex, real",
                        "enum": ["bin", "dec", "hex", "real"],
                    },
                },
                "required": ["path", "signal_paths", "start_time"],
            },
        ),
        types.Tool(
            name="fsdb_convert_time",
            description="Convert time values between different units (s, ms, us, ns, ps, fs)",
            inputSchema={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Absolute path to the FSDB file",
                    },
                    "time_value": {
                        "type": "number",
                        "description": "Time value to convert",
                    },
                    "from_unit": {
                        "type": "string",
                        "description": "Source time unit (s, ms, us, ns, ps, fs)",
                    },
                    "to_unit": {
                        "type": "string",
                        "description": "Target time unit (s, ms, us, ns, ps, fs)",
                    },
                },
                "required": ["path", "time_value"],
            },
        ),
        types.Tool(
            name="fsdb_get_signal_members",
            description="Get member signals of a composite signal (array, struct, union, etc.)",
            inputSchema={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Absolute path to the FSDB file",
                    },
                    "signal_path": {
                        "type": "string",
                        "description": "Full signal path",
                    },
                    "include_details": {
                        "type": "boolean",
                        "description": "Include detailed information for each member",
                    },
                },
                "required": ["path", "signal_path"],
            },
        ),
    ]


@server.call_tool()
async def handle_call_tool(
    name: str, arguments: dict | None
) -> list[types.TextContent | types.ImageContent | types.EmbeddedResource]:
    """Handle tool execution requests."""
    # Lazy load NPI on first tool call
    if not NPI_AVAILABLE:
        LoadNPI()
    
    if not NPI_AVAILABLE:
        return [types.TextContent(
            type="text",
            text="Error: pynpi library not available. Please ensure VERDI_HOME is set and pynpi is installed."
        )]
    
    ensure_npi_init()
    
    if arguments is None:
        arguments = {}
    
    try:
        if name == "fsdb_is_fsdb":
            path = arguments["path"]
            is_fsdb = waveform.is_fsdb(path)
            return [types.TextContent(
                type="text",
                text=json.dumps({"is_fsdb": is_fsdb, "path": path}, indent=2)
            )]
        
        elif name == "fsdb_open":
            path = arguments["path"]
            logger.info(f"fsdb_open called with path: {path}")
            logger.debug(f"Current working directory: {os.getcwd()}")
            logger.debug(f"NPI_AVAILABLE: {NPI_AVAILABLE}")
            logger.debug(f"npi_initialized: {npi_initialized}")
            
            if not os.path.exists(path):
                logger.error(f"File not found: {path}")
                return [types.TextContent(
                    type="text",
                    text=f"Error: File not found: {path}"
                )]
            
            logger.info(f"File exists, size: {os.path.getsize(path)} bytes")
            
            if path in opened_files:
                logger.warning(f"File already opened: {path} close first")
                #return [types.TextContent(
                #    type="text",
                #    text=f"File already opened: {path}"
                #)]
                file_handle = opened_files[path]
                with suppress_npi_stdout():
                    waveform.close(file_handle)
                del opened_files[path]
            
            try:
                logger.info(f"Attempting to open FSDB file: {path}")
                ensure_npi_init()
                with suppress_npi_stdout():
                    file_handle = waveform.open(path)
                
                logger.debug(f"waveform.open() returned: {file_handle}")
                
                if file_handle is None:
                    logger.error(f"waveform.open() returned None for path: {path}")
                    logger.error(f"Possible reasons:")
                    logger.error(f"  1. File is not a valid FSDB file")
                    logger.error(f"  2. NPI library not properly initialized")
                    logger.error(f"  3. File permissions issue")
                    logger.error(f"  4. Corrupted FSDB file")
                    return [types.TextContent(
                        type="text",
                        text=f"Error: Failed to open FSDB file: {path}"
                    )]
                
                logger.info(f"Successfully opened FSDB file: {path}")
                opened_files[path] = file_handle
                with suppress_npi_stdout():
                    info = format_file_info(file_handle)
                logger.debug(f"File info: {info}")
                
                return [types.TextContent(
                    type="text",
                    text=json.dumps({"status": "opened", "info": info}, indent=2)
                )]
            except Exception as e:
                logger.exception(f"Exception while opening FSDB file: {path}")
                return [types.TextContent(
                    type="text",
                    text=f"Error: Exception while opening FSDB file: {path}\n{str(e)}"
                )]
        
        elif name == "fsdb_close":
            path = arguments["path"]
            if path not in opened_files:
                return [types.TextContent(
                    type="text",
                    text=f"Error: File not opened: {path}"
                )]
            
            file_handle = opened_files[path]
            with suppress_npi_stdout():
                waveform.close(file_handle)
            del opened_files[path]
            
            return [types.TextContent(
                type="text",
                text=json.dumps({"status": "closed", "path": path}, indent=2)
            )]
        
        elif name == "fsdb_list_scopes":
            path = arguments["path"]
            scope_path = arguments.get("scope_path")
            
            if path not in opened_files:
                return [types.TextContent(
                    type="text",
                    text=f"Error: File not opened: {path}"
                )]
            
            file_handle = opened_files[path]
            
            with suppress_npi_stdout():
                if scope_path:
                    scope = file_handle.scope_by_name(scope_path)
                    if scope is None:
                        return [types.TextContent(
                            type="text",
                            text=f"Error: Scope not found: {scope_path}"
                        )]
                    scopes = scope.child_scope_list()
                else:
                    scopes = file_handle.top_scope_list()
            
            # Limit the number of scopes returned
            total_scopes = len(scopes)
            truncated = total_scopes > MAX_SCOPES_RETURN
            scopes = scopes[:MAX_SCOPES_RETURN]
            
            with suppress_npi_stdout():
                scope_list = [format_scope_info(s) for s in scopes]
            
            result = {
                "scopes": scope_list,
                "total": total_scopes,
                "returned": len(scope_list),
                "truncated": truncated
            }
            
            return [types.TextContent(
                type="text",
                text=json.dumps(result, indent=2)
            )]
        
        elif name == "fsdb_list_signals":
            path = arguments["path"]
            scope_path = arguments.get("scope_path")
            
            if path not in opened_files:
                return [types.TextContent(
                    type="text",
                    text=f"Error: File not opened: {path}"
                )]
            
            file_handle = opened_files[path]
            
            with suppress_npi_stdout():
                if scope_path:
                    scope = file_handle.scope_by_name(scope_path)
                    if scope is None:
                        return [types.TextContent(
                            type="text",
                            text=f"Error: Scope not found: {scope_path}"
                        )]
                    signals = scope.sig_list()
                else:
                    signals = file_handle.top_sig_list()
            
            # Limit the number of signals returned
            total_signals = len(signals)
            truncated = total_signals > MAX_SIGNALS_RETURN
            signals = signals[:MAX_SIGNALS_RETURN]
            
            with suppress_npi_stdout():
                signal_list = [format_signal_info(s) for s in signals]
            
            result = {
                "signals": signal_list,
                "total": total_signals,
                "returned": len(signal_list),
                "truncated": truncated
            }
            
            return [types.TextContent(
                type="text",
                text=json.dumps(result, indent=2)
            )]
        
        elif name == "fsdb_get_signal_info":
            path = arguments["path"]
            signal_path = arguments["signal_path"]
            
            if path not in opened_files:
                return [types.TextContent(
                    type="text",
                    text=f"Error: File not opened: {path}"
                )]
            
            file_handle = opened_files[path]
            with suppress_npi_stdout():
                signal = file_handle.sig_by_name(signal_path)
            
            if signal is None:
                return [types.TextContent(
                    type="text",
                    text=f"Error: Signal not found: {signal_path}"
                )]
            
            with suppress_npi_stdout():
                info = format_signal_info(signal)
            
            return [types.TextContent(
                type="text",
                text=json.dumps(info, indent=2)
            )]
        
        elif name == "fsdb_get_signal_value":
            path = arguments["path"]
            signal_paths = arguments["signal_paths"]
            time = arguments["time"]
            fmt = arguments.get("format", "hex")
            
            try:
                file_handle = get_file_handle(path)
                vct_format = parse_format(fmt)
                
                # Use L1 batch API for multiple signals
                with suppress_npi_stdout():
                    values = waveform.sig_vec_value_at(
                        file_handle, signal_paths, time, vct_format
                    )
                
                # Combine results
                result = {
                    "time": time,
                    "format": fmt,
                    "signals": [
                        {"path": sig_path, "value": value}
                        for sig_path, value in zip(signal_paths, values)
                    ]
                }
                
                return [types.TextContent(
                    type="text",
                    text=json.dumps(result, indent=2)
                )]
            except Exception as e:
                logger.error(f"Error in fsdb_get_signal_value: {e}", exc_info=True)
                return [types.TextContent(
                    type="text",
                    text=f"Error: {str(e)}"
                )]
        
        elif name == "fsdb_search":
            path = arguments["path"]
            pattern = arguments["pattern"].lower()  # Case-insensitive search
            search_type = arguments.get("search_type", "all")
            scope_path = arguments.get("scope_path")
            
            if path not in opened_files:
                return [types.TextContent(
                    type="text",
                    text=f"Error: File not opened: {path}"
                )]
            
            file_handle = opened_files[path]
            
            # Helper function to recursively search scopes
            def search_scopes_recursive(scope, pattern, results, max_results=MAX_SCOPES_RETURN):
                if len(results) >= max_results:
                    return True  # Truncated
                
                # Check if current scope matches
                if pattern in scope.name().lower() or pattern in scope.full_name().lower():
                    results.append(format_scope_info(scope))
                
                # Search child scopes
                for child_scope in scope.child_scope_list():
                    if search_scopes_recursive(child_scope, pattern, results, max_results):
                        return True
                
                return False
            
            # Helper function to recursively search signals
            def search_signals_recursive(scope, pattern, results, max_results=MAX_SIGNALS_RETURN):
                if len(results) >= max_results:
                    return True  # Truncated
                
                # Search signals in current scope
                for signal in scope.sig_list():
                    if len(results) >= max_results:
                        return True
                    if pattern in signal.name().lower() or pattern in signal.full_name().lower():
                        results.append(format_signal_info(signal))
                
                # Search child scopes
                for child_scope in scope.child_scope_list():
                    if search_signals_recursive(child_scope, pattern, results, max_results):
                        return True
                
                return False
            
            result = {
                "pattern": arguments["pattern"],
                "search_type": search_type,
            }
            
            # Determine starting point
            with suppress_npi_stdout():
                if scope_path:
                    start_scope = file_handle.scope_by_name(scope_path)
                    if start_scope is None:
                        return [types.TextContent(
                            type="text",
                            text=f"Error: Scope not found: {scope_path}"
                        )]
                    start_scopes = [start_scope]
                    result["scope_path"] = scope_path
                else:
                    start_scopes = file_handle.top_scope_list()
                
                # Search for scopes
                if search_type in ["scopes", "all"]:
                    scope_results = []
                    truncated_scopes = False
                    
                    for scope in start_scopes:
                        if search_scopes_recursive(scope, pattern, scope_results):
                            truncated_scopes = True
                            break
                    
                    result["scopes"] = {
                        "matches": scope_results,
                        "count": len(scope_results),
                        "truncated": truncated_scopes
                    }
                
                # Search for signals
                if search_type in ["signals", "all"]:
                    signal_results = []
                    truncated_signals = False
                    
                    for scope in start_scopes:
                        if search_signals_recursive(scope, pattern, signal_results):
                            truncated_signals = True
                            break
                    
                    result["signals"] = {
                        "matches": signal_results,
                        "count": len(signal_results),
                        "truncated": truncated_signals
                    }
            
            return [types.TextContent(
                type="text",
                text=json.dumps(result, indent=2)
            )]
        
        elif name == "fsdb_get_signal_changes":
            path = arguments["path"]
            signal_paths = arguments["signal_paths"]
            start_time = arguments["start_time"]
            end_time = arguments["end_time"]
            fmt = arguments.get("format", "hex")
            
            try:
                file_handle = get_file_handle(path)
                vct_format = parse_format(fmt)
                
                # Batch query by calling single-signal API for each signal
                signals_data = []
                with suppress_npi_stdout():
                    for sig_path in signal_paths:
                        # Call single-signal API
                        changes_list = waveform.sig_value_between(
                            file_handle, sig_path, start_time, end_time, vct_format
                        )
                        
                        # Apply limit per signal
                        changes = [
                            {"time": time, "value": value}
                            for time, value in changes_list[:MAX_CHANGES_RETURN]
                        ]
                        
                        signals_data.append({
                            "signal": sig_path,
                            "changes": changes,
                            "total": len(changes_list),
                            "returned": len(changes),
                            "truncated": len(changes_list) > MAX_CHANGES_RETURN
                        })
                
                result = {
                    "start_time": start_time,
                    "end_time": end_time,
                    "format": fmt,
                    "signals": signals_data
                }
                
                return [types.TextContent(
                    type="text",
                    text=json.dumps(result, indent=2)
                )]
            except Exception as e:
                logger.error(f"Error in fsdb_get_signal_changes: {e}", exc_info=True)
                return [types.TextContent(
                    type="text",
                    text=f"Error: {str(e)}"
                )]
        
        elif name == "fsdb_find_signal_value":
            path = arguments["path"]
            signal_paths = arguments["signal_paths"]
            values = arguments["values"]
            start_time = arguments["start_time"]
            direction = arguments.get("direction", "forward")
            fmt = arguments.get("format", "hex")
            
            try:
                file_handle = get_file_handle(path)
                vct_format = parse_format(fmt)
                
                # Validate that signal_paths and values have the same length
                if len(signal_paths) != len(values):
                    return [types.TextContent(
                        type="text",
                        text=f"Error: signal_paths and values must have the same length (got {len(signal_paths)} and {len(values)})"
                    )]
                
                # Batch query by calling single-signal API for each signal
                signals_data = []
                with suppress_npi_stdout():
                    for sig_path, val in zip(signal_paths, values):
                        if direction == "forward":
                            found_time = waveform.sig_find_value_forward(
                                file_handle, sig_path, val, start_time, vct_format
                            )
                        else:
                            found_time = waveform.sig_find_value_backward(
                                file_handle, sig_path, val, start_time, vct_format
                            )
                        
                        signals_data.append({
                            "signal": sig_path,
                            "value": val,
                            "found_time": found_time,
                            "found": found_time is not None
                        })
                
                result = {
                    "start_time": start_time,
                    "direction": direction,
                    "signals": signals_data
                }
                
                return [types.TextContent(
                    type="text",
                    text=json.dumps(result, indent=2)
                )]
            except Exception as e:
                logger.error(f"Error in fsdb_find_signal_value: {e}", exc_info=True)
                return [types.TextContent(
                    type="text",
                    text=f"Error: {str(e)}"
                )]
        
        elif name == "fsdb_get_signal_statistics":
            path = arguments["path"]
            signal_paths = arguments["signal_paths"]
            start_time = arguments["start_time"]
            end_time = arguments["end_time"]
            
            try:
                file_handle = get_file_handle(path)
                
                # Batch query by calling single-signal API for each signal
                signals_data = []
                with suppress_npi_stdout():
                    for sig_path in signal_paths:
                        vc_count = waveform.sig_vc_count(
                            file_handle, sig_path, start_time, end_time
                        )
                        signals_data.append({
                            "signal": sig_path,
                            "value_change_count": vc_count
                        })
                    
                    # Get file time range for context
                    file_min_time = file_handle.min_time()
                    file_max_time = file_handle.max_time()
                
                result = {
                    "start_time": start_time,
                    "end_time": end_time,
                    "time_range": end_time - start_time,
                    "signals": signals_data,
                    "file_time_range": {
                        "min": file_min_time,
                        "max": file_max_time
                    }
                }
                
                return [types.TextContent(
                    type="text",
                    text=json.dumps(result, indent=2)
                )]
            except Exception as e:
                logger.error(f"Error in fsdb_get_signal_statistics: {e}", exc_info=True)
                return [types.TextContent(
                    type="text",
                    text=f"Error: {str(e)}"
                )]
        
        elif name == "fsdb_find_x_values":
            path = arguments["path"]
            signal_paths = arguments["signal_paths"]
            start_time = arguments["start_time"]
            direction = arguments.get("direction", "forward")
            fmt = arguments.get("format", "hex")
            
            try:
                file_handle = get_file_handle(path)
                vct_format = parse_format(fmt)
                
                # Batch query by calling single-signal API for each signal
                signals_data = []
                with suppress_npi_stdout():
                    for sig_path in signal_paths:
                        if direction == "forward":
                            result_tuple = waveform.sig_find_x_forward(
                                file_handle, sig_path, start_time, vct_format
                            )
                        else:
                            result_tuple = waveform.sig_find_x_backward(
                                file_handle, sig_path, start_time, vct_format
                            )
                        
                        if result_tuple:
                            time, value = result_tuple
                            signals_data.append({
                                "signal": sig_path,
                                "found_time": time,
                                "value": value,
                                "found": True
                            })
                        else:
                            signals_data.append({
                                "signal": sig_path,
                                "found": False
                            })
                
                result = {
                    "start_time": start_time,
                    "direction": direction,
                    "signals": signals_data
                }
                
                return [types.TextContent(
                    type="text",
                    text=json.dumps(result, indent=2)
                )]
            except Exception as e:
                logger.error(f"Error in fsdb_find_x_values: {e}", exc_info=True)
                return [types.TextContent(
                    type="text",
                    text=f"Error: {str(e)}"
                )]
        
        elif name == "fsdb_convert_time":
            path = arguments["path"]
            time_value = arguments["time_value"]
            from_unit = arguments.get("from_unit")
            to_unit = arguments.get("to_unit")
            
            try:
                file_handle = get_file_handle(path)
                
                # Use L1 time conversion API
                with suppress_npi_stdout():
                    # Get file time unit
                    file_time_unit = waveform.time_scale_unit(file_handle)
                    
                    if from_unit:
                        # Convert input time to file time unit
                        time_in = waveform.convert_time_in(file_handle, time_value, from_unit)
                    else:
                        time_in = time_value
                    
                    if to_unit:
                        # Convert file time unit to output time unit
                        time_out = waveform.convert_time_out(file_handle, time_in, to_unit)
                    else:
                        time_out = time_in
                
                result = {
                    "input_value": time_value,
                    "input_unit": from_unit or file_time_unit,
                    "output_value": time_out,
                    "output_unit": to_unit or file_time_unit,
                    "file_time_unit": file_time_unit
                }
                
                return [types.TextContent(
                    type="text",
                    text=json.dumps(result, indent=2)
                )]
            except Exception as e:
                logger.error(f"Error in fsdb_convert_time: {e}", exc_info=True)
                return [types.TextContent(
                    type="text",
                    text=f"Error: {str(e)}"
                )]
        
        elif name == "fsdb_get_signal_members":
            path = arguments["path"]
            signal_path = arguments["signal_path"]
            include_details = arguments.get("include_details", False)
            
            try:
                file_handle = get_file_handle(path)
                signal = get_signal(file_handle, signal_path)
                
                with suppress_npi_stdout():
                    if not signal.has_member():
                        return [types.TextContent(
                            type="text",
                            text=json.dumps({
                                "signal": signal_path,
                                "has_members": False,
                                "members": []
                            }, indent=2)
                        )]
                    
                    members = signal.member_list()
                    
                    if include_details:
                        # Include full details for each member
                        member_list = [format_signal_info(m) for m in members]
                    else:
                        # Include only basic info
                        member_list = [
                            {
                                "name": m.name(),
                                "full_name": m.full_name(),
                                "left_range": m.left_range(),
                                "right_range": m.right_range(),
                                "range_size": m.range_size(),
                            }
                            for m in members
                        ]
                
                result = {
                    "signal": signal_path,
                    "has_members": True,
                    "member_count": len(member_list),
                    "members": member_list
                }
                
                return [types.TextContent(
                    type="text",
                    text=json.dumps(result, indent=2)
                )]
            except Exception as e:
                logger.error(f"Error in fsdb_get_signal_members: {e}", exc_info=True)
                return [types.TextContent(
                    type="text",
                    text=f"Error: {str(e)}"
                )]
        
        else:
            return [types.TextContent(
                type="text",
                text=f"Error: Unknown tool: {name}"
            )]
    
    except Exception as e:
        logger.error(f"Error executing tool {name}: {e}", exc_info=True)
        return [types.TextContent(
            type="text",
            text=f"Error: {str(e)}"
        )]


async def main():
    """Main entry point for the server."""
    logger.info("=" * 60)
    logger.info("Starting FSDB MCP Server")
    logger.info(f"NPI Available: {NPI_AVAILABLE}")
    logger.info(f"Python version: {sys.version}")
    logger.info(f"Working directory: {os.getcwd()}")
    
    # Run the server using stdin/stdout streams
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="fsdb-mcp-server",
                server_version="0.1.0",
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
            ),
        )


def cleanup():
    """Cleanup function to close all files and shutdown NPI."""
    global npi_initialized, temp_work_dir
    
    # Close all opened files
    for path, file_handle in list(opened_files.items()):
        try:
            waveform.close(file_handle)
            logger.info(f"Closed file: {path}")
        except Exception as e:
            logger.error(f"Error closing file {path}: {e}")
    
    opened_files.clear()
    
    # Shutdown NPI
    if NPI_AVAILABLE and npi_initialized:
        try:
            with suppress_npi_stdout():
                npisys.end()
            npi_initialized = False
            logger.info("NPI system shutdown")
        except Exception as e:
            logger.error(f"Error shutting down NPI: {e}")
    
    # Clean up temporary working directory
    if temp_work_dir and temp_work_dir.exists():
        try:
            import shutil
            shutil.rmtree(temp_work_dir)
            logger.info(f"Cleaned up temporary directory: {temp_work_dir}")
        except Exception as e:
            logger.warning(f"Could not clean up temporary directory {temp_work_dir}: {e}")


if __name__ == "__main__":
    import asyncio
    import atexit
    
    # Register cleanup handler
    atexit.register(cleanup)
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Server interrupted by user")
    except Exception as e:
        logger.error(f"Server error: {e}", exc_info=True)
    finally:
        cleanup()
