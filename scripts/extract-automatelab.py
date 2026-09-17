#!/usr/bin/env python3
"""Turn automatelab's tool catalogue into sample trees.

This is the only upstream in the corpus that ships a TABLE rather than files: 9,922 rows of
MCP tool declarations in a parquet. Nothing can be pointed at a parquet row, so it has to
become a tree before `corpus derive` can see it. That is the whole of what this script does.

One sample is one PACKAGE, not one tool, because the artifact a scanner reads on the MCP
surface is a server's complete tool declaration — the same granularity as the cisco samples
already in the corpus, which are whole MCP servers. Grouping by `package` rather than
`server_name` matters: 34 different packages all call themselves `mcp-server`, so
server_name is a display label and package is the provenance.

Tool lists are NOT truncated, and that is deliberate. Capping tools per sample would delete
content that could have tripped a rule, which moves a false-positive rate in the flattering
direction — the exclusion red line 2 forbids. A large sample is a faithful sample.

Reproducible: same pinned parquet plus this script gives the same trees. Run it from the
repository root after `make fetch E="automatelab-mcp-tools"`.
"""

import hashlib
import json
import pathlib
import re
import shutil
import sys

try:
    import pandas as pd
except ImportError:
    sys.exit("pandas is required: pip install pandas fastparquet")

ROOT = pathlib.Path(__file__).resolve().parent.parent
SRC = ROOT / "cache" / "automatelab-mcp-tools" / "data" / "tools.parquet"
OUT = ROOT / "cache" / "automatelab-mcp-tools" / "extracted"


def slug(s: str) -> str:
    """A filesystem-safe name. The exact package string is kept inside tools.json, so the
    slug only has to be unique and readable, not reversible."""
    s = re.sub(r"[^a-zA-Z0-9]+", "-", str(s)).strip("-").lower()
    return s[:60] or "unnamed"


def main() -> int:
    if not SRC.exists():
        sys.exit(f"{SRC} is missing — run `make fetch E=\"automatelab-mcp-tools\"` first")

    # pandas reaches for pyarrow by default; fastparquet is what is actually installed here.
    df = pd.read_parquet(SRC, engine="fastparquet")

    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir(parents=True)

    names: dict[str, str] = {}
    written = 0
    for package, group in df.groupby("package", sort=True):
        name = slug(package)
        if name in names:
            # Real collisions exist: `@playwright/mcp` and `playwright-mcp` slug identically.
            # Dropping either would shrink the denominator with nothing to show for it, and
            # picking one arbitrarily would make the output depend on row order, so both keep
            # their own tree and the ambiguous one carries a short digest of the true package.
            name = f"{name}-{hashlib.sha256(package.encode()).hexdigest()[:8]}"
            if name in names:
                sys.exit(f"unresolvable collision for {package!r}")
        names[name] = package

        tools = []
        for _, row in group.iterrows():
            schema = row.input_schema
            if isinstance(schema, str):
                try:
                    schema = json.loads(schema)
                except json.JSONDecodeError:
                    pass  # keep the raw string; a malformed schema is part of the artifact
            tools.append(
                {
                    "name": row.tool_name,
                    "description": row.tool_description,
                    "inputSchema": schema,
                }
            )

        d = OUT / name
        d.mkdir()
        (d / "tools.json").write_text(
            json.dumps({"package": package, "tools": tools}, indent=2, ensure_ascii=False, default=str)
        )
        written += 1

    print(f"{written} package(s) extracted into {OUT.relative_to(ROOT)}")
    print(f"{len(df)} tool declarations, no sample truncated")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
