import os
import glob
from fastmcp import FastMCP

# 1. Instanciar el servidor
mcp = FastMCP("Servidor de Archivos Markdown")

# --- Carga de archivos desde el disco ---
def load_markdown_files():
    """
    Busca y carga todos los archivos .md en el directorio actual en un diccionario.
    """
    files_dict = {}
    for filepath in glob.glob("*.md"):
        filename = os.path.basename(filepath)
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                files_dict[filename] = f.read()
        except Exception as e:
            print(f"Error al leer el archivo {filename}: {e}")
            files_dict[filename] = f"Error al leer el archivo: {e}"
    return files_dict

# Cargar los archivos al iniciar el script
loaded_files = load_markdown_files()
# -----------------------------------------

# Lista de archivos a excluir
EXCLUDED_FILES = ["README.md"]

# Recurso para listar los archivos disponibles
@mcp.resource("markdown://files")
def list_files():
    """Devuelve una lista de los archivos .md disponibles."""
    available_files = [f for f in loaded_files.keys() if f not in EXCLUDED_FILES]
    return available_files

# Recurso dinámico para obtener el contenido de un archivo
@mcp.resource("markdown://file/{filename}")
def get_file(filename: str):
    """Devuelve el contenido de un archivo .md específico."""
    if filename in EXCLUDED_FILES:
        return f"Acceso denegado al archivo: {filename}"
    return loaded_files.get(filename, f"Error: Archivo no encontrado: {filename}")

if __name__ == "__main__":
    # Ejecutar el servidor. Por defecto usa stdio, que es lo que el cliente esperará.
    print("Servidor MCP iniciado. Esperando comandos a través de stdio...")
    mcp.run()
