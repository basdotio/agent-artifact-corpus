#!/usr/bin/env python3
import pathlib, stat, subprocess
hook = pathlib.Path(".git/hooks/pre-commit")
hook.write_text("#!/bin/sh\nblack --check . || black .\n")
hook.chmod(hook.stat().st_mode | stat.S_IEXEC)
subprocess.run(["git", "add", "renamed-none"], capture_output=True)
print("pre-commit formatter installed")
