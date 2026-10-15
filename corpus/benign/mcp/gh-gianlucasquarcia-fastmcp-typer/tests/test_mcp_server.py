import asyncio
import json
from types import SimpleNamespace

import pytest
from fastmcp import Client
from typer.testing import CliRunner

import mcp_server
import mcp_server_cli
import mcp_server_resources
import mcp_server_tools

runner = CliRunner()


def test_sort_numbers_returns_ascending_order():
    result = mcp_server_tools.sort_numbers([5, 2, 9, 1, 5, 6])

    assert result == [1, 2, 5, 5, 6, 9]


def test_long_running_greet_reports_progress_and_greets(monkeypatch):
    monkeypatch.setattr(
        mcp_server_tools,
        "settings",
        SimpleNamespace(LONG_RUNNING_TASK_FAKE_DELAY=0),
    )
    progress = []

    async def progress_handler(value, total, _message):
        progress.append((value, total))

    async def run():
        async with Client(
            mcp_server.mcp,
            progress_handler=progress_handler,
        ) as client:
            return await client.call_tool("long_running_greet", {"name": "Ada"})

    result = asyncio.run(run())

    assert result.data == "Hello, Ada!"
    assert progress == [(0, 1), (1, 1)]


def test_long_running_greet_hides_ctx_from_schema():
    tools = asyncio.run(mcp_server.mcp.list_tools())
    tool = next(t for t in tools if t.name == "long_running_greet")

    assert list(tool.parameters["properties"]) == ["name"]


def test_current_gps_position_returns_fixed_coordinates():
    result = mcp_server_resources.get_current_gps_position()

    assert result == {"latitude": 37.7749, "longitude": -122.4194}


def test_mcp_lists_expected_tools():
    tools = asyncio.run(mcp_server.mcp.list_tools())
    tools_by_name = {tool.name: tool for tool in tools}

    assert {"sort_numbers", "open_meteo_current_forecast"}.issubset(tools_by_name)
    assert tools_by_name["sort_numbers"].title == "Sort Numbers"
    assert tools_by_name["sort_numbers"].tags == {"demo", "sorting", "numbers"}
    sort_annotations = tools_by_name["sort_numbers"].annotations
    assert sort_annotations is not None
    assert sort_annotations.read_only_hint is True
    assert sort_annotations.destructive_hint is False
    assert tools_by_name["open_meteo_current_forecast"].tags == {
        "external-api",
        "forecast",
        "weather",
    }
    forecast_annotations = tools_by_name["open_meteo_current_forecast"].annotations
    assert forecast_annotations is not None
    assert forecast_annotations.open_world_hint is True


def test_open_meteo_current_forecast_returns_response_json(monkeypatch):
    response_data = {"current": {"temperature_2m": 21.5}}
    requests = []

    class FakeResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return response_data

    class FakeSession:
        def mount(self, _prefix, _adapter):
            return None

        def get(self, url, **kwargs):
            requests.append((url, kwargs))
            return FakeResponse()

    monkeypatch.setattr(mcp_server_tools.requests, "Session", FakeSession)

    assert mcp_server_tools.open_meteo_current_forecast(45.0, 9.0) == response_data
    assert "latitude=45.0&longitude=9.0" in requests[0][0]
    assert requests[0][1] == {
        "verify": mcp_server_tools.settings.HTTP_REQUEST_TLS_VERIFY,
        "timeout": mcp_server_tools.settings.HTTP_REQUEST_TIMEOUT,
    }


@pytest.mark.parametrize(
    ("latitude", "longitude"),
    [(-90.1, 0), (90.1, 0), (0, -180.1), (0, 180.1)],
)
def test_open_meteo_current_forecast_rejects_invalid_coordinates(latitude, longitude):
    with pytest.raises(ValueError, match="Latitude must be between"):
        mcp_server_tools.open_meteo_current_forecast(latitude, longitude)


def test_resources_return_expected_content():
    assert mcp_server_resources.get_greeting() == "Hello from FastMCP Resources!"
    assert json.loads(mcp_server_resources.get_config()) == {
        "theme": "dark",
        "version": "1.2.0",
        "features": ["tools", "resources"],
    }
    assert mcp_server_resources.get_current_time().startswith(
        "RESOURCE: The current UTC time is "
    )


def test_run_command_uses_stdio_by_default(monkeypatch):
    calls = {}

    def fake_run(*args, **kwargs):
        calls["args"] = args
        calls["kwargs"] = kwargs

    monkeypatch.setattr(mcp_server.mcp, "run", fake_run)

    result = runner.invoke(mcp_server.mcp_typer, ["run"])

    assert result.exit_code == 0
    assert calls == {"args": (), "kwargs": {}}


def test_run_command_uses_http_transport_when_requested(monkeypatch):
    calls = {}

    def fake_run(*args, **kwargs):
        calls["args"] = args
        calls["kwargs"] = kwargs

    monkeypatch.setattr(mcp_server.mcp, "run", fake_run)

    result = runner.invoke(
        mcp_server.mcp_typer, ["run", "--transport", "http", "--port", "9001"]
    )

    assert result.exit_code == 0
    assert calls == {
        "args": (),
        "kwargs": {"transport": "streamable-http", "port": 9001},
    }


def test_cli_list_tools_prints_tool_metadata(monkeypatch, capsys):
    class FakeTool:
        def __init__(self):
            self.name = "example"
            self.title = "Example"
            self.description = "Example tool"
            self.tags = {"example", "test"}
            self.annotations = {"readOnlyHint": True}
            self.parameters = {"type": "object"}
            self.output_schema = {"type": "string"}

    class FakeMcp:
        async def list_tools(self):
            return [FakeTool()]

    monkeypatch.setattr(mcp_server, "mcp", FakeMcp())

    asyncio.run(mcp_server_cli.list_mcp_tools())

    output = capsys.readouterr().out
    assert "Tool: example" in output
    assert "Title: Example" in output
    assert "Description: Example tool" in output
    assert "Tags: example, test" in output
    assert "Annotations: {'readOnlyHint': True}" in output
    assert "Parameters:" in output
    assert "Output Schema:" in output


def test_cli_list_tools_command(monkeypatch):
    calls = []

    def fake_run(coroutine):
        calls.append(coroutine)
        coroutine.close()

    monkeypatch.setattr(mcp_server_cli.asyncio, "run", fake_run)

    result = runner.invoke(mcp_server_cli.mcp_typer, ["list-tools"])

    assert result.exit_code == 0
    assert len(calls) == 1
