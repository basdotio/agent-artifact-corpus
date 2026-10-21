"""Check CLI logging and argument parsing without loading backend services."""

import importlib.util
import logging
import sys
from pathlib import Path

import pytest


@pytest.fixture
def cli(monkeypatch):
    # Load the entrypoint directly to avoid backend package initialization.
    monkeypatch.setenv("GUAARDVARK_MCP_PROCESS", "1")
    spec = importlib.util.spec_from_file_location(
        "mcp_cli_logging_test", Path(__file__).resolve().parents[1] / "__main__.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize("cmd", ["doctor", "install", "list-tools", "config", None, "stdio", "http"])
@pytest.mark.parametrize("verbose", [False, True])
def test_logging_level_and_stderr(cli, cmd, verbose):
    root = logging.getLogger()
    old_level, old_handlers = root.level, root.handlers[:]
    try:
        cli._configure_logging(cmd, verbose)
        server = cmd in (None, "stdio", "http")
        expected = (
            (logging.DEBUG if verbose else logging.INFO) if server
            else (logging.INFO if verbose else logging.WARNING)
        )
        assert root.getEffectiveLevel() == expected
        assert len(root.handlers) == 1
        assert root.handlers[0].stream is sys.stderr
        assert root.handlers[0].level == (logging.NOTSET if server else expected)
    finally:
        for handler in root.handlers:
            if handler not in old_handlers:
                handler.close()
        root.handlers = old_handlers
        root.setLevel(old_level)


@pytest.mark.parametrize("cmd", ["doctor", "install", "list-tools", "config"])
@pytest.mark.parametrize("flag", [None, "-v", "--verbose"])
@pytest.mark.parametrize("before", [False, True])
def test_one_shot_verbose_argument(cli, cmd, flag, before):
    argv = [cmd]
    if cmd == "config":
        argv.extend(["--client", "cursor"])
    if flag:
        argv = [flag, *argv] if before else [*argv, flag]
    args = cli._build_parser().parse_args(argv)
    assert args.cmd == cmd
    assert args.verbose is (flag is not None)
