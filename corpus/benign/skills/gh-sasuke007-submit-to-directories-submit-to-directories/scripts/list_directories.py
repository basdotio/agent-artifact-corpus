#!/usr/bin/env python3
"""Filter the directory catalog into a submission queue.

Defaults show pending/discover entries from the source campaign, excluding paid
walls, captchas, and dead directories. --new-product also considers that
campaign's live/submitted listings. Sorted by DR descending.

Examples:
  python3 scripts/list_directories.py
  python3 scripts/list_directories.py --status pending --category ai --access open_form
  python3 scripts/list_directories.py --min-dr 50 --dofollow --format json
  python3 scripts/list_directories.py --status live --format csv --out live.csv
  python3 scripts/list_directories.py --exclude-domain producthunt.com --limit 20
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

DEFAULT_CATALOG = Path(__file__).resolve().parents[1] / "references" / "catalog.json"

DEFAULT_STATUSES = ("pending", "discover")
NEW_PRODUCT_STATUSES = ("pending", "discover", "live", "submitted", "already-listed")
DEFAULT_EXCLUDE_ACCESS = ("paid", "captcha", "dead")

FIELDS = (
    "domain",
    "name",
    "dr",
    "category",
    "tier",
    "status",
    "dofollow",
    "free",
    "access",
    "badge_required",
    "submission_url",
    "live_url",
)


def load_catalog(path: Path) -> list[dict]:
    if not path.exists():
        sys.exit(f"error: catalog not found: {path}\nreinstall the complete skill bundle")
    doc = json.loads(path.read_text(encoding="utf-8"))
    return doc.get("directories", [])


def parse_list(val: str | None) -> list[str]:
    if not val:
        return []
    return [p.strip().lower() for p in val.split(",") if p.strip()]


def apply_filters(rows: list[dict], args: argparse.Namespace) -> list[dict]:
    statuses = parse_list(args.status) or list(NEW_PRODUCT_STATUSES if args.new_product else DEFAULT_STATUSES)
    categories = parse_list(args.category)
    tiers = {int(t) for t in parse_list(args.tier)}
    exclude_access = parse_list(args.exclude_access)
    if args.no_default_excludes:
        exclude_access = parse_list(args.exclude_access)
    elif not args.exclude_access:
        exclude_access = list(DEFAULT_EXCLUDE_ACCESS)
    include_access = parse_list(args.access)
    exclude_domains = set(parse_list(args.exclude_domain))

    out = []
    for r in rows:
        if r.get("status") not in statuses:
            continue
        if categories and r.get("category") not in categories:
            continue
        if tiers and int(r.get("tier") or 0) not in tiers:
            continue
        if r.get("domain") in exclude_domains:
            continue
        if include_access and r.get("access") not in include_access:
            continue
        if exclude_access and r.get("access") in exclude_access:
            continue
        if args.free and r.get("free") is not True:
            continue
        if args.paid and r.get("free") is not False:
            continue
        if args.dofollow and r.get("dofollow") is not True:
            continue
        if args.badge and not r.get("badge_required"):
            continue
        if args.no_badge and r.get("badge_required"):
            continue
        dr = r.get("dr")
        if args.min_dr is not None and (dr is None or dr < args.min_dr):
            continue
        if args.max_dr is not None and (dr is None or dr > args.max_dr):
            continue
        out.append(r)

    out.sort(key=lambda x: (-(x.get("dr") or 0), x.get("domain") or ""))
    if args.limit is not None:
        out = out[: args.limit]
    return out


def emit(rows: list[dict], fmt: str, out_path: str | None) -> None:
    payload = [{k: r.get(k) for k in FIELDS} for r in rows]
    if fmt == "json":
        text = json.dumps(payload, indent=2, ensure_ascii=False) + "\n"
    elif fmt == "csv":
        from io import StringIO

        buf = StringIO()
        w = csv.DictWriter(buf, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(payload)
        text = buf.getvalue()
    else:
        if not payload:
            text = "no directories matched\n"
        else:
            header = f"{'DR':>4}  {'status':<14} {'access':<10} {'cat':<8} {'badge':<5} domain"
            lines = [header, "-" * len(header)]
            for r in payload:
                dr = r["dr"] if r["dr"] is not None else "-"
                badge = "yes" if r["badge_required"] else ""
                lines.append(
                    f"{str(dr):>4}  {str(r['status']):<14} {str(r['access']):<10} "
                    f"{str(r['category']):<8} {badge:<5} {r['domain']}"
                )
            lines.append("")
            lines.append(f"total: {len(payload)}")
            text = "\n".join(lines) + "\n"

    if out_path:
        Path(out_path).write_text(text, encoding="utf-8")
        print(f"wrote {out_path} ({len(payload)} rows)", file=sys.stderr)
    else:
        sys.stdout.write(text)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--catalog", default=str(DEFAULT_CATALOG))
    ap.add_argument("--status", help="comma list; default: pending,discover (or new-product statuses with --new-product)")
    ap.add_argument("--new-product", action="store_true", help="reconsider source-campaign live/submitted listings for a different product")
    ap.add_argument("--category", help="comma list: launch,startup,saas,ai,agent,review,dev,nocode,content,local,general,other")
    ap.add_argument("--tier", help="comma list of tier numbers")
    ap.add_argument("--access", help="comma list to REQUIRE: open_form,login,captcha,paid,dead,unknown")
    ap.add_argument("--exclude-access", help="comma list to exclude (default: paid,captcha,dead)")
    ap.add_argument("--no-default-excludes", action="store_true", help="do not apply the default paid/captcha/dead excludes")
    ap.add_argument("--exclude-domain", help="comma list of domains to skip")
    ap.add_argument("--free", action="store_true", help="only directories with a free path")
    ap.add_argument("--paid", action="store_true", help="only paid-only directories")
    ap.add_argument("--dofollow", action="store_true", help="only verified-dofollow directories")
    ap.add_argument("--badge", action="store_true", help="only directories requiring a reciprocal badge")
    ap.add_argument("--no-badge", action="store_true", help="only directories not requiring a badge")
    ap.add_argument("--min-dr", type=int)
    ap.add_argument("--max-dr", type=int)
    ap.add_argument("--limit", type=int)
    ap.add_argument("--format", choices=("table", "json", "csv"), default="table")
    ap.add_argument("--out", help="write output to file instead of stdout")
    args = ap.parse_args()

    rows = load_catalog(Path(args.catalog))
    matched = apply_filters(rows, args)
    emit(matched, args.format, args.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
