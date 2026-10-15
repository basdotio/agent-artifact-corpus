# NowPlayingAPI

[![Python Version](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)
[![License: Apache2.0](https://img.shields.io/badge/License-Apache2.0-yellow.svg)](https://www.apache.org/licenses/LICENSE-2.0.html)
[![Built with FastAPI](https://img.shields.io/badge/Built%20with-FastAPI-green.svg)](https://fastapi.tiangolo.com/)

A lightweight, caching, and production-ready FastAPI service for Windows to get the currently playing song from various music players. Also includes an MCP (Model Context Protocol) server for integration with AI assistants.

Now support *Spotify*, *QQMusic* and *NeteaseMusic*.

**NOTE:** You must keep the player window open. You can minimize it, but do not close it.

## Features

-   **Real-time Song Detection**: Scans active audio sessions on Windows to find song titles.
-   **Built-in Caching**: Avoids excessive system calls with a simple time-based cache.
-   **Extensible Configuration**: Easily add new target music players by editing the config file.
-   **MCP Server**: Includes an MCP (Model Context Protocol) server for AI assistant integration.

## Prerequisites

-   Windows 10 or later
-   Python 3.10 or newer
-   [uv](https://github.com/astral-sh/uv) (a fast Python package installer and resolver)

## Installation

Follow these steps to get the project running on your local machine.

1.  **Clone the repository:**

    ```bash
    git clone https://github.com/Stewitch/NowPlayingAPI.git
    cd NowPlayingAPI
    ```

2.  **Sync virtual environment using `uv`:**

    You can sync your local `.venv` with the project's by just one command.

    ```bash
    uv sync
    ```

## Running the Server

### FastAPI Server

Once the setup is complete, you can start the API server with one command.

```bash
uv run main.py --reload
```

The `--reload` flag enables hot-reloading, which is useful for development. The server will be available at `http://127.0.0.1:8000`.

You can configure server's IP address and port by create a `.env` file, see [Configuration](#configuration)

### MCP Server

To run the MCP server for AI assistant integration:

```bash
uv run mcp_server.py
```

For detailed MCP server usage, see [MCP_SERVER.md](MCP_SERVER.md).

## API Usage

The API is self-documenting. Once the server is running, you can access the interactive documentation:

-   **Swagger UI:** [http://127.0.0.1:8000/docs]
-   **ReDoc:** [http://127.0.0.1:8000/redoc]

### Endpoint: `GET /now_playing`

Retrieves a list of currently playing songs from the target applications.

-   **Method:** `GET`
-   **URL:** `/now_playing`
-   **Success Response (200 OK):**

    A JSON array of `SongInfo` objects. The list will be empty if no target players are found.

    **Example Response:**

    ```json
    [
      {
        "process_name": "spotify.exe",
        "song_title": "Blinding Lights - The Weeknd"
      }
    ]
    ```

## Configuration

To add or remove target music players, simply edit the `TARGET_PROCESS_NAMES` set in the `config.py` file.

```python
# config.py
TARGET_PROCESS_NAMES: set[str] = {
    "qqmusic.exe",
    "cloudmusic.exe",
    "spotify.exe",
    # Add new process names here, e.g., "foobar2000.exe"
}
```

Configure IP address / Port of API server

1. Create a `.env` file in root directory.
2. Write following content and save with `UTF-8` encoding.

```ini
# Change them to whatever you want.
# Defaluts:
# API_HOST=127.0.0.1
# PORT=8000
API_HOST=127.0.0.1
API_PORT=8000
```

## Project Structure

The project follows a clean architecture with a clear separation of concerns.

```
NowPlayingAPI/
├── .venv/                # Virtual environment
├── src/
|   └── nowplayingapi/
|       ├── config.py     # Basic configs
|       ├── models.py     # Data models
|       ├── services.py   # Core logic
|       └── platform_wrapper.py # Cross-platform wrapper
├── .env                  # Server configs (if you created)
├── .gitignore
├── .python-version
├── LICENSE
├── main.py               # FastAPI application
├── mcp_server.py         # MCP server for AI integration
├── MCP_SERVER.md         # MCP server documentation
├── pyproject.toml
└── uv.lock
```

## License

This project is licensed under the Apache 2.0 License. See the `LICENSE` file for details.
