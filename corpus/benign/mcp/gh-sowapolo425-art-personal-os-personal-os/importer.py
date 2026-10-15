"""Import source material without promoting AI text to personal facts."""
import hashlib
import json
from datetime import datetime, timezone
from pathlib import PurePosixPath

from .store import MAX_TEXT, checked_text, now

MAX_UPLOAD = 8 * 1024 * 1024
MAX_ITEMS = 500


def fingerprint(content):
    return hashlib.sha256(content.replace("\r\n", "\n").encode("utf-8")).hexdigest()


def import_key(filename, locator, content):
    return fingerprint(json.dumps([filename, locator, fingerprint(content)], ensure_ascii=False))


def existing_imports(store):
    records = list(store._all())
    return ({r["import_key"] for r in records if "import_key" in r},
            {(r["source"], fingerprint(r["content"]), r["title"], r.get("source_created_at")) for r in records
             if r["status"] == "imported_source" and "import_key" not in r})


def duplicate(item, known, legacy):
    return item["key"] in known or ("local import / " + item["filename"], fingerprint(item["content"]),
                                    item["title"], item.get("source_created_at")) in legacy


def source_date(value):
    if value is None:
        return None
    try:
        if isinstance(value, (int, float)):
            return datetime.fromtimestamp(value, timezone.utc).isoformat()
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            return None
        return parsed.astimezone(timezone.utc).isoformat()
    except (ValueError, TypeError, OverflowError, OSError, AttributeError):
        return None


def parse_import(filename, text):
    if not isinstance(filename, str) or len(filename) > 180 or "/" in filename or "\\" in filename:
        raise ValueError("Choose a file name, not a path")
    checked_text(text, "file text", MAX_UPLOAD)
    if len(text.encode("utf-8")) > MAX_UPLOAD:
        raise ValueError("Import file exceeds 8 MB; split it into smaller files")
    extension = PurePosixPath(filename).suffix.lower()
    items = []

    def append(title, content, date=None, locator="document"):
        checked_text(content, "imported record", MAX_TEXT)
        title = str(title or filename)[:300]
        items.append({"key": import_key(filename, locator, content), "title": title, "content": content,
                      "locator": locator,
                      "filename": filename, "source_created_at": source_date(date)})
        if len(items) > MAX_ITEMS:
            raise ValueError("More than 500 conversations; split the export")

    if extension in (".md", ".txt"):
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        title = next((line.lstrip("# ") for line in lines if line.startswith("# ")), filename)
        append(title, text)
    elif extension == ".json":
        data = json.loads(text)
        if isinstance(data, list) and data and all(isinstance(m, dict) and "role" in m for m in data):
            data = {"messages": data, "title": filename}
        conversations = data if isinstance(data, list) else data.get("conversations", [data]) if isinstance(data, dict) else None
        if not isinstance(conversations, list) or not conversations:
            raise ValueError("Expected a conversation export or an object with messages")
        for position, conversation in enumerate(conversations):
            if not isinstance(conversation, dict):
                raise ValueError("Invalid conversation entry")
            if "mapping" in conversation:
                mapping = conversation["mapping"]
                if not isinstance(mapping, dict):
                    raise ValueError("Invalid ChatGPT mapping")
                current = conversation.get("current_node")
                if current:
                    chain, seen = [], set()
                    while current:
                        if not isinstance(current, str) or current in seen or current not in mapping:
                            raise ValueError("Invalid or cyclic conversation branch")
                        seen.add(current)
                        item = mapping[current]
                        if not isinstance(item, dict):
                            raise ValueError("Invalid conversation node")
                        chain.append(item.get("message"))
                        current = item.get("parent")
                    messages = list(reversed(chain))
                else:
                    raise ValueError("ChatGPT export has no current_node; cannot select a branch safely")
            else:
                messages = conversation.get("messages")
            if not isinstance(messages, list):
                raise ValueError("JSON must contain ChatGPT mapping or messages")
            parts = []
            for message in messages:
                if not isinstance(message, dict) or message.get("channel") in ("analysis", "commentary"):
                    continue
                author = message.get("author") or {}
                if not isinstance(author, dict):
                    raise ValueError("Invalid message author")
                role = message.get("role") or author.get("role")
                if role not in ("user", "assistant"):
                    continue
                body = message.get("content", "")
                if isinstance(body, dict):
                    parts_value = body.get("parts", [])
                    if not isinstance(parts_value, list):
                        raise ValueError("Message content parts must be a list")
                    body = "\n".join(p for p in parts_value if isinstance(p, str))
                if not isinstance(body, str) or not body.strip():
                    continue
                label = "用户原文" if role == "user" else "助手回复（AI 生成，非用户事实）"
                parts.append(label + "：\n" + body)
            if parts:
                cid = conversation.get("id") or conversation.get("conversation_id")
                locator = f"conversation:{cid}" if isinstance(cid, (str, int)) and cid else f"conversation-index:{position}"
                append(conversation.get("title", filename), "\n\n".join(parts), conversation.get("create_time"), locator)
    else:
        raise ValueError("Supported files: UTF-8 .md, .txt and conversation .json")
    if not items:
        raise ValueError("No supported text messages found")
    # Deduplicate the same source location, not different conversations with equal words.
    unique = {item["key"]: item for item in items}
    return list(unique.values())


def preview_import(store, items):
    with store.locked():
        known, legacy = existing_imports(store)
    return [{**item, "duplicate": duplicate(item, known, legacy)} for item in items]


def commit_import(store, items, keys, sensitivity="restricted"):
    if sensitivity not in ("private", "restricted"):
        raise ValueError("Invalid sensitivity")
    if not isinstance(keys, list) or not keys or len(keys) > MAX_ITEMS or not all(isinstance(k, str) for k in keys):
        raise ValueError("Select at least one preview item")
    selected = set(keys)
    if not selected.issubset({item["key"] for item in items}):
        raise ValueError("Selection does not belong to this preview")
    imported, skipped = [], 0
    with store.locked():
        known, legacy = existing_imports(store)
        for item in items:
            if item["key"] not in selected:
                continue
            if duplicate(item, known, legacy):
                skipped += 1
                continue
            record = store._new(item["title"], item["content"], "knowledge", sensitivity, ["导入资料"],
                                "local import / " + item["filename"], "imported_source")
            record.update(import_hash=fingerprint(item["content"]), import_key=item["key"],
                          import_locator=item.get("locator", "document"), imported_at=now())
            if item["source_created_at"]:
                record["source_created_at"] = item["source_created_at"]
                record["created_at"] = item["source_created_at"]
            store._save(record)
            store._audit("import", record["id"])
            known.add(item["key"])
            imported.append(record["id"])
    return {"imported": len(imported), "skipped": skipped, "record_ids": imported}
