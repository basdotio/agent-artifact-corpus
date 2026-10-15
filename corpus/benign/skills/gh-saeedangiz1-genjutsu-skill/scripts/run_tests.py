#!/usr/bin/env python3
"""Run local regression suites without allowing outbound network connections."""
from pathlib import Path
import argparse
import ipaddress
import json
import socket
import sys
import tempfile
import unittest


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dependencies", type=Path, help="Optional isolated dependency directory.")
    parser.add_argument("--scratch", type=Path, help="Writable directory for temporary test fixtures.")
    parser.add_argument("--report", type=Path, help="Save machine-readable observed results.")
    args = parser.parse_args(argv)
    root = Path(__file__).resolve().parents[1]
    runtime = root / "assets" / "workflow"
    scratch = (args.scratch or root / ".test-artifacts").resolve()
    scratch.mkdir(parents=True, exist_ok=True)
    tempfile.tempdir = str(scratch)
    sys.dont_write_bytecode = True
    sys.path[0:0] = [str(runtime), str(runtime / "tests"), str(root / "scripts")]
    if args.dependencies:
        sys.path.insert(0, str(args.dependencies.resolve()))
    original_connect = socket.socket.connect
    original_connect_ex = socket.socket.connect_ex

    def allowed(address):
        try:
            return isinstance(address, tuple) and ipaddress.ip_address(address[0]).is_loopback
        except ValueError:
            return False

    def connect(self, address):
        if not allowed(address):
            raise RuntimeError("Outbound network is disabled for offline validation.")
        return original_connect(self, address)

    def connect_ex(self, address):
        if not allowed(address):
            raise RuntimeError("Outbound network is disabled for offline validation.")
        return original_connect_ex(self, address)

    socket.socket.connect = connect
    socket.socket.connect_ex = connect_ex
    try:
        suite = unittest.TestSuite()
        for directory in (runtime / "tests", root / "tests"):
            if directory.is_dir():
                suite.addTests(unittest.TestLoader().discover(str(directory)))
        result = unittest.TextTestRunner(verbosity=2).run(suite)
        summary = {"tests_run": result.testsRun, "passed": result.wasSuccessful(),
                   "failures": len(result.failures), "errors": len(result.errors),
                   "skipped": len(result.skipped), "outbound_network_disabled": True,
                   "scope": "Offline synthetic/mocked tests; no paid provider acceptance or full visual review."}
        if args.report:
            args.report.parent.mkdir(parents=True, exist_ok=True)
            args.report.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(summary))
        return not result.wasSuccessful()
    finally:
        socket.socket.connect = original_connect
        socket.socket.connect_ex = original_connect_ex


if __name__ == "__main__":
    sys.exit(main())
