"""Definición de herramientas MCP para Power BI."""
import json
from typing import Any, Dict

from .powerbi_client import PowerBIClient


_client = None


def get_client() -> PowerBIClient:
    """Obtiene o crea una instancia singleton del cliente de Power BI."""
    global _client
    if _client is None:
        _client = PowerBIClient()
    return _client


TOOLS = [
    {
        "name": "test_connection",
        "description": "Prueba la conexión al modelo de Power BI actual.",
        "inputSchema": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "refresh_connection",
        "description": "Refresca la conexión local y re-detecta el dashboard abierto.",
        "inputSchema": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "list_local_instances",
        "description": "Lista instancias locales detectadas de Power BI Desktop (puertos XMLA).",
        "inputSchema": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "use_local_instance",
        "description": "Selecciona manualmente una instancia local por puerto XMLA.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "port": {
                    "type": "string",
                    "description": "Puerto XMLA local, por ejemplo 50943",
                }
            },
            "required": ["port"],
        },
    },
    {
        "name": "get_model_info",
        "description": "Obtiene resumen del modelo: tablas, medidas y relaciones.",
        "inputSchema": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "get_tables",
        "description": "Lista tablas del modelo.",
        "inputSchema": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "get_columns",
        "description": "Lista columnas; `table_name` es opcional.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "table_name": {
                    "type": "string",
                    "description": "Nombre de tabla para filtrar columnas",
                }
            },
            "required": [],
        },
    },
    {
        "name": "get_measures",
        "description": "Lista medidas; `table_name` es opcional.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "table_name": {
                    "type": "string",
                    "description": "Nombre de tabla para filtrar medidas",
                }
            },
            "required": [],
        },
    },
    {
        "name": "get_relationships",
        "description": "Lista relaciones del modelo.",
        "inputSchema": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "execute_dax",
        "description": "Ejecuta consulta DAX y devuelve filas.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Consulta DAX, por ejemplo EVALUATE TOPN(10, Ventas)",
                }
            },
            "required": ["query"],
        },
    },
    {
        "name": "validate_dax",
        "description": "Valida una expresion DAX sin ejecutarla.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "expression": {
                    "type": "string",
                    "description": "Expresion DAX a validar",
                }
            },
            "required": ["expression"],
        },
    },
    {
        "name": "generate_tmsl_create_measure",
        "description": "Genera el payload TMSL JSON para crear una medida (no ejecuta).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "table": {"type": "string"},
                "measure_name": {"type": "string"},
                "dax_expression": {"type": "string"}
            },
            "required": ["table", "measure_name", "dax_expression"]
        }
    },
    {
        "name": "create_measure",
        "description": "Crea (o actualiza) una medida DAX directamente en el modelo de Power BI Desktop via TOM. Si la medida ya existe, actualiza su expresión.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "table": {"type": "string", "description": "Nombre de la tabla donde crear la medida"},
                "measure_name": {"type": "string", "description": "Nombre de la medida"},
                "dax_expression": {"type": "string", "description": "Expresión DAX de la medida"}
            },
            "required": ["table", "measure_name", "dax_expression"]
        }
    },
    {
        "name": "create_relationship",
        "description": "Crea una relación entre dos tablas directamente en el modelo de Power BI Desktop via TOM.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Nombre único de la relación"},
                "from_table": {"type": "string"},
                "from_column": {"type": "string"},
                "to_table": {"type": "string"},
                "to_column": {"type": "string"},
                "cross_filtering": {"type": "string", "description": "BothDirections (defecto) o OneDirection"}
            },
            "required": ["name", "from_table", "from_column", "to_table", "to_column"]
        }
    },
]


async def handle_tool_call(name: str, arguments: Dict[str, Any]) -> str:
    """Maneja llamadas a herramientas MCP y retorna JSON string."""
    client = get_client()

    try:
        if name == "test_connection":
            result = {
                "success": client.test_connection(),
                "connection_string": client.connection_string,
                "local_port": client.local_port,
                "local_workspace": client.local_workspace,
            }
        elif name == "refresh_connection":
            result = client.refresh_connection()
        elif name == "list_local_instances":
            result = {"instances": client.discover_local_instances()}
        elif name == "use_local_instance":
            port = arguments.get("port")
            if not port:
                return json.dumps({"error": "Missing 'port' argument"})
            result = client.use_local_instance(str(port))
        elif name == "get_model_info":
            result = client.get_model_info()
        elif name == "get_tables":
            result = {"tables": client.get_tables()}
        elif name == "get_columns":
            result = {"columns": client.get_columns(arguments.get("table_name"))}
        elif name == "get_measures":
            result = {"measures": client.get_measures(arguments.get("table_name"))}
        elif name == "get_relationships":
            result = {"relationships": client.get_relationships()}
        elif name == "generate_tmsl_create_measure":
            table = arguments.get("table")
            measure_name = arguments.get("measure_name")
            dax = arguments.get("dax_expression")
            if not table or not measure_name or not dax:
                return json.dumps({"error": "Missing required args: table, measure_name, dax_expression"})
            result = {"tmsl": client.generate_tmsl_create_measure(table, measure_name, dax)}
        elif name == "create_measure":
            table = arguments.get("table")
            measure_name = arguments.get("measure_name")
            dax = arguments.get("dax_expression")
            if not table or not measure_name or not dax:
                return json.dumps({"error": "Missing required args: table, measure_name, dax_expression"})
            result = client.create_measure(table, measure_name, dax)
        elif name == "create_relationship":
            name_arg = arguments.get("name")
            from_table = arguments.get("from_table")
            from_column = arguments.get("from_column")
            to_table = arguments.get("to_table")
            to_column = arguments.get("to_column")
            cross_filtering = arguments.get("cross_filtering", "BothDirections")
            if not (name_arg and from_table and from_column and to_table and to_column):
                return json.dumps({"error": "Missing required args: name, from_table, from_column, to_table, to_column"})
            result = client.create_relationship(name_arg, from_table, from_column, to_table, to_column, cross_filtering=cross_filtering)
        elif name == "execute_dax":
            query = arguments.get("query")
            if not query:
                return json.dumps({"error": "Missing 'query' argument"})
            result = {"rows": client.execute_dax(query)}
        elif name == "validate_dax":
            expression = arguments.get("expression")
            if not expression:
                return json.dumps({"error": "Missing 'expression' argument"})
            try:
                from .dax_validator import DaxValidator
            except Exception as ie:
                return json.dumps({"error": "DaxValidator not available", "detail": str(ie)})
            result = DaxValidator.validate(expression)
        else:
            return json.dumps({"error": f"Tool desconocida: {name}"})

        return json.dumps(result, indent=2, ensure_ascii=False, default=str)
    except Exception as e:
        return json.dumps({"error": str(e)})