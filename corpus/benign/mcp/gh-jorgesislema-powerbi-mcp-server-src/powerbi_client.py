"""Cliente para conectarse a Power BI (local o cloud)."""
import os
import re
from pathlib import Path
from typing import List, Dict, Any, Optional

from dotenv import load_dotenv

# ---------------------------------------------------------------------------
# Pre-load ADOMD.NET DLL so that pyadomd's `clr.AddReference` can find it.
# pyadomd calls `clr.AddReference('Microsoft.AnalysisServices.AdomdClient')`
# which requires the DLL directory to be in sys.path (CLR probing path).
# ---------------------------------------------------------------------------
import sys as _sys

def _setup_adomd_vendor() -> str | None:
    """Localiza vendor/adomd/, lo añade a sys.path y lo precarga via clr."""
    _vendor_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'vendor', 'adomd'))
    if not os.path.isdir(_vendor_dir):
        return None
    # Needed for native DLL resolution (e.g. msasxpress.dll)
    os.add_dll_directory(_vendor_dir)
    # Needed so clr.AddReference can probe this directory
    if _vendor_dir not in _sys.path:
        _sys.path.insert(0, _vendor_dir)
    # Explicitly pre-load with full path to guarantee the right DLL is used
    _dll = os.path.join(_vendor_dir, 'Microsoft.AnalysisServices.AdomdClient.dll')
    if os.path.exists(_dll):
        try:
            import clr as _clr  # type: ignore
            _clr.AddReferenceToFileAndPath(_dll)
        except Exception:
            pass
    return _vendor_dir

_adomd_vendor_dir = _setup_adomd_vendor()

try:
    from pyadomd import Pyadomd
    _pyadomd_import_error = None
except Exception as e:
    Pyadomd = None
    _pyadomd_import_error = str(e) + (f"; vendor/adomd tried: {_adomd_vendor_dir}" if _adomd_vendor_dir else " (vendor/adomd not found)")

load_dotenv()

class PowerBIClient:
    """Cliente para conectarse a modelos de Power BI"""

    def __init__(self):
        self.mode = os.getenv("POWERBI_MODE", "local")
        self.local_port = os.getenv("LOCAL_PORT")
        self.local_database = os.getenv("LOCAL_DATABASE", "")
        self.local_workspace = ""
        # Usar sin Initial Catalog por defecto para consultas $SYSTEM locales
        self.connection_string = self._build_connection_string(with_catalog=False)

    def _get_workspace_root(self) -> Path:
        local_app_data = os.getenv("LOCALAPPDATA")
        if not local_app_data:
            raise Exception("No se encontro la variable LOCALAPPDATA")
        return Path(local_app_data) / "Microsoft" / "Power BI Desktop" / "AnalysisServicesWorkspaces"

    def discover_local_instances(self) -> List[Dict[str, Any]]:
        """Descubre puertos XMLA locales de Power BI Desktop abiertos."""
        root = self._get_workspace_root()
        if not root.exists():
            return []

        instances: List[Dict[str, Any]] = []
        for port_file in root.glob("*/Data/msmdsrv.port.txt"):
            try:
                raw = ""
                for enc in ("utf-8", "utf-16", "latin-1"):
                    try:
                        raw = port_file.read_text(encoding=enc)
                        break
                    except UnicodeDecodeError:
                        continue
                normalized = raw.replace("\x00", "")
                match = re.search(r"(\d+)", normalized)
                port = match.group(1) if match else ""
                if not port:
                    continue
                workspace = port_file.parents[1].name
                instances.append(
                    {
                        "workspace": workspace,
                        "port": port,
                        "port_file": str(port_file),
                        "last_modified": port_file.stat().st_mtime,
                    }
                )
            except OSError:
                continue

        instances.sort(key=lambda item: item["last_modified"], reverse=True)
        return instances

    def _auto_select_local_instance(self) -> Optional[Dict[str, Any]]:
        instances = self.discover_local_instances()
        if not instances:
            return None
        return instances[0]

    def _build_connection_string(self, with_catalog: bool = True) -> str:
        """Construye la cadena de conexión según el modo.

        `with_catalog=False` omite el Initial Catalog, lo que permite consultar
        $SYSTEM.TMSCHEMA_* en Power BI Desktop local sin permisos de base de datos.
        """
        if self.mode == "local":
            if not self.local_port:
                selected = self._auto_select_local_instance()
                if selected:
                    self.local_port = selected["port"]
                    self.local_workspace = selected["workspace"]

            port = self.local_port or "54321"
            if with_catalog:
                database = self.local_database or self.local_workspace or "PowerBIModel"
                return f"Provider=MSOLAP;Data Source=localhost:{port};Initial Catalog={database}"
            else:
                return f"Provider=MSOLAP;Data Source=localhost:{port}"
        else:
            # Modo cloud
            workspace = os.getenv("CLOUD_WORKSPACE_ID")
            dataset = os.getenv("CLOUD_DATASET_ID")
            return f"Provider=MSOLAP;Data Source=powerbi://api.powerbi.com/v1.0/myorg/{workspace};Initial Catalog={dataset}"

    def refresh_connection(self) -> Dict[str, Any]:
        """Refresca la cadena de conexion para volver a detectar el modelo local abierto."""
        if self.mode == "local":
            selected = self._auto_select_local_instance()
            if selected:
                self.local_port = selected["port"]
                self.local_workspace = selected["workspace"]
        self.connection_string = self._build_connection_string(with_catalog=False)
        return {
            "mode": self.mode,
            "connection_string": self.connection_string,
            "local_port": self.local_port,
            "local_workspace": self.local_workspace,
        }

    def use_local_instance(self, port: str) -> Dict[str, Any]:
        """Fija manualmente el puerto local a usar."""
        if not str(port).isdigit():
            raise Exception("El puerto debe ser numerico")
        self.local_port = str(port)
        self.connection_string = self._build_connection_string(with_catalog=False)
        return {
            "mode": self.mode,
            "connection_string": self.connection_string,
            "local_port": self.local_port,
            "local_workspace": self.local_workspace,
        }

    def execute_dax(self, dax_query: str) -> List[Dict[str, Any]]:
        """
        Ejecuta una consulta DAX y retorna los resultados
        """
        if Pyadomd is None:
            raise Exception(
                "No se encontro 'pyadomd'. Instala dependencias con: "
                "python -m pip install -r requirements.txt"
            )
        try:
            with Pyadomd(self.connection_string) as conn:
                with conn.cursor().execute(dax_query) as cursor:
                    # Obtener nombres de columnas
                    columns = [col[0] for col in cursor.description] if cursor.description else []
                    # Convertir filas a diccionarios
                    rows = []
                    for row in cursor.fetchall():
                        row_dict = {}
                        for i, value in enumerate(row):
                            col_name = columns[i] if i < len(columns) else f"col_{i}"
                            row_dict[col_name] = value
                        rows.append(row_dict)
                    return rows
        except Exception as e:
            raise Exception(f"Error ejecutando DAX: {str(e)}")
    
    def get_tables(self) -> List[Dict[str, Any]]:
        """Obtiene lista de tablas del modelo"""
        query = "SELECT * FROM $SYSTEM.TMSCHEMA_TABLES"
        return self.execute_dax(query)
    
    def get_columns(self, table_name: Optional[str] = None) -> List[Dict[str, Any]]:
        """Obtiene columnas de una tabla específica o todas.

        $SYSTEM.TMSCHEMA_COLUMNS no tiene TableName, sino TableID.
        Filtramos obteniendo primero el ID de la tabla.
        """
        all_cols = self.execute_dax("SELECT * FROM $SYSTEM.TMSCHEMA_COLUMNS")
        if not table_name:
            return all_cols
        tables = self.execute_dax("SELECT * FROM $SYSTEM.TMSCHEMA_TABLES")
        tbl_id = next((t["ID"] for t in tables if t.get("Name") == table_name), None)
        if tbl_id is None:
            return []
        filtered = [c for c in all_cols if c.get("TableID") == tbl_id]
        # Enriquecemos con TableName para comodidad
        for c in filtered:
            c["TableName"] = table_name
        return filtered

    def get_measures(self, table_name: Optional[str] = None) -> List[Dict[str, Any]]:
        """Obtiene medidas de una tabla específica o todas.

        $SYSTEM.TMSCHEMA_MEASURES no tiene TableName, sino TableID.
        """
        all_meas = self.execute_dax("SELECT * FROM $SYSTEM.TMSCHEMA_MEASURES")
        if not table_name:
            return all_meas
        tables = self.execute_dax("SELECT * FROM $SYSTEM.TMSCHEMA_TABLES")
        tbl_id = next((t["ID"] for t in tables if t.get("Name") == table_name), None)
        if tbl_id is None:
            return []
        filtered = [m for m in all_meas if m.get("TableID") == tbl_id]
        for m in filtered:
            m["TableName"] = table_name
        return filtered
    
    def get_relationships(self) -> List[Dict[str, Any]]:
        """Obtiene todas las relaciones del modelo"""
        query = "SELECT * FROM $SYSTEM.TMSCHEMA_RELATIONSHIPS"
        return self.execute_dax(query)
    
    def get_model_info(self) -> Dict[str, Any]:
        """Obtiene información general del modelo"""
        tables = self.get_tables()
        measures = self.get_measures()
        relationships = self.get_relationships()

        return {
            "mode": self.mode,
            "connection_string": self.connection_string,
            "local_port": self.local_port,
            "local_workspace": self.local_workspace,
            "table_count": len(tables),
            "measure_count": len(measures),
            "relationship_count": len(relationships),
            "tables": [{"name": t.get("Name"), "id": t.get("ID")} for t in tables],
            "measures": [{"name": m.get("Name"), "table": m.get("TableName")} for m in measures[:10]],  # Top 10
            "relationships": [{"name": r.get("Name")} for r in relationships]
        }

    def test_connection(self) -> bool:
        """Prueba si la conexión funciona usando $SYSTEM (no requiere Initial Catalog)"""
        try:
            rows = self.execute_dax("SELECT * FROM $SYSTEM.TMSCHEMA_TABLES")
            return True
        except Exception:
            return False

    def generate_tmsl_create_measure(self, table: str, measure_name: str, dax_expression: str) -> Dict[str, Any]:
        """Genera un payload TMSL (JSON) correcto para crear una medida.

        Formato TMSL correcto: parentObject identifica la tabla padre,
        y measure va al mismo nivel dentro de 'create'.
        """
        db = self.local_workspace or ""
        return {
            "create": {
                "parentObject": {
                    "database": db,
                    "table": table
                },
                "measure": {
                    "name": measure_name,
                    "expression": dax_expression
                }
            }
        }

    def generate_tmsl_create_relationship(self, name: str, from_table: str, from_column: str, to_table: str, to_column: str, cross_filtering: str = "BothDirections") -> Dict[str, Any]:
        """Genera un payload TMSL correcto para crear una relación entre tablas."""
        db = self.local_workspace or ""
        return {
            "create": {
                "parentObject": {
                    "database": db
                },
                "relationship": {
                    "name": name,
                    "fromTable": from_table,
                    "fromColumn": from_column,
                    "toTable": to_table,
                    "toColumn": to_column,
                    "crossFilteringBehavior": cross_filtering
                }
            }
        }

    # ------------------------------------------------------------------
    # TOM write helpers  (Tabular Object Model — mismo mecanismo que Tabular Editor)
    # ------------------------------------------------------------------

    def _load_tom(self):
        """Carga las DLLs de TOM desde vendor/tom y devuelve el modulo Server de TOM."""
        import os as _os
        import sys as _sys
        tom_dir = _os.path.abspath(
            _os.path.join(_os.path.dirname(__file__), '..', 'vendor', 'tom')
        )
        if not _os.path.isdir(tom_dir):
            raise Exception(
                f"Carpeta de TOM no encontrada: {tom_dir}. "
                "Coloca las DLLs de TOM en vendor/tom/ (ver README)."
            )
        _os.add_dll_directory(tom_dir)
        if tom_dir not in _sys.path:
            _sys.path.insert(0, tom_dir)
        try:
            import clr  # type: ignore
            for asm_name in (
                "Microsoft.AnalysisServices.Core",
                "Microsoft.AnalysisServices.Tabular",
            ):
                try:
                    clr.AddReference(asm_name)
                except Exception:
                    pass
            from Microsoft.AnalysisServices.Tabular import Server as _TomServer  # type: ignore
            return _TomServer
        except Exception as e:
            raise Exception(
                f"No se pudieron cargar las DLLs de TOM: {e}. "
                "Verifica que Microsoft.AnalysisServices.Tabular.dll este en vendor/tom."
            )

    def _tom_connect(self):
        """Devuelve (server, database) conectados via TOM al PBI Desktop local."""
        TomServer = self._load_tom()
        if not self.local_port:
            self.refresh_connection()
        if not self.local_port:
            raise Exception("No se encontro instancia local de Power BI Desktop.")
        conn_str = self._build_connection_string(with_catalog=False)
        srv = TomServer()
        srv.Connect(conn_str)
        if srv.Databases.Count == 0:
            srv.Disconnect()
            raise Exception("El servidor AS local no tiene bases de datos cargadas.")
        db = srv.Databases[0]
        return srv, db

    def apply_tmsl(self, tmsl_payload: Dict[str, Any], catalog: Optional[str] = None) -> Dict[str, Any]:
        """Aplica un payload TMSL al modelo local usando ADOMD.NET ExecuteNonQuery.

        Parámetro `catalog` añadido por compatibilidad:
        - `catalog=None` (comportamiento por defecto, sin Initial Catalog en la cadena)
        - `catalog==''` omite Initial Catalog
        - `catalog=='NAME'` fuerza `Initial Catalog=NAME`

        Fallback para operaciones no cubiertas por los metodos TOM especificos.
        """
        import json as _json

        if not self.local_port:
            self.refresh_connection()
        if not self.local_port:
            raise Exception("No se encontro instancia local de Power BI Desktop.")

        # Construir cadena de conexion respetando el parametro `catalog` si se proporcionó
        if catalog is None:
            conn_str = self._build_connection_string(with_catalog=False)
        else:
            # catalog == '' -> sin Initial Catalog
            if catalog == "":
                conn_str = self._build_connection_string(with_catalog=False)
            else:
                port = self.local_port
                conn_str = f"Provider=MSOLAP;Data Source=localhost:{port};Initial Catalog={catalog}"

        tmsl_json = _json.dumps(tmsl_payload)

        try:
            import clr  # type: ignore
            from Microsoft.AnalysisServices.AdomdClient import (  # type: ignore
                AdomdConnection, AdomdCommand
            )
        except Exception as e:
            raise Exception(
                f"No se pudo cargar Microsoft.AnalysisServices.AdomdClient: {e}."
            )

        conn = AdomdConnection(conn_str)
        try:
            conn.Open()
            cmd = AdomdCommand()
            cmd.Connection = conn
            cmd.CommandText = tmsl_json
            result = cmd.ExecuteNonQuery()
            return {"status": "success", "result": result, "tmsl": tmsl_payload}
        except Exception as e:
            raise Exception(f"Error al aplicar TMSL: {str(e)}")
        finally:
            try:
                conn.Close()
            except Exception:
                pass

    def create_measure(self, table: str, measure_name: str, dax_expression: str, execute: bool = False, catalog: Optional[str] = None) -> Dict[str, Any]:
        """Crea una medida DAX directamente en el modelo de Power BI Desktop via TOM.

        Usa Tabular Object Model (misma API que Tabular Editor) para escribir
        la medida en el AS embebido de Power BI Desktop.
        """
        # Compatibilidad: si se solicita `execute=True`, usar TMSL/ADOMD (comportamiento antiguo esperado por scripts)
        if execute:
            tmsl = self.generate_tmsl_create_measure(table, measure_name, dax_expression)
            return self.apply_tmsl(tmsl, catalog=catalog if catalog is not None else "")

        try:
            from Microsoft.AnalysisServices.Tabular import Measure as _Measure  # type: ignore
        except ImportError:
            self._load_tom()
            from Microsoft.AnalysisServices.Tabular import Measure as _Measure  # type: ignore

        srv, db = self._tom_connect()
        try:
            model = db.Model
            tbl = model.Tables.Find(table)
            if tbl is None:
                all_names = [model.Tables[i].Name for i in range(model.Tables.Count)]
                raise Exception(
                    f"Tabla '{table}' no encontrada. "
                    f"Tablas disponibles: {all_names}"
                )
            existing = tbl.Measures.Find(measure_name)
            if existing is not None:
                # Actualiza la expresion de la medida existente
                existing.Expression = dax_expression
                model.SaveChanges()
                return {
                    "status": "updated",
                    "message": f"Medida '{measure_name}' actualizada (ya existia).",
                    "name": measure_name,
                    "table": table,
                    "expression": dax_expression,
                }
            m = _Measure()
            m.Name = measure_name
            m.Expression = dax_expression
            tbl.Measures.Add(m)
            model.SaveChanges()
            return {
                "status": "success",
                "created": "measure",
                "name": measure_name,
                "table": table,
                "expression": dax_expression,
            }
        finally:
            try:
                srv.Disconnect()
            except Exception:
                pass

    def create_relationship(
        self,
        name: str,
        from_table: str,
        from_column: str,
        to_table: str,
        to_column: str,
        cross_filtering: str = "BothDirections",
    ) -> Dict[str, Any]:
        """Crea una relacion entre tablas directamente en el modelo via TOM."""
        try:
            from Microsoft.AnalysisServices.Tabular import (  # type: ignore
                SingleColumnRelationship as _Rel,
                CrossFilteringBehavior as _CFB,
            )
        except ImportError:
            self._load_tom()
            from Microsoft.AnalysisServices.Tabular import (  # type: ignore
                SingleColumnRelationship as _Rel,
                CrossFilteringBehavior as _CFB,
            )

        srv, db = self._tom_connect()
        try:
            model = db.Model
            rel = _Rel()
            rel.Name = name
            rel.FromTable = from_table
            rel.FromColumn = from_column
            rel.ToTable = to_table
            rel.ToColumn = to_column
            try:
                rel.CrossFilteringBehavior = getattr(_CFB, cross_filtering)
            except Exception:
                pass  # usar default si el valor no es valido
            model.Relationships.Add(rel)
            model.SaveChanges()
            return {
                "status": "success",
                "created": "relationship",
                "name": name,
                "from": f"{from_table}[{from_column}]",
                "to": f"{to_table}[{to_column}]",
            }
        finally:
            try:
                srv.Disconnect()
            except Exception:
                pass