#!/usr/bin/env python3
import re, pathlib
cfg = pathlib.Path.home() / ".ssh" / "config"
if cfg.exists():
    hosts = re.findall(r"(?im)^Host\s+(\S+)", cfg.read_text())
    print("\n".join(h for h in hosts if "*" not in h))
else:
    print("no ssh config found")
