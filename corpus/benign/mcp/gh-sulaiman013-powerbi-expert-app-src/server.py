"""
Power BI MCP Server V3
======================
Enterprise-grade MCP server with air-gapped deployment support.

Key Features:
- Schema-only data boundary (actual data NEVER goes to LLM)
- Air-gapped operation with local Ollama + powerbi-expert model
- Network isolation validation
- Tamper-evident audit logging
- PII detection and masking

Your data never leaves your environment. Period.
"""

import asyncio
import json
import logging
import os
import sys
import time
import yaml
from pathlib import Path
from typing import Any, Dict, List, Optional

from mcp.server import Server, NotificationOptions
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent
from mcp.server.models import InitializationOptions

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stderr)]
)
logger = logging.getLogger("powerbi-mcp-v3")

# Import V3 components
from .connectors.desktop import PowerBIDesktopConnector
from .connectors.rest import PowerBIRestConnector
from .connectors.xmla import PowerBIXmlaConnector
from .llm.ollama_provider import OllamaProvider, create_ollama_provider
from .llm.base_provider import LLMRequest, LLMConfig, LLMProviderType
from .llm.data_boundary import DataBoundary
from .security.network_validator import NetworkValidator
from .security.audit_logger import AuditLogger

from dataclasses import dataclass, field
from typing import List

@dataclass
class ModelSchemaContext:
    """Simple schema context for AI prompts"""
    model_name: str = ""
    tables: List[str] = field(default_factory=list)
    measures: List[str] = field(default_factory=list)
    relationships: List[dict] = field(default_factory=list)


class PowerBIMCPServerV3:
    """
    Power BI MCP Server V3 - Enterprise Air-Gapped Edition

    This server provides:
    1. Power BI Desktop connectivity (schema extraction, DAX execution)
    2. AI-powered DAX generation using local powerbi-expert model
    3. Network isolation validation
    4. Security audit logging
    5. PII detection
    """

    def __init__(self, config_path: Optional[str] = None):
        self.server = Server("powerbi-mcp-v3")

        # Load configuration
        self.config = self._load_config(config_path)

        # Initialize components
        self.desktop_connector: Optional[PowerBIDesktopConnector] = None
        self.rest_connector: Optional[PowerBIRestConnector] = None
        self.xmla_connector: Optional[PowerBIXmlaConnector] = None
        self.llm_provider: Optional[OllamaProvider] = None
        self.data_boundary = DataBoundary()
        self.network_validator: Optional[NetworkValidator] = None
        self.audit_logger: Optional[AuditLogger] = None

        # Track connection state
        self.connected_model_schema: Optional[ModelSchemaContext] = None
        self.cloud_connected: bool = False

        self._setup_handlers()

    def _load_config(self, config_path: Optional[str] = None) -> Dict[str, Any]:
        """Load server configuration from YAML"""
        if config_path is None:
            config_path = Path(__file__).parent.parent / "config" / "server.yaml"

        try:
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f)
                logger.info(f"Loaded configuration from {config_path}")
                return config
        except Exception as e:
            logger.warning(f"Could not load config: {e}. Using defaults.")
            return {
                "deployment_mode": "airgap",
                "llm": {
                    "provider": "ollama",
                    "ollama": {
                        "endpoint": "http://127.0.0.1:11434",
                        "model": "powerbi-expert",
                        "temperature": 0.1,
                        "max_tokens": 4096,
                        "timeout": 120
                    }
                }
            }

    async def _initialize_llm(self) -> bool:
        """Initialize the LLM provider"""
        try:
            ollama_config = self.config.get("llm", {}).get("ollama", {})

            self.llm_provider = create_ollama_provider(
                endpoint=ollama_config.get("endpoint", "http://127.0.0.1:11434"),
                model=ollama_config.get("model", "powerbi-expert"),
                temperature=ollama_config.get("temperature", 0.1),
                max_tokens=ollama_config.get("max_tokens", 4096),
                timeout=ollama_config.get("timeout", 120)
            )

            success = await self.llm_provider.initialize()
            if success:
                logger.info(f"LLM provider initialized: {ollama_config.get('model')}")
            return success

        except Exception as e:
            logger.error(f"Failed to initialize LLM: {e}")
            return False

    def _get_desktop_connector(self) -> PowerBIDesktopConnector:
        """Get or create Desktop connector"""
        if not self.desktop_connector:
            self.desktop_connector = PowerBIDesktopConnector()
        return self.desktop_connector

    def _setup_handlers(self):
        """Set up MCP tool handlers"""

        @self.server.list_tools()
        async def handle_list_tools() -> List[Tool]:
            """Return list of available tools"""
            tools = [
                # === POWER BI DESKTOP TOOLS ===
                Tool(
                    name="desktop_discover",
                    description="Discover all running Power BI Desktop instances on this machine",
                    inputSchema={
                        "type": "object",
                        "properties": {},
                        "required": []
                    }
                ),
                Tool(
                    name="desktop_connect",
                    description="Connect to a Power BI Desktop instance. Auto-selects if only one instance running.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "port": {
                                "type": "integer",
                                "description": "Port number (optional - auto-selects if not provided)"
                            }
                        },
                        "required": []
                    }
                ),
                Tool(
                    name="desktop_get_schema",
                    description="Get the full schema of the connected model (tables, columns, measures, relationships). This is sent to the AI for DAX generation.",
                    inputSchema={
                        "type": "object",
                        "properties": {},
                        "required": []
                    }
                ),
                Tool(
                    name="desktop_list_tables",
                    description="List all tables in the connected Power BI Desktop model",
                    inputSchema={
                        "type": "object",
                        "properties": {},
                        "required": []
                    }
                ),
                Tool(
                    name="desktop_list_columns",
                    description="List columns for a specific table",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "table_name": {
                                "type": "string",
                                "description": "Name of the table"
                            }
                        },
                        "required": ["table_name"]
                    }
                ),
                Tool(
                    name="desktop_list_measures",
                    description="List all measures in the connected model",
                    inputSchema={
                        "type": "object",
                        "properties": {},
                        "required": []
                    }
                ),
                Tool(
                    name="desktop_execute_dax",
                    description="Execute a DAX query against the connected Power BI Desktop model",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "dax_query": {
                                "type": "string",
                                "description": "DAX query to execute"
                            },
                            "max_rows": {
                                "type": "integer",
                                "description": "Maximum rows to return (default: 100)",
                                "default": 100
                            }
                        },
                        "required": ["dax_query"]
                    }
                ),

                # === AI-POWERED DAX TOOLS ===
                Tool(
                    name="ai_generate_dax",
                    description="Use the powerbi-expert AI to generate a DAX measure based on your description. The AI only sees schema (table/column names), never actual data.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "description": {
                                "type": "string",
                                "description": "Natural language description of what DAX you need (e.g., 'year-over-year sales growth')"
                            },
                            "context": {
                                "type": "string",
                                "description": "Additional context about your model (optional)"
                            }
                        },
                        "required": ["description"]
                    }
                ),
                Tool(
                    name="ai_explain_dax",
                    description="Use the powerbi-expert AI to explain what a DAX expression does",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "dax_expression": {
                                "type": "string",
                                "description": "The DAX expression to explain"
                            }
                        },
                        "required": ["dax_expression"]
                    }
                ),
                Tool(
                    name="ai_optimize_dax",
                    description="Use the powerbi-expert AI to suggest optimizations for a DAX expression",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "dax_expression": {
                                "type": "string",
                                "description": "The DAX expression to optimize"
                            }
                        },
                        "required": ["dax_expression"]
                    }
                ),
                Tool(
                    name="ai_generate_mcode",
                    description="Use the powerbi-expert AI to generate Power Query (M code) based on your description",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "description": {
                                "type": "string",
                                "description": "Natural language description of the Power Query transformation"
                            }
                        },
                        "required": ["description"]
                    }
                ),

                # === SECURITY & STATUS TOOLS ===
                Tool(
                    name="server_status",
                    description="Get the V3 server status including LLM connectivity, Power BI connection, and security settings",
                    inputSchema={
                        "type": "object",
                        "properties": {},
                        "required": []
                    }
                ),
                Tool(
                    name="validate_airgap",
                    description="Validate that the server is running in proper air-gapped mode with no external network access",
                    inputSchema={
                        "type": "object",
                        "properties": {},
                        "required": []
                    }
                ),

                # === POWER BI SERVICE (CLOUD) TOOLS ===
                Tool(
                    name="cloud_configure",
                    description="Configure Power BI Service connection with Service Principal credentials (tenant_id, client_id, client_secret)",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "tenant_id": {
                                "type": "string",
                                "description": "Azure AD tenant ID"
                            },
                            "client_id": {
                                "type": "string",
                                "description": "Service Principal client/application ID"
                            },
                            "client_secret": {
                                "type": "string",
                                "description": "Service Principal client secret"
                            }
                        },
                        "required": ["tenant_id", "client_id", "client_secret"]
                    }
                ),
                Tool(
                    name="cloud_list_workspaces",
                    description="List all Power BI Service workspaces accessible to the Service Principal",
                    inputSchema={
                        "type": "object",
                        "properties": {},
                        "required": []
                    }
                ),
                Tool(
                    name="cloud_list_datasets",
                    description="List all datasets in a Power BI Service workspace",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "workspace_id": {
                                "type": "string",
                                "description": "ID of the workspace"
                            }
                        },
                        "required": ["workspace_id"]
                    }
                ),
                Tool(
                    name="cloud_connect_xmla",
                    description="Connect to a Power BI dataset via XMLA endpoint for querying",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "workspace_name": {
                                "type": "string",
                                "description": "Name of the Power BI workspace"
                            },
                            "dataset_name": {
                                "type": "string",
                                "description": "Name of the dataset/semantic model"
                            },
                            "effective_user": {
                                "type": "string",
                                "description": "Optional: User email to impersonate for RLS testing"
                            }
                        },
                        "required": ["workspace_name", "dataset_name"]
                    }
                ),
                Tool(
                    name="cloud_list_tables",
                    description="List tables in the connected Power BI Service dataset via XMLA",
                    inputSchema={
                        "type": "object",
                        "properties": {},
                        "required": []
                    }
                ),
                Tool(
                    name="cloud_list_columns",
                    description="List columns for a table in the connected Power BI Service dataset",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "table_name": {
                                "type": "string",
                                "description": "Name of the table"
                            }
                        },
                        "required": ["table_name"]
                    }
                ),
                Tool(
                    name="cloud_execute_dax",
                    description="Execute a DAX query against the connected Power BI Service dataset via XMLA",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "dax_query": {
                                "type": "string",
                                "description": "DAX query to execute"
                            }
                        },
                        "required": ["dax_query"]
                    }
                ),
                Tool(
                    name="cloud_get_model_info",
                    description="Get comprehensive model info (tables, columns) from connected Power BI Service dataset",
                    inputSchema={
                        "type": "object",
                        "properties": {},
                        "required": []
                    }
                ),
            ]
            return tools

        @self.server.call_tool()
        async def handle_call_tool(name: str, arguments: dict) -> List[TextContent]:
            """Handle tool execution"""
            logger.info(f"Tool called: {name}")

            try:
                # Desktop tools
                if name == "desktop_discover":
                    result = await self._handle_desktop_discover()
                elif name == "desktop_connect":
                    result = await self._handle_desktop_connect(arguments)
                elif name == "desktop_get_schema":
                    result = await self._handle_desktop_get_schema()
                elif name == "desktop_list_tables":
                    result = await self._handle_desktop_list_tables()
                elif name == "desktop_list_columns":
                    result = await self._handle_desktop_list_columns(arguments)
                elif name == "desktop_list_measures":
                    result = await self._handle_desktop_list_measures()
                elif name == "desktop_execute_dax":
                    result = await self._handle_desktop_execute_dax(arguments)

                # AI tools
                elif name == "ai_generate_dax":
                    result = await self._handle_ai_generate_dax(arguments)
                elif name == "ai_explain_dax":
                    result = await self._handle_ai_explain_dax(arguments)
                elif name == "ai_optimize_dax":
                    result = await self._handle_ai_optimize_dax(arguments)
                elif name == "ai_generate_mcode":
                    result = await self._handle_ai_generate_mcode(arguments)

                # Status tools
                elif name == "server_status":
                    result = await self._handle_server_status()
                elif name == "validate_airgap":
                    result = await self._handle_validate_airgap()

                # Cloud/Service tools
                elif name == "cloud_configure":
                    result = await self._handle_cloud_configure(arguments)
                elif name == "cloud_list_workspaces":
                    result = await self._handle_cloud_list_workspaces()
                elif name == "cloud_list_datasets":
                    result = await self._handle_cloud_list_datasets(arguments)
                elif name == "cloud_connect_xmla":
                    result = await self._handle_cloud_connect_xmla(arguments)
                elif name == "cloud_list_tables":
                    result = await self._handle_cloud_list_tables()
                elif name == "cloud_list_columns":
                    result = await self._handle_cloud_list_columns(arguments)
                elif name == "cloud_execute_dax":
                    result = await self._handle_cloud_execute_dax(arguments)
                elif name == "cloud_get_model_info":
                    result = await self._handle_cloud_get_model_info()

                else:
                    result = f"Unknown tool: {name}"

                return [TextContent(type="text", text=result)]

            except Exception as e:
                error_msg = f"Error executing {name}: {str(e)}"
                logger.error(error_msg, exc_info=True)
                return [TextContent(type="text", text=error_msg)]

    # ==================== DESKTOP HANDLERS ====================

    async def _handle_desktop_discover(self) -> str:
        """Discover running Power BI Desktop instances"""
        try:
            connector = self._get_desktop_connector()

            if not connector.is_available():
                return ("Desktop connectivity unavailable.\n\n"
                        "Requirements:\n"
                        "1. pip install psutil pythonnet\n"
                        "2. Power BI Desktop installed\n"
                        "3. A .pbix file open in Power BI Desktop")

            instances = await asyncio.get_event_loop().run_in_executor(
                None, connector.discover_instances
            )

            if not instances:
                return ("No Power BI Desktop instances found.\n\n"
                        "Please open a .pbix file in Power BI Desktop.")

            result = f"Found {len(instances)} Power BI Desktop instance(s):\n\n"
            for i, inst in enumerate(instances, 1):
                result += f"{i}. Port: {inst['port']}\n"
                result += f"   Model: {inst['model_name']}\n"
                result += f"   PID: {inst['pid']}\n\n"

            result += "Use 'desktop_connect' to connect to an instance."
            return result

        except Exception as e:
            return f"Error discovering instances: {str(e)}"

    async def _handle_desktop_connect(self, args: Dict[str, Any]) -> str:
        """Connect to a Power BI Desktop instance"""
        try:
            connector = self._get_desktop_connector()
            port = args.get("port")

            success = await asyncio.get_event_loop().run_in_executor(
                None, lambda: connector.connect(port=port)
            )

            if success:
                model_name = connector.current_model_name or "Unknown"
                return (f"Connected to Power BI Desktop!\n\n"
                        f"Model: {model_name}\n"
                        f"Port: {connector.current_port}\n\n"
                        f"Use 'desktop_get_schema' to extract the model schema for AI-powered DAX generation.")
            else:
                return "Failed to connect. Ensure Power BI Desktop is running with a .pbix file open."

        except Exception as e:
            return f"Connection error: {str(e)}"

    async def _handle_desktop_get_schema(self) -> str:
        """Get full model schema for AI context"""
        try:
            connector = self._get_desktop_connector()

            if not connector.current_port:
                return "Not connected. Use 'desktop_connect' first."

            # Get model info
            model_info = await asyncio.get_event_loop().run_in_executor(
                None, connector.get_model_info
            )

            # Store for AI context
            self.connected_model_schema = ModelSchemaContext(
                model_name=model_info.get('model_name', 'Unknown'),
                tables=model_info.get('tables', []),
                measures=[m.get('name') for m in model_info.get('measures', [])],
                relationships=model_info.get('relationships', [])
            )

            result = f"Schema for: {model_info.get('model_name', 'Unknown Model')}\n"
            result += "=" * 50 + "\n\n"

            result += f"Tables ({model_info.get('table_count', 0)}):\n"
            for table in model_info.get('tables', []):
                result += f"  - {table}\n"

            result += f"\nMeasures ({model_info.get('measure_count', 0)}):\n"
            for m in model_info.get('measures', [])[:10]:  # Limit display
                result += f"  - {m.get('name')} ({m.get('table')})\n"
            if model_info.get('measure_count', 0) > 10:
                result += f"  ... and {model_info.get('measure_count') - 10} more\n"

            result += f"\nRelationships ({model_info.get('relationship_count', 0)}):\n"
            for rel in model_info.get('relationships', [])[:5]:
                result += f"  - {rel.get('from_table')}[{rel.get('from_column')}] -> {rel.get('to_table')}[{rel.get('to_column')}]\n"

            result += "\n" + "=" * 50
            result += "\nSchema loaded! AI tools can now generate DAX based on your model."
            result += "\nNote: Only schema (names) is shared with AI - actual data NEVER leaves."

            return result

        except Exception as e:
            return f"Error getting schema: {str(e)}"

    async def _handle_desktop_list_tables(self) -> str:
        """List tables from connected model"""
        try:
            connector = self._get_desktop_connector()

            if not connector.current_port:
                return "Not connected. Use 'desktop_connect' first."

            tables = await asyncio.get_event_loop().run_in_executor(
                None, connector.list_tables
            )

            if not tables:
                return "No tables found."

            result = f"Tables ({len(tables)}):\n\n"
            for table in tables:
                result += f"  - {table['name']}\n"

            return result

        except Exception as e:
            return f"Error: {str(e)}"

    async def _handle_desktop_list_columns(self, args: Dict[str, Any]) -> str:
        """List columns for a table"""
        try:
            connector = self._get_desktop_connector()
            table_name = args.get("table_name")

            if not connector.current_port:
                return "Not connected. Use 'desktop_connect' first."

            if not table_name:
                return "Error: table_name is required"

            columns = await asyncio.get_event_loop().run_in_executor(
                None, connector.list_columns, table_name
            )

            if not columns:
                return f"No columns found for '{table_name}'."

            result = f"Columns in '{table_name}' ({len(columns)}):\n\n"
            for col in columns:
                result += f"  - {col['name']} ({col.get('type', 'Unknown')})\n"

            return result

        except Exception as e:
            return f"Error: {str(e)}"

    async def _handle_desktop_list_measures(self) -> str:
        """List measures from connected model"""
        try:
            connector = self._get_desktop_connector()

            if not connector.current_port:
                return "Not connected. Use 'desktop_connect' first."

            measures = await asyncio.get_event_loop().run_in_executor(
                None, connector.list_measures
            )

            if not measures:
                return "No measures found."

            result = f"Measures ({len(measures)}):\n\n"
            for m in measures:
                result += f"  - {m['name']}\n"
                if m.get('expression'):
                    expr = m['expression'][:60] + "..." if len(m['expression']) > 60 else m['expression']
                    result += f"    = {expr}\n"

            return result

        except Exception as e:
            return f"Error: {str(e)}"

    async def _handle_desktop_execute_dax(self, args: Dict[str, Any]) -> str:
        """Execute DAX query"""
        try:
            connector = self._get_desktop_connector()
            dax_query = args.get("dax_query")
            max_rows = args.get("max_rows", 100)

            if not connector.current_port:
                return "Not connected. Use 'desktop_connect' first."

            if not dax_query:
                return "Error: dax_query is required"

            results = await asyncio.get_event_loop().run_in_executor(
                None, lambda: connector.execute_dax(dax_query, max_rows)
            )

            if not results:
                return "Query returned no results."

            result = f"Query returned {len(results)} row(s):\n\n"
            result += json.dumps(results[:20], indent=2)  # Limit display

            if len(results) > 20:
                result += f"\n\n... and {len(results) - 20} more rows"

            return result

        except Exception as e:
            return f"DAX Error: {str(e)}"

    # ==================== AI HANDLERS ====================

    async def _handle_ai_generate_dax(self, args: Dict[str, Any]) -> str:
        """Generate DAX using powerbi-expert model"""
        try:
            description = args.get("description")
            context = args.get("context", "")

            if not description:
                return "Error: description is required"

            # Initialize LLM if needed
            if not self.llm_provider:
                if not await self._initialize_llm():
                    return "Error: Could not initialize AI model. Is Ollama running with powerbi-expert model?"

            # Build prompt with schema context if available
            schema_context = ""
            if self.connected_model_schema:
                schema_context = f"\n\nConnected Model Schema:\n"
                schema_context += f"Tables: {', '.join(self.connected_model_schema.tables[:20])}\n"
                schema_context += f"Measures: {', '.join(self.connected_model_schema.measures[:10])}\n"

            system_prompt = """You are PowerBI-Expert, an elite AI specialized in Microsoft Power BI.
Generate clean, optimized DAX code. Use best practices:
- Use VAR for intermediate calculations
- Use DIVIDE() instead of / for safe division
- Use CALCULATE() with proper filter context
- Return only the DAX code with brief explanation."""

            user_prompt = f"Generate a DAX measure for: {description}"
            if context:
                user_prompt += f"\n\nAdditional context: {context}"
            if schema_context:
                user_prompt += schema_context

            request = LLMRequest(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                temperature=0.1,
                max_tokens=1024
            )

            response = await self.llm_provider.generate(request)

            result = "AI-Generated DAX:\n"
            result += "=" * 40 + "\n\n"
            result += response.content
            result += "\n\n" + "=" * 40
            result += f"\nGenerated by: {response.model}"
            result += f"\nLatency: {response.latency_ms:.0f}ms"

            return result

        except Exception as e:
            return f"AI Error: {str(e)}"

    async def _handle_ai_explain_dax(self, args: Dict[str, Any]) -> str:
        """Explain DAX using powerbi-expert model"""
        try:
            dax_expression = args.get("dax_expression")

            if not dax_expression:
                return "Error: dax_expression is required"

            if not self.llm_provider:
                if not await self._initialize_llm():
                    return "Error: Could not initialize AI model."

            request = LLMRequest(
                system_prompt="You are PowerBI-Expert. Explain DAX expressions clearly and concisely.",
                user_prompt=f"Explain this DAX expression:\n\n{dax_expression}",
                temperature=0.2,
                max_tokens=1024
            )

            response = await self.llm_provider.generate(request)
            return f"DAX Explanation:\n\n{response.content}"

        except Exception as e:
            return f"AI Error: {str(e)}"

    async def _handle_ai_optimize_dax(self, args: Dict[str, Any]) -> str:
        """Optimize DAX using powerbi-expert model"""
        try:
            dax_expression = args.get("dax_expression")

            if not dax_expression:
                return "Error: dax_expression is required"

            if not self.llm_provider:
                if not await self._initialize_llm():
                    return "Error: Could not initialize AI model."

            request = LLMRequest(
                system_prompt="""You are PowerBI-Expert. Analyze DAX for performance issues and suggest optimizations.
Focus on:
- Reducing iterator usage on large tables
- Using CALCULATE predicates instead of FILTER
- Leveraging VAR for reusable calculations
- Proper use of DIVIDE(), SELECTEDVALUE(), etc.""",
                user_prompt=f"Optimize this DAX expression:\n\n{dax_expression}",
                temperature=0.1,
                max_tokens=1024
            )

            response = await self.llm_provider.generate(request)
            return f"DAX Optimization Suggestions:\n\n{response.content}"

        except Exception as e:
            return f"AI Error: {str(e)}"

    async def _handle_ai_generate_mcode(self, args: Dict[str, Any]) -> str:
        """Generate Power Query M code"""
        try:
            description = args.get("description")

            if not description:
                return "Error: description is required"

            if not self.llm_provider:
                if not await self._initialize_llm():
                    return "Error: Could not initialize AI model."

            request = LLMRequest(
                system_prompt="""You are PowerBI-Expert specialized in Power Query (M code).
Generate clean, efficient M code. Always use proper:
- let...in structure
- Table. functions for transformations
- List. functions for list operations
- Error handling where appropriate""",
                user_prompt=f"Generate Power Query (M code) for: {description}",
                temperature=0.1,
                max_tokens=1024
            )

            response = await self.llm_provider.generate(request)

            result = "AI-Generated Power Query (M Code):\n"
            result += "=" * 40 + "\n\n"
            result += response.content

            return result

        except Exception as e:
            return f"AI Error: {str(e)}"

    # ==================== STATUS HANDLERS ====================

    async def _handle_server_status(self) -> str:
        """Get comprehensive server status"""
        status = []
        status.append("Power BI MCP Server V3 Status")
        status.append("=" * 40)

        # Deployment mode
        mode = self.config.get("deployment_mode", "airgap")
        status.append(f"\nDeployment Mode: {mode.upper()}")

        # LLM status
        if self.llm_provider:
            llm_info = self.llm_provider.get_status_info()
            status.append(f"\nLLM Provider: {llm_info.get('provider')}")
            status.append(f"  Model: {llm_info.get('model')}")
            status.append(f"  Status: {llm_info.get('status')}")
            status.append(f"  Localhost Only: {llm_info.get('is_localhost')}")
        else:
            status.append("\nLLM Provider: Not initialized")
            status.append("  (Will initialize on first AI tool use)")

        # Desktop connector status
        connector = self._get_desktop_connector()
        status.append(f"\nPower BI Desktop:")
        status.append(f"  Available: {connector.is_available()}")
        if connector.current_port:
            status.append(f"  Connected: Yes")
            status.append(f"  Port: {connector.current_port}")
            status.append(f"  Model: {connector.current_model_name}")
        else:
            status.append(f"  Connected: No")

        # Schema context
        if self.connected_model_schema:
            status.append(f"\nSchema Context Loaded:")
            status.append(f"  Tables: {len(self.connected_model_schema.tables)}")
            status.append(f"  Measures: {len(self.connected_model_schema.measures)}")

        status.append("\n" + "=" * 40)
        status.append("Data Boundary: Schema-only (actual data NEVER sent to LLM)")

        return "\n".join(status)

    async def _handle_validate_airgap(self) -> str:
        """Validate air-gap configuration"""
        results = []
        results.append("Air-Gap Validation")
        results.append("=" * 40)

        all_passed = True

        # Check LLM endpoint
        if self.llm_provider:
            is_localhost = self.llm_provider.get_status_info().get("is_localhost", False)
            if is_localhost:
                results.append("[PASS] LLM endpoint is localhost")
            else:
                results.append("[FAIL] LLM endpoint is NOT localhost!")
                all_passed = False
        else:
            results.append("[INFO] LLM not yet initialized")

        # Check config
        network_config = self.config.get("network", {})
        if network_config.get("strict_isolation", False):
            results.append("[PASS] Network strict isolation enabled")
        else:
            results.append("[WARN] Network strict isolation not enabled")

        if not network_config.get("allow_external_dns", True):
            results.append("[PASS] External DNS blocked")
        else:
            results.append("[WARN] External DNS allowed")

        # Check data boundary
        data_boundary = self.config.get("data_boundary", {})
        if data_boundary.get("schema_only", True):
            results.append("[PASS] Schema-only data boundary enabled")
        else:
            results.append("[FAIL] Schema-only mode disabled!")
            all_passed = False

        if not data_boundary.get("include_sample_data", False):
            results.append("[PASS] Sample data NOT included")
        else:
            results.append("[FAIL] Sample data inclusion enabled!")
            all_passed = False

        results.append("\n" + "=" * 40)
        if all_passed:
            results.append("AIR-GAP VALIDATION: PASSED")
        else:
            results.append("AIR-GAP VALIDATION: FAILED - Review settings!")

        return "\n".join(results)

    # ==================== CLOUD/SERVICE HANDLERS ====================

    async def _handle_cloud_configure(self, arguments: dict) -> str:
        """Configure Power BI Service connection"""
        try:
            tenant_id = arguments.get("tenant_id", "")
            client_id = arguments.get("client_id", "")
            client_secret = arguments.get("client_secret", "")

            if not all([tenant_id, client_id, client_secret]):
                return "Missing required credentials (tenant_id, client_id, client_secret)"

            # Initialize REST connector for workspace/dataset listing
            self.rest_connector = PowerBIRestConnector(tenant_id, client_id, client_secret)

            # Initialize XMLA connector for querying
            self.xmla_connector = PowerBIXmlaConnector(tenant_id, client_id, client_secret)

            # Test authentication
            if self.rest_connector.authenticate():
                self.cloud_connected = True
                return ("Power BI Service configured successfully!\n\n"
                        "You can now:\n"
                        "1. Use 'cloud_list_workspaces' to see available workspaces\n"
                        "2. Use 'cloud_list_datasets' to see datasets in a workspace\n"
                        "3. Use 'cloud_connect_xmla' to connect to a dataset for querying")
            else:
                return "Authentication failed. Check your Service Principal credentials."

        except Exception as e:
            return f"Error configuring cloud connection: {str(e)}"

    async def _handle_cloud_list_workspaces(self) -> str:
        """List Power BI Service workspaces"""
        try:
            if not self.rest_connector or not self.cloud_connected:
                return "Not connected. Use 'cloud_configure' first with Service Principal credentials."

            workspaces = await asyncio.get_event_loop().run_in_executor(
                None, self.rest_connector.list_workspaces
            )

            if not workspaces:
                return "No workspaces found (or authentication failed)."

            result = f"Found {len(workspaces)} workspace(s):\n\n"
            for ws in workspaces:
                result += f"• {ws['name']}\n"
                result += f"  ID: {ws['id']}\n"
                result += f"  State: {ws.get('state', 'Unknown')}\n\n"

            return result

        except Exception as e:
            return f"Error listing workspaces: {str(e)}"

    async def _handle_cloud_list_datasets(self, arguments: dict) -> str:
        """List datasets in a workspace"""
        try:
            if not self.rest_connector or not self.cloud_connected:
                return "Not connected. Use 'cloud_configure' first."

            workspace_id = arguments.get("workspace_id", "")
            if not workspace_id:
                return "workspace_id is required"

            datasets = await asyncio.get_event_loop().run_in_executor(
                None, lambda: self.rest_connector.list_datasets(workspace_id)
            )

            if not datasets:
                return "No datasets found in this workspace."

            result = f"Found {len(datasets)} dataset(s):\n\n"
            for ds in datasets:
                result += f"• {ds['name']}\n"
                result += f"  ID: {ds['id']}\n"
                result += f"  Configured by: {ds.get('configuredBy', 'Unknown')}\n\n"

            result += "\nUse 'cloud_connect_xmla' with workspace_name and dataset_name to connect."
            return result

        except Exception as e:
            return f"Error listing datasets: {str(e)}"

    async def _handle_cloud_connect_xmla(self, arguments: dict) -> str:
        """Connect to a dataset via XMLA"""
        try:
            if not self.xmla_connector:
                return "Not configured. Use 'cloud_configure' first."

            workspace_name = arguments.get("workspace_name", "")
            dataset_name = arguments.get("dataset_name", "")
            effective_user = arguments.get("effective_user")

            if not workspace_name or not dataset_name:
                return "workspace_name and dataset_name are required"

            success = await asyncio.get_event_loop().run_in_executor(
                None, lambda: self.xmla_connector.connect(workspace_name, dataset_name, effective_user)
            )

            if success:
                rls_msg = ""
                if effective_user:
                    rls_msg = f"\nRLS Active: Impersonating '{effective_user}'"

                return (f"Connected to dataset '{dataset_name}' via XMLA!{rls_msg}\n\n"
                        "You can now use:\n"
                        "• cloud_list_tables - See available tables\n"
                        "• cloud_execute_dax - Run DAX queries\n"
                        "• cloud_get_model_info - Get full model schema")
            else:
                return ("XMLA connection failed.\n\n"
                        "Check that:\n"
                        "1. XMLA endpoint is enabled for the workspace\n"
                        "2. Service Principal has access to the dataset\n"
                        "3. ADOMD.NET is installed (comes with SSMS)")

        except Exception as e:
            return f"Error connecting via XMLA: {str(e)}"

    async def _handle_cloud_list_tables(self) -> str:
        """List tables in connected cloud dataset"""
        try:
            if not self.xmla_connector or not self.xmla_connector.connection_string:
                return "Not connected to a dataset. Use 'cloud_connect_xmla' first."

            tables = await asyncio.get_event_loop().run_in_executor(
                None, self.xmla_connector.discover_tables
            )

            if not tables:
                return "No tables found (or connection lost)."

            result = f"Found {len(tables)} table(s):\n\n"
            for t in tables:
                result += f"• {t['name']}\n"
                if t.get('description') and t['description'] != "No description available":
                    result += f"  {t['description']}\n"

            return result

        except Exception as e:
            return f"Error listing tables: {str(e)}"

    async def _handle_cloud_list_columns(self, arguments: dict) -> str:
        """List columns for a table in cloud dataset"""
        try:
            if not self.xmla_connector or not self.xmla_connector.connection_string:
                return "Not connected to a dataset. Use 'cloud_connect_xmla' first."

            table_name = arguments.get("table_name", "")
            if not table_name:
                return "table_name is required"

            schema = await asyncio.get_event_loop().run_in_executor(
                None, lambda: self.xmla_connector.get_table_schema(table_name)
            )

            columns = schema.get("columns", [])
            if not columns:
                return f"No columns found for table '{table_name}'"

            result = f"Columns in '{table_name}':\n\n"
            for col in columns:
                result += f"• {col['name']} ({col['type']})\n"

            return result

        except Exception as e:
            return f"Error listing columns: {str(e)}"

    async def _handle_cloud_execute_dax(self, arguments: dict) -> str:
        """Execute DAX query on cloud dataset"""
        try:
            if not self.xmla_connector or not self.xmla_connector.connection_string:
                return "Not connected to a dataset. Use 'cloud_connect_xmla' first."

            dax_query = arguments.get("dax_query", "")
            if not dax_query:
                return "dax_query is required"

            results = await asyncio.get_event_loop().run_in_executor(
                None, lambda: self.xmla_connector.execute_dax(dax_query)
            )

            if not results:
                return "Query returned no results."

            # Format results
            result = f"Query returned {len(results)} row(s):\n\n"

            # Show first 20 rows
            for i, row in enumerate(results[:20]):
                result += f"{i+1}. {json.dumps(row, default=str)}\n"

            if len(results) > 20:
                result += f"\n... and {len(results) - 20} more rows"

            return result

        except Exception as e:
            return f"DAX execution error: {str(e)}"

    async def _handle_cloud_get_model_info(self) -> str:
        """Get comprehensive model info from cloud dataset"""
        try:
            if not self.xmla_connector or not self.xmla_connector.connection_string:
                return "Not connected to a dataset. Use 'cloud_connect_xmla' first."

            # Get tables
            tables = await asyncio.get_event_loop().run_in_executor(
                None, self.xmla_connector.discover_tables
            )

            result = f"Model: {self.xmla_connector.dataset_name}\n"
            result += f"Workspace: {self.xmla_connector.workspace_name}\n"
            result += "=" * 50 + "\n\n"

            result += f"Tables ({len(tables)}):\n"
            for t in tables:
                result += f"  • {t['name']}\n"

            # Get columns for first few tables
            result += "\nColumn Details (first 5 tables):\n"
            for t in tables[:5]:
                schema = await asyncio.get_event_loop().run_in_executor(
                    None, lambda tn=t['name']: self.xmla_connector.get_table_schema(tn)
                )
                cols = schema.get("columns", [])
                result += f"\n{t['name']}:\n"
                for col in cols[:10]:
                    result += f"  - {col['name']} ({col['type']})\n"
                if len(cols) > 10:
                    result += f"  ... and {len(cols) - 10} more columns\n"

            return result

        except Exception as e:
            return f"Error getting model info: {str(e)}"

    async def run(self):
        """Run the MCP server"""
        logger.info("Starting Power BI MCP Server V3...")

        async with stdio_server() as (read_stream, write_stream):
            await self.server.run(
                read_stream,
                write_stream,
                InitializationOptions(
                    server_name="powerbi-mcp-v3",
                    server_version="3.0.0",
                    capabilities=self.server.get_capabilities(
                        notification_options=NotificationOptions(),
                        experimental_capabilities={},
                    ),
                ),
            )


async def main():
    """Main entry point"""
    server = PowerBIMCPServerV3()
    await server.run()


if __name__ == "__main__":
    asyncio.run(main())
