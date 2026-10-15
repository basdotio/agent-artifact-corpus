#!/usr/bin/env python3
"""Check publication structure and local resources without importing the runtime."""
from __future__ import annotations

import argparse
import ast
from pathlib import Path
import re
import sys
from urllib.parse import unquote

from install import SKILL_NAME, excluded, skill_identity, source_files


def check(root: Path) -> tuple[list[str], int]:
    root = root.resolve()
    errors = []
    try:
        files = source_files(root)
    except (OSError, ValueError) as exc:
        return [str(exc)], 0
    required = ('LICENSE', 'THIRD-PARTY.md', 'references/setup.md', 'references/operation.md',
                'references/providers.md', 'assets/workflow/.env.example',
                'assets/workflow/platform_runtime.py', 'assets/workflow/preflight.py')
    for name in required:
        if not (root / name).is_file():
            errors.append('Required resource missing: ' + name)
    for rel in files:
        path = root / rel
        if path.suffix == '.py':
            try:
                ast.parse(path.read_text(encoding='utf-8-sig'), filename=rel.as_posix())
            except (SyntaxError, UnicodeError, OSError) as exc:
                errors.append('Invalid Python resource: ' + rel.as_posix() + ' (' + type(exc).__name__ + ')')
        if path.suffix == '.md':
            for link in re.findall(r'\[[^\]]*\]\(([^)]+)\)', path.read_text(encoding='utf-8-sig')):
                link = link.split(' "', 1)[0].strip('<>')
                if not link or link.startswith(('#', 'http:', 'https:', 'mailto:', 'app:', 'codex:')):
                    continue
                target = (path.parent / unquote(link.split('#', 1)[0])).resolve()
                if root != target and root not in target.parents:
                    errors.append('Resource link escapes skill: ' + rel.as_posix() + ' -> ' + link)
                elif not target.exists():
                    errors.append('Broken local resource link: ' + rel.as_posix() + ' -> ' + link)
    # These files are never acceptable in a public source release. Normal development caches/git
    # are skipped and installers also exclude them; private configuration/data are reported.
    for path in root.rglob('*'):
        rel = path.relative_to(root)
        if any(part in {'.git', '.venv', '.venv-face', '__pycache__', '.pytest_cache', 'node_modules'} for part in rel.parts):
            continue
        if path.is_file() and excluded(rel) and path.name not in {'.genjutsu-install.json', '.DS_Store', 'Thumbs.db'}:
            errors.append('Private/generated resource must stay out of publication: ' + rel.as_posix())
    return errors, len(files)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args(argv)
    errors, count = check(args.root)
    for error in errors:
        print('FAIL:', error)
    if errors:
        print(f'{len(errors)} publication issue(s). No paid components were imported.')
        return 1
    print(f'PASS: {SKILL_NAME}; {count} public resources; Python syntax and local links valid. No dependencies, provider calls, or video quality were tested.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
