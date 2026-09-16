#!/usr/bin/env python3
"""インライン形式の L3 フェーズファイルをフォルダ構造に分割する。

PH-xxxx_name.md を PH-xxxx_name/ フォルダに分割し、
_phase.md（frontmatter + 機能一覧以外の全セクション）と
F-xxxx_*.md（各機能）を生成する。チェック状態 [x]・frontmatter・
セクション順序（検証記録・完了サマリ等の任意セクション含む）は保持。
分割後に元ファイルを削除する。merge.py と往復可能。

使い方:
    python3 split.py <PH-ID | パス>
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):  # Windows 等でも UTF-8 出力を保証
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import PHASES_DIR, build_doc, parse_doc, write_lf  # noqa: E402


def resolve_inline(target: str) -> Path | None:
    p = Path(target)
    if p.is_file():
        return p
    if PHASES_DIR.exists():
        matches = [f for f in PHASES_DIR.glob("PH-*.md") if target in f.name]
        if len(matches) == 1:
            return matches[0]
        if len(matches) > 1:
            joined = ", ".join(m.name for m in matches)
            print(f"error: '{target}' に複数一致: {joined}", file=sys.stderr)
    return None


def slugify(name: str) -> str:
    """ファイル名に使える形へ。ASCII はケバブ化、日本語等はそのまま残す。"""
    s = re.sub(r'[\\/:*?"<>|]+', "", name.strip())
    s = re.sub(r"\s+", "-", s)
    return s or "feature"


def parse_features(feature_section: str) -> list[tuple[str, str, str]]:
    """## 機能一覧 の本文から (F-ID, 機能名, 本文) を列挙する。"""
    feats: list[tuple[str, str, str]] = []
    for part in re.split(r"(?m)^(?=###\s+F-)", feature_section):
        part = part.strip()
        if not part.startswith("###"):
            continue
        first, _, rest = part.partition("\n")
        m = re.match(r"^###\s+(F-\d+)\s*:\s*(.*)$", first.strip())
        if not m:
            continue
        fid, fname = m.group(1), m.group(2).strip()
        body = re.sub(r"\n?-{3,}\s*$", "", rest).strip("\n")  # 末尾の --- を除去
        feats.append((fid, fname, body))
    return feats


def main() -> int:
    ap = argparse.ArgumentParser(description="L3 フェーズの分割")
    ap.add_argument("target", help="PH-ID またはパス")
    args = ap.parse_args()

    src = resolve_inline(args.target)
    if src is None:
        print(f"error: 指定されたファイルが見つかりません: {args.target}", file=sys.stderr)
        return 1

    folder = src.parent / src.stem
    if folder.exists():
        print(f"error: 同名フォルダが存在します: {folder}", file=sys.stderr)
        return 1

    fm, title, preamble, sections = parse_doc(src.read_text(encoding="utf-8"))
    feat_section = "\n".join(next((b for h, b in sections if h == "機能一覧"), []))
    feats = parse_features(feat_section)
    if not feats:
        print("error: 機能セクション（### F-xxx）が見つかりません", file=sys.stderr)
        return 1

    block_count = len(re.findall(r"(?m)^###\s+F-", feat_section))
    if block_count != len(feats):
        print(
            "error: 解析できない機能ブロックがあります"
            "（### F-xxx: 名前 の形式か確認してください）",
            file=sys.stderr,
        )
        return 1

    folder.mkdir(parents=True)

    # 機能一覧のみリストに差し替え、他セクションは原文の行をそのまま保持する
    feat_list_body = [""] + [f"- {fid}: {fname}" for fid, fname, _ in feats] + [""]
    new_sections = [
        (h, feat_list_body if h == "機能一覧" else b) for h, b in sections
    ]
    write_lf(folder / "_phase.md", build_doc(fm, title, preamble, new_sections))

    created: list[str] = []
    for fid, fname, body in feats:
        # インラインの **受け入れ条件**: を F ファイルの ## 受け入れ条件 に変換
        # （[ \t]* に限定: \s* だと改行を跨いで後続の空行まで消費してしまう）
        fbody = re.sub(r"(?m)^\*\*受け入れ条件\*\*[ \t]*:[ \t]*$", "## 受け入れ条件", body)
        content = f"# {fid}: {fname}\n\n{fbody}\n"
        fpath = folder / f"{fid}_{slugify(fname)}.md"
        write_lf(fpath, content)
        created.append(fpath.name)

    src.unlink()

    print("# 分割完了")
    print(f"\n**入力**: {src}")
    print(f"**出力**: {folder}/")
    print("\n## 生成ファイル")
    print("- _phase.md（フェーズ概要）")
    for c in created:
        print(f"- {c}")
    print(f"\n**分割数**: {len(created)}機能")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
