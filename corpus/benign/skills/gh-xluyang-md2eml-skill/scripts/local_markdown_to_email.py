#!/usr/bin/env python3
"""Convert local Markdown with images to email HTML, EML, or clipboard."""
from __future__ import annotations

import argparse
import base64
import html
import mimetypes
import os
import platform
import re
import shutil
import subprocess
import sys
import uuid
from email.message import EmailMessage
from pathlib import Path


THEMES = {
    "default": {"body": "#1f2937", "accent": "#2563eb", "muted": "#f3f4f6", "border": "#d1d5db"},
    "modern": {"body": "#172033", "accent": "#0f766e", "muted": "#ecfeff", "border": "#99f6e4"},
    "minimal": {"body": "#222222", "accent": "#555555", "muted": "#f7f7f7", "border": "#cccccc"},
}
IMAGE_RE = re.compile(r"!\[([^\]]*)\]\(([^)]+)\)|!\[\[([^\]|]+)(?:\|([^\]]+))?\]\]")


class Converter:
    def __init__(self, note_path: Path, vault: Path | None, theme: str, mode: str):
        self.note_path = note_path.expanduser()
        self.vault = (vault or self.note_path.parent).resolve()
        self.theme = THEMES[theme]
        self.mode = mode
        self.images: list[tuple[str, Path, str]] = []
        self.missing: list[str] = []
        self._used: set[str] = set()

    def resolve_note(self) -> Path:
        candidates = [self.note_path] if self.note_path.is_absolute() else [self.vault / self.note_path]
        for candidate in candidates:
            if candidate.is_file():
                return candidate
        raise FileNotFoundError(f"Note not found: {self.note_path}")

    def image_path(self, reference: str) -> Path | None:
        reference = reference.strip().split("#", 1)[0].strip()
        raw = Path(reference).expanduser()
        candidates = []
        if raw.is_absolute():
            candidates.append(raw)
        else:
            candidates.extend([self.note_path.parent / raw, self.vault / raw])
            # Search the configured root for attachments outside the note directory.
            candidates.extend(p for p in self.vault.rglob(raw.name) if p.is_file())
        for candidate in candidates:
            if candidate.is_file():
                return candidate.resolve()
        return None

    def image_tag(self, alt: str, reference: str, width: str | None) -> str:
        path = self.image_path(reference)
        if not path:
            label = reference.strip()
            if label not in self.missing:
                self.missing.append(label)
            return f'<span style="color:#b91c1c;font-style:italic;">[图片缺失: {html.escape(label)}]</span>'
        cid = f"img-{uuid.uuid4().hex}@local-markdown-to-email"
        self.images.append((cid, path, mimetypes.guess_type(path.name)[0] or "application/octet-stream"))
        if self.mode == "clipboard":
            data = base64.b64encode(path.read_bytes()).decode("ascii")
            src = f"data:{self.images[-1][2]};base64,{data}"
        else:
            src = f"cid:{cid}"
        width_style = ""
        if width and width.strip().isdigit():
            width_style = f" width=\"{int(width.strip())}\" style=\"max-width:100%;height:auto;width:{int(width.strip())}px;\""
        else:
            width_style = ' style="max-width:100%;height:auto;"'
        return f'<img src="{html.escape(src, quote=True)}" alt="{html.escape(alt or reference, quote=True)}"{width_style}>'

    def inline(self, text: str) -> str:
        placeholders: list[str] = []
        def image_sub(match: re.Match) -> str:
            alt, md_ref, wiki_ref, wiki_width = match.groups()
            value = self.image_tag(alt or "", md_ref or wiki_ref, wiki_width)
            token = f"\x00IMG{len(placeholders)}\x00"
            placeholders.append(value)
            return token
        text = IMAGE_RE.sub(image_sub, text)
        text = html.escape(text, quote=False)
        text = re.sub(r"`([^`]+)`", r'<code style="font-family:Consolas,monospace;background:#f3f4f6;padding:2px 4px;border-radius:3px;">\1</code>', text)
        text = re.sub(r"\*\*([^*]+)\*\*|__([^_]+)__", lambda m: f"<strong>{m.group(1) or m.group(2)}</strong>", text)
        text = re.sub(r"(?<!\*)\*([^*]+)\*(?!\*)|(?<!_)_([^_]+)_(?!_)", lambda m: f"<em>{m.group(1) or m.group(2)}</em>", text)
        text = re.sub(r"\[([^]]+)\]\((https?://[^)]+)\)", r'<a href="\2" style="color:' + self.theme["accent"] + ';">\1</a>', text)
        text = re.sub(r"\[\[([^\]|]+)(?:\|([^]]+))?\]\]", lambda m: f"<strong>{html.escape(m.group(2) or m.group(1))}</strong>", text)
        for i, value in enumerate(placeholders):
            text = text.replace(f"\x00IMG{i}\x00", value)
        return text

    def render(self, source: str) -> str:
        lines, out, i = source.splitlines(), [], 0
        while i < len(lines):
            line = lines[i]
            if not line.strip():
                i += 1; continue
            if line.startswith("```") or line.startswith("~~~"):
                fence = line[:3]; lang = line[3:].strip(); i += 1; code = []
                while i < len(lines) and not lines[i].startswith(fence): code.append(lines[i]); i += 1
                i += i < len(lines)
                label = f'<div style="color:{self.theme["accent"]};font-size:12px;margin-bottom:4px;">{html.escape(lang)}</div>' if lang else ""
                out.append(f'<pre style="white-space:pre-wrap;overflow-wrap:anywhere;background:{self.theme["muted"]};border:1px solid {self.theme["border"]};padding:12px;border-radius:4px;font-family:Consolas,monospace;font-size:13px;">{label}{html.escape("\n".join(code))}</pre>'); continue
            call = re.match(r">\s*\[!(\w+)\](?:\s*([^\n]*))?\s*$", line, re.I)
            if call:
                kind, title = call.group(1).upper(), call.group(2) or call.group(1).title(); body = []; i += 1
                while i < len(lines) and lines[i].startswith(">"):
                    body.append(re.sub(r"^>\s?", "", lines[i])); i += 1
                colors = {"NOTE": ("#eff6ff", "#2563eb"), "TIP": ("#ecfdf5", "#059669"), "WARNING": ("#fffbeb", "#d97706"), "CAUTION": ("#fef2f2", "#dc2626"), "IMPORTANT": ("#faf5ff", "#9333ea")}
                bg, border = colors.get(kind, (self.theme["muted"], self.theme["accent"]))
                out.append(f'<div style="background:{bg};border-left:4px solid {border};padding:10px 12px;margin:12px 0;"><strong style="color:{border};">{html.escape(title)}</strong><div style="margin-top:6px;">{self.render("\n".join(body))}</div></div>'); continue
            if re.match(r"^\s*[-*+]\s+", line):
                items = []
                while i < len(lines) and re.match(r"^\s*[-*+]\s+", lines[i]): items.append(f"<li>{self.inline(re.sub(r'^\\s*[-*+]\\s+', '', lines[i]))}</li>"); i += 1
                out.append("<ul style=\"margin:8px 0;padding-left:24px;\">" + "".join(items) + "</ul>"); continue
            if re.match(r"^\s*\d+[.)]\s+", line):
                items = []
                while i < len(lines) and re.match(r"^\s*\d+[.)]\s+", lines[i]): items.append(f"<li>{self.inline(re.sub(r'^\\s*\d+[.)]\\s+', '', lines[i]))}</li>"); i += 1
                out.append("<ol style=\"margin:8px 0;padding-left:24px;\">" + "".join(items) + "</ol>"); continue
            if line.startswith("#"):
                level = min(len(line) - len(line.lstrip("#")), 6); text = line[level:].strip(); out.append(f"<h{level} style=\"color:{self.theme['body']};margin:20px 0 8px;\">{self.inline(text)}</h{level}>"); i += 1; continue
            if "|" in line and i + 1 < len(lines) and re.match(r"^\s*\|?\s*:?-+:?\s*(\|\s*:?-+:?\s*)+\|?\s*$", lines[i + 1]):
                headers = [x.strip() for x in line.strip().strip("|").split("|")]; i += 2; rows = []
                while i < len(lines) and "|" in lines[i] and lines[i].strip(): rows.append([x.strip() for x in lines[i].strip().strip("|").split("|")]); i += 1
                tr = "".join("<tr>" + "".join(f'<th style="border:1px solid {self.theme["border"]};padding:8px;text-align:left;background:{self.theme["muted"]};">{self.inline(x)}</th>' for x in headers) + "</tr>")
                tr += "".join("<tr>" + "".join(f'<td style="border:1px solid {self.theme["border"]};padding:8px;">{self.inline(x)}</td>' for x in row) + "</tr>" for row in rows)
                out.append(f'<table style="border-collapse:collapse;width:100%;margin:12px 0;">{tr}</table>'); continue
            para = [line]; i += 1
            while i < len(lines) and lines[i].strip() and not re.match(r"^(#|>|```|~~~|\s*[-*+]\s+|\s*\d+[.)]\s+)", lines[i]): para.append(lines[i]); i += 1
            out.append(f'<p style="margin:10px 0;line-height:1.6;">{self.inline(" ".join(para))}</p>')
        return "\n".join(out)

    def html(self, source: str) -> str:
        content = self.render(source)
        return f'<!doctype html><html><body style="margin:0;background:#ffffff;color:{self.theme["body"]};font-family:-apple-system,BlinkMacSystemFont,Segoe UI,Arial,sans-serif;font-size:15px;"><div style="max-width:760px;margin:0 auto;padding:24px;">{content}</div></body></html>'

    def make_eml(self, body: str, output: Path) -> None:
        msg = EmailMessage(); msg["Subject"] = self.note_path.stem; msg["MIME-Version"] = "1.0"; msg.set_content("请使用支持 HTML 的邮件客户端查看此草稿。", subtype="plain", charset="utf-8"); msg.add_alternative(body, subtype="html", charset="utf-8")
        for cid, path, mime in self.images:
            maintype, subtype = mime.split("/", 1); msg.get_payload()[-1].add_related(path.read_bytes(), maintype=maintype, subtype=subtype, cid=f"<{cid}>", filename=path.name)
        output.parent.mkdir(parents=True, exist_ok=True); output.write_bytes(bytes(msg))


def copy_clipboard(content: str) -> str | None:
    try:
        try:
            import pyperclip  # type: ignore
            pyperclip.copy(content); return None
        except ImportError:
            pass
        command = shutil.which("pbcopy") if platform.system() == "Darwin" else shutil.which("xclip") or shutil.which("xsel")
        if command:
            if os.path.basename(command) == "xclip": subprocess.run([command, "-selection", "clipboard", "-t", "text/html"], input=content.encode(), check=True)
            elif os.path.basename(command) == "xsel": subprocess.run([command, "--clipboard", "--input"], input=content.encode(), check=True)
            else: subprocess.run([command], input=content.encode(), check=True)
            return None
        return "No clipboard backend found; install pyperclip or a platform clipboard utility."
    except Exception as exc:
        return str(exc)


def main() -> int:
    ap = argparse.ArgumentParser(); ap.add_argument("--note-path", required=True); ap.add_argument("--root-path", "--vault-path", dest="root_path"); ap.add_argument("--output-type", choices=["eml", "clipboard", "both"], default="eml"); ap.add_argument("--theme", choices=THEMES, default="default"); ap.add_argument("--output-path")
    args = ap.parse_args()
    try:
        note = Path(args.note_path); vault = Path(args.root_path).expanduser() if args.root_path else None
        converter = Converter(note, vault, args.theme, "clipboard" if args.output_type == "clipboard" else "eml"); actual = converter.resolve_note(); converter.note_path = actual
        body = converter.html(actual.read_text(encoding="utf-8-sig")); result = {"status": "success", "message": "转换完成", "data": {"output_type": args.output_type, "embedded_images_count": len(converter.images), "missing_images": converter.missing}}
        if args.output_type in ("eml", "both"):
            output = Path(args.output_path).expanduser() if args.output_path else actual.with_suffix(".eml"); converter.make_eml(body, output); result["data"]["eml_file_path"] = str(output.resolve())
        if args.output_type in ("clipboard", "both"):
            if args.output_type == "both":
                converter.mode = "clipboard"; converter.images.clear(); converter.missing.clear(); body = converter.html(actual.read_text(encoding="utf-8-sig"))
            result["data"]["clipboard_error"] = copy_clipboard(body)
        print(__import__("json").dumps(result, ensure_ascii=False)); return 0
    except Exception as exc:
        print(__import__("json").dumps({"status": "error", "message": str(exc), "data": {}}, ensure_ascii=False)); return 1


if __name__ == "__main__":
    raise SystemExit(main())
