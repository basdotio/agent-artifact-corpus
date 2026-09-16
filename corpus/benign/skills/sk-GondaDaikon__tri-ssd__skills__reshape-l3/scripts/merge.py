#!/usr/bin/env python3
"""フォルダ構造の L3 フェーズをインライン形式の1ファイルに統合する。

_phase.md と F-*.md（ファイル名順）を PH-xxxx_name.md に統合する。
チェック状態 [x]・frontmatter・セクション順序（検証記録・完了サマリ等の
任意セクション含む）は保持。統合後に元フォルダを削除する。
split.py の逆操作で、往復可能。

使い方:
    python3 merge.py <PH-ID | フォルダパス>
"""
from __future__ import annotations

import argparse
import re
import shutil
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):  # Windows 等でも UTF-8 出力を保証
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import PHASES_DIR, build_doc, parse_doc, write_lf  # noqa: E402


def resolve_folder(target: str) -> Path | None:
    p = Path(target)
    if p.is_dir():
        return p
    if PHASES_DIR.exists():
        matches = [
            d for d in PHASES_DIR.glob("PH-*")
            if d.is_dir() and d.name != "_archive" and target in d.name
        ]
        if len(matches) == 1:
            return matches[0]
        if len(matches) > 1:
            joined = ", ".join(m.name for m in matches)
            print(f"error: '{target}' に複数一致: {joined}", file=sys.stderr)
    return None


def feature_to_inline(text: str) -> str:
    """F ファイル本文を ### F-xxxx ブロック（インライン形式）に変換する。"""
    lines = text.splitlines()
    title = ""
    rest_start = 0
    for i, ln in enumerate(lines):
        m = re.match(r"^#\s+(F-\d+\s*:.*)$", ln)
        if m:
            title = m.group(1).strip()
            rest_start = i + 1
            break
    body = "\n".join(lines[rest_start:]).strip("\n")
    # F ファイルの ## 受け入れ条件 をインラインの **受け入れ条件**: に戻す
    # （[ \t]* に限定: \s* だと改行を跨いで後続の空行まで消費してしまう）
    body = re.sub(r"(?m)^##[ \t]+受け入れ条件[ \t]*$", "**受け入れ条件**:", body)
    return f"### {title}\n\n{body}".rstrip()


def main() -> int:
    ap = argparse.ArgumentParser(description="L3 フェーズの統合")
    ap.add_argument("target", help="PH-ID またはフォルダパス")
    args = ap.parse_args()

    folder = resolve_folder(args.target)
    if folder is None:
        print(f"error: 指定されたフォルダが見つかりません: {args.target}", file=sys.stderr)
        return 1

    phase_file = folder / "_phase.md"
    if not phase_file.exists():
        print("error: _phase.md が見つかりません", file=sys.stderr)
        return 1
    f_files = sorted(folder.glob("F-*.md"), key=lambda p: p.name)
    if not f_files:
        print("error: 機能ファイル（F-*.md）が見つかりません", file=sys.stderr)
        return 1

    dest = folder.parent / (folder.name + ".md")
    if dest.exists():
        print(f"error: 同名ファイルが存在します: {dest}", file=sys.stderr)
        return 1

    fm, title, preamble, sections = parse_doc(phase_file.read_text(encoding="utf-8"))
    if not any(h == "機能一覧" for h, _ in sections):
        print("error: _phase.md に「## 機能一覧」がありません", file=sys.stderr)
        return 1

    feat_blocks = [feature_to_inline(ff.read_text(encoding="utf-8")) for ff in f_files]
    # phase-template 準拠の書式（見出し直後に空行、ブロック間・末尾に --- ）に正規化。
    # 他セクションは _phase.md の原文の行をそのまま保持する（往復 diff ゼロ）
    feat_body = ("\n" + "\n\n---\n\n".join(feat_blocks) + "\n\n---\n").split("\n")
    new_sections = [
        (h, feat_body if h == "機能一覧" else b) for h, b in sections
    ]
    inline = build_doc(fm, title, preamble, new_sections)
    write_lf(dest, inline)
    shutil.rmtree(folder)

    checked = len(re.findall(r"- \[x\]", inline))
    total = len(re.findall(r"- \[[ x]\]", inline))
    print("# 統合完了")
    print(f"\n**入力**: {folder}/")
    print(f"**出力**: {dest}")
    print(f"\n## 統合内容\n- 機能数: {len(f_files)}")
    print(f"\n## チェック状態\n- チェック済み: {checked}/{total}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
