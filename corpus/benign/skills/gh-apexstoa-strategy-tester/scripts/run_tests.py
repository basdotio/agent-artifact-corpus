#!/usr/bin/env python3
"""Run every tests/test_*.py in this one process: one line per file, a total, exit 1 on any failure."""
from __future__ import annotations

import argparse, glob, importlib.util, os, sys, time, traceback

sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))


def main():
    argparse.ArgumentParser(description=__doc__).parse_args()  # --help prints the line above; there are no options
    for p in (HERE, os.path.join(HERE, "tests")):
        if p not in sys.path:
            sys.path.insert(0, p)
    failed, files, t_all = 0, sorted(glob.glob(os.path.join(HERE, "tests", "test_*.py"))), time.time()
    for path in files:
        name, t0 = os.path.basename(path), time.time()
        try:
            spec = importlib.util.spec_from_file_location("_t_" + name[:-3], path)
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            mod.main()
            print(f"PASS {name} ({time.time() - t0:.1f} s)", flush=True)
        except (Exception, SystemExit) as e:  # an assertion, an error, or an unexpected sys.exit in a test
            failed += 1
            where = traceback.extract_tb(e.__traceback__)[-1]
            text = (str(e) or type(e).__name__).splitlines()[0]
            print(f"FAIL {name}: {type(e).__name__}: {text} (line {where.lineno}: {where.line})", flush=True)
    print(f"{len(files) - failed} of {len(files)} test files passed in {time.time() - t_all:.1f} s")
    sys.exit(1 if failed or not files else 0)


if __name__ == "__main__":
    main()
