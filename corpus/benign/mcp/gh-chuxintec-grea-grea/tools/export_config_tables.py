#!/usr/bin/env python3
"""Export every TextAsset from the decrypted configuration AssetBundle."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from grea.safe_paths import relative_name, unique_paths, disjoint, write_bytes_new


def raw_script(value: object) -> bytes:
    if isinstance(value, bytes):
        return value
    if isinstance(value, bytearray):
        return bytes(value)
    if isinstance(value, str):
        return value.encode("utf-8")
    return bytes(value)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("bundle", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()

    import UnityPy
    args.output = disjoint(args.output, args.bundle)
    environment = UnityPy.load(str(args.bundle))
    assets = [obj for obj in environment.objects if obj.type.name == "TextAsset"]
    selected = [(obj, obj.read()) for obj in assets]
    names = [relative_name(asset.m_Name) for _, asset in selected]
    if any(len(name.parts) != 1 for name in names):
        raise ValueError("TextAsset names must be single portable filenames")
    unique_paths(names)
    args.output.mkdir(parents=True, exist_ok=False)
    raw_dir = args.output / "raw"
    json_dir = args.output / "json"
    raw_dir.mkdir(parents=True, exist_ok=True)
    json_dir.mkdir(parents=True, exist_ok=True)

    index: list[dict[str, object]] = []
    level_summary: dict[str, object] = {}
    parsed_tables: dict[str, object] = {}

    for obj, asset in selected:
        name = asset.m_Name
        payload = raw_script(asset.m_Script)
        raw_path = raw_dir / f"{name}.bytes"
        write_bytes_new(raw_path, payload)

        entry: dict[str, object] = {
            "name": name,
            "logical_path": f"Assets/GameRes/BundleRes/Data/Config/{name}.bytes",
            "path_id": obj.path_id,
            "bytes": len(payload),
            "sha256": hashlib.sha256(payload).hexdigest(),
            "raw_file": str(raw_path.relative_to(args.output)),
            "json_valid": False,
        }

        try:
            text = payload.decode("utf-8-sig")
            parsed = json.loads(text)
        except (UnicodeDecodeError, json.JSONDecodeError):
            parsed = None
        else:
            parsed_tables[name] = parsed
            json_path = json_dir / f"{name}.json"
            # Preserve the publisher's compact formatting while dropping the
            # UTF-8 BOM so ordinary JSON tools can open the file directly.
            write_bytes_new(json_path, text.encode("utf-8"))
            entry["json_valid"] = True
            entry["json_file"] = str(json_path.relative_to(args.output))
            if isinstance(parsed, dict):
                entry["root_keys"] = list(parsed)
                records = parsed.get("Datas")
                if isinstance(records, list):
                    entry["record_count"] = len(records)
                    if name in {
                        "LevelConfig",
                        "Level2Config",
                        "MapConfig",
                        "PBGameLevelConfig",
                        "PBGameMapConfig",
                        "ChapterConfig",
                    }:
                        field_names = sorted(
                            {key for item in records if isinstance(item, dict) for key in item}
                        )
                        ids = [
                            item.get("ID", item.get("Id", item.get("id")))
                            for item in records
                            if isinstance(item, dict)
                        ]
                        ids = [value for value in ids if value is not None]
                        level_summary[name] = {
                            "record_count": len(records),
                            "first_id": ids[0] if ids else None,
                            "last_id": ids[-1] if ids else None,
                            "fields": field_names,
                            "json_file": str(json_path.relative_to(args.output)),
                        }
        index.append(entry)

    level_rows = (
        parsed_tables.get("LevelConfig", {}).get("Datas", [])
        if isinstance(parsed_tables.get("LevelConfig"), dict)
        else []
    )
    map_rows = (
        parsed_tables.get("MapConfig", {}).get("Datas", [])
        if isinstance(parsed_tables.get("MapConfig"), dict)
        else []
    )
    chapter_rows = (
        parsed_tables.get("ChapterConfig", {}).get("Datas", [])
        if isinstance(parsed_tables.get("ChapterConfig"), dict)
        else []
    )
    level_ids = [row.get("ID") for row in level_rows if isinstance(row, dict)]
    level_map_ids = [row.get("MapId") for row in level_rows if isinstance(row, dict)]
    available_map_ids = {
        row.get("Id") for row in map_rows if isinstance(row, dict) and row.get("Id") is not None
    }
    chapter_level_ids = [
        level_id
        for row in chapter_rows
        if isinstance(row, dict)
        for level_id in row.get("LevelIDs", [])
    ]
    level_summary["cross_table_validation"] = {
        "level_ids_contiguous_1_to_count": level_ids == list(range(1, len(level_ids) + 1)),
        "unique_level_map_ids": len(set(level_map_ids)),
        "missing_map_ids": sorted(set(level_map_ids) - available_map_ids),
        "all_level_map_ids_resolved": set(level_map_ids) <= available_map_ids,
        "chapter_level_references": len(chapter_level_ids),
        "unique_chapter_level_references": len(set(chapter_level_ids)),
        "all_levels_covered_by_chapters": set(level_ids) <= set(chapter_level_ids),
    }

    index.sort(key=lambda item: str(item["name"]).lower())
    (args.output / "TABLE_INDEX.json").write_text(
        json.dumps(
            {
                "bundle": args.bundle.name,
                "bundle_sha256": hashlib.sha256(args.bundle.read_bytes()).hexdigest(),
                "text_asset_count": len(index),
                "json_table_count": sum(bool(item["json_valid"]) for item in index),
                "tables": index,
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    (args.output / "LEVEL_TABLE_SUMMARY.json").write_text(
        json.dumps(level_summary, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    print(f"text_assets={len(index)}")
    print(f"json_tables={sum(bool(item['json_valid']) for item in index)}")
    for name, summary in level_summary.items():
        if isinstance(summary, dict) and "record_count" in summary:
            print(
                f"{name}: records={summary['record_count']} "
                f"ids={summary['first_id']}..{summary['last_id']}"
            )


if __name__ == "__main__":
    main()
