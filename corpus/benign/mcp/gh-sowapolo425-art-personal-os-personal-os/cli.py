import argparse
import json
import sys
import zipfile
from .store import Store


def main():
    # JSON/MCP output must remain UTF-8 when Windows redirects stdout to pipes.
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="Local personal data for MCP Agents")
    parser.add_argument("--vault", required=True, help="Explicit path to your private local vault")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("init")
    serve = sub.add_parser("serve")
    serve.add_argument("--allow-restricted", action="store_true", help="Expose restricted records to this Agent")
    dashboard = sub.add_parser("dashboard", help="Open a local browser dashboard")
    dashboard.add_argument("--port", type=int, default=8765)
    dashboard.add_argument("--no-browser", action="store_true")
    sub.add_parser("proposals")
    show = sub.add_parser("show-proposal")
    show.add_argument("id")
    for name in ("approve", "reject"):
        command = sub.add_parser(name)
        command.add_argument("id")
        command.add_argument("--resolution", choices=("replace", "keep_both", "scoped"))
        command.add_argument("--scope")
    delete = sub.add_parser("delete")
    delete.add_argument("id")
    delete.add_argument("--revision", required=True, type=int)
    delete.add_argument("--mode", choices=("source", "deactivate", "purge"), default="source")
    delete.add_argument("--impact", help="Fingerprint from deletion-preview; required for purge")
    deletion_preview = sub.add_parser("deletion-preview")
    deletion_preview.add_argument("id")
    restore = sub.add_parser("restore")
    restore.add_argument("id")
    restore.add_argument("--revision", required=True, type=int)
    backup = sub.add_parser("backup", help="Create a checked ZIP backup")
    backup.add_argument("--output", required=True)
    restore_zip = sub.add_parser("restore-backup", help="Restore to a new adjacent vault")
    restore_zip.add_argument("archive")
    export = sub.add_parser("analysis-pack", help="Export selected records for your own Agent or model API")
    export.add_argument("--ids", nargs="+", required=True)
    export.add_argument("--purpose", required=True)
    export.add_argument("--output", required=True)
    export.add_argument("--allow-restricted", action="store_true")
    args = parser.parse_args()
    store = Store(args.vault)
    try:
        if args.command == "dashboard":
            from .dashboard import run
            run(args.vault, args.port, not args.no_browser)
            return
        if args.command == "serve":
            if not store.meta.is_dir():
                raise ValueError("Run init first")
            from .server import create_server
            create_server(args.vault, args.allow_restricted).run(transport="stdio")
            return
        if args.command == "init":
            store.init()
            result = {"initialized": True, "vault": str(store.root)}
        elif args.command == "proposals":
            result = [{"id": p["id"], "title": p["record"]["title"], "state": p["state"]} for p in store.proposals()]
        elif args.command == "show-proposal":
            result = next((p for p in store.proposals() if p["id"] == args.id), None)
            if result is None:
                raise ValueError("Proposal not found")
        elif args.command in ("approve", "reject"):
            result = store.review(args.id, args.command == "approve", args.resolution, args.scope)
        elif args.command == "delete":
            result = store.delete(args.id, args.revision, args.mode, args.impact)
        elif args.command == "deletion-preview":
            result = store.deletion_preview(args.id, True)
        elif args.command == "analysis-pack":
            from pathlib import Path
            from .conversations import analysis_pack
            destination = Path(args.output).expanduser().resolve()
            if destination.is_relative_to(store.root):
                raise ValueError("Save analysis exports outside the active vault")
            pack = analysis_pack(store, args.ids, args.purpose, args.allow_restricted)
            destination.parent.mkdir(parents=True, exist_ok=True)
            with destination.open("x", encoding="utf-8") as stream:
                json.dump(pack, stream, ensure_ascii=False, indent=2)
            result = {"output": str(destination), "record_count": pack["record_count"], "model_called": False}
        elif args.command == "backup":
            from pathlib import Path
            from .backup import create_backup
            destination = Path(args.output).expanduser().resolve()
            if destination.is_relative_to(store.root):
                raise ValueError("Save backups outside the active vault")
            data = create_backup(store)
            destination.parent.mkdir(parents=True, exist_ok=True)
            with destination.open("xb") as stream:
                stream.write(data)
            result = {"backup": str(destination), "bytes": len(data), "encrypted": False}
        elif args.command == "restore-backup":
            from pathlib import Path
            from .backup import restore_backup, MAX_ARCHIVE
            archive = Path(args.archive)
            if archive.stat().st_size > MAX_ARCHIVE:
                raise ValueError("Backup exceeds 32 MB")
            result = restore_backup(store, archive.read_bytes())
        else:
            result = store.restore(args.id, args.revision)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    except (ValueError, OSError, KeyError, zipfile.BadZipFile, RuntimeError) as exc:
        print(f"Personal OS: {exc}", file=sys.stderr)
        raise SystemExit(1)


if __name__ == "__main__":
    main()
