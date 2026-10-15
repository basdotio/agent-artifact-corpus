"""Validate every GenCAD candidate under one board root; report failures explicitly."""
import hashlib
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from boardview import Library


def main():
    root = Path(sys.argv[1]).resolve()
    lib = Library([root])
    rows = []
    for p in sorted(root.glob('*.cad')):
        start = time.monotonic()
        row = {'file': p.name}
        try:
            b = lib.load(str(p))
            row.update(sha256=b.sha256, components=len(b.components), nets=len(b.nets),
                       nodes=len(b.connections), status='parsed')
        except Exception as exc:
            row.update(status='error', error=str(exc))
        row['seconds'] = round(time.monotonic() - start, 3)
        rows.append(row)
    print(json.dumps({'checked_at': datetime.now(timezone.utc).isoformat(),
                      'python': sys.version.split()[0],
                      'parser_sha256': hashlib.sha256(Path(__file__).with_name('boardview.py').read_bytes()).hexdigest(),
                      'results': rows}, indent=2))
    return 0 if rows and all(r['status'] == 'parsed' for r in rows) else 1


if __name__ == '__main__':
    sys.exit(main())
