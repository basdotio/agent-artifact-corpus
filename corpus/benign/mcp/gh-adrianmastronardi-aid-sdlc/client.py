import asyncio
import json
from fastmcp import Client

async def main():
    # Para conectarse a un subproceso, se debe usar el formato de configuración
    # estándar de MCP, que incluye un diccionario `mcpServers`.
    server_config = {
        "mcpServers": {
            "default": {
                "command": "python",
                "args": ["main.py"]
            }
        }
    }

    async with Client(server_config) as client:
        print("Cliente conectado al servidor.")

        # 1. Listar los recursos disponibles para confirmar la conexión
        resources = await client.list_resources()
        print(f"\\nRecursos disponibles: {resources}")

        # 2. Invocar el recurso para listar archivos
        print("\\n--- Listando archivos disponibles ---")
        # El resultado es una lista con un objeto TextResourceContents, cuyo texto es un JSON.
        list_result = await client.read_resource("markdown://files")
        json_text = list_result[0].text
        available_files = json.loads(json_text)
        print(f"Archivos: {available_files}")

        # 3. Si hay archivos, leer el primero de la lista
        if available_files:
            filename_to_read = available_files[0]
            print(f"\\n--- Leyendo el contenido de: {filename_to_read} ---")

            # Invocamos el recurso dinámico con el nombre del archivo
            content_result = await client.read_resource(f"markdown://file/{filename_to_read}")
            print(content_result[0].text)

        # 4. Intentar leer un archivo que no existe
        print("\\n--- Intentando leer un archivo que no existe ---")
        not_found_result = await client.read_resource("markdown://file/archivo_inexistente.md")
        print(not_found_result[0].text)

        # 5. Intentar leer el archivo excluido
        print("\\n--- Intentando leer el archivo excluido (README.md) ---")
        excluded_result = await client.read_resource("markdown://file/README.md")
        print(excluded_result[0].text)

if __name__ == "__main__":
    asyncio.run(main())
