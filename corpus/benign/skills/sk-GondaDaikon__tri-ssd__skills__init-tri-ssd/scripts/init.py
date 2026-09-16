#!/usr/bin/env python3
"""Tri-SSD のディレクトリ構造を初期化する。

docs/ 配下に L0-L3 のディレクトリを .gitkeep 付きで作成し、
情報の在り処マップ（docs/README.md）を生成する。
既存のディレクトリ・ファイルは上書きしない（決定的・冪等）。

使い方:
    python3 init.py [--root DIR]
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):  # Windows 等でも UTF-8 出力を保証
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

# (相対パス, 説明) — 説明は出力の可読性のためだけに使う
DIRS = [
    ("docs/l0_ideas", "アイディア・ラフメモ（任意）"),
    ("docs/l1_requirements", "要件定義"),
    ("docs/l2_foundation", "システム構成"),
    ("docs/l3_phases", "フェーズ（機能+受け入れ条件）"),
]

# 情報の在り処マップ（docs/README.md）。既存があれば上書きしない
README = """\
# ドキュメント構成（Tri-SSD）

| したいこと | 見る場所 |
|---|---|
| 要求・成功条件を知る | l1_requirements/vision.md |
| 技術選定・設計・確認済みの前提を知る | l2_foundation/foundation.md |
| 画面・データ設計の詳細を見る | l2_foundation/interface.md / data.md（分離時のみ。foundation.md から参照） |
| 今のフェーズの作業・受け入れ条件を見る | l3_phases/PH-nnnn_*.md（frontmatter `status` で特定） |
| 過去の経緯を知る | ../CHANGELOG.md → 詳細は l3_phases/_archive/ |
| アイディアの原石を置く | l0_ideas/（任意・自由形式） |

レイヤー: L0（任意メモ）→ L1（要件）→ L2（構成）→ L3（フェーズ）。
ID形式: PREFIX-nnnn（REQ / PH / F）。番号は再利用しない（永久欠番）。
"""


def main() -> int:
    ap = argparse.ArgumentParser(description="Tri-SSD ディレクトリ初期化")
    ap.add_argument("--root", default=".", help="プロジェクトルート（既定: カレント）")
    args = ap.parse_args()
    root = Path(args.root)

    created: list[str] = []
    skipped: list[str] = []
    for rel, _desc in DIRS:
        gitkeep = root / rel / ".gitkeep"
        if gitkeep.exists():
            skipped.append(rel)
            continue
        gitkeep.parent.mkdir(parents=True, exist_ok=True)
        gitkeep.touch()
        created.append(rel)

    readme = root / "docs" / "README.md"
    if readme.exists():
        skipped.append("docs/README.md")
    else:
        with open(readme, "w", encoding="utf-8", newline="\n") as f:
            f.write(README)
        created.append("docs/README.md")

    print("# Tri-SSD 初期化完了")
    if created:
        print("\n## 作成したもの")
        for c in created:
            print(f"- {c}" + ("" if c.endswith(".md") else "/"))
    if skipped:
        print("\n## 既存（スキップ）")
        for s in skipped:
            print(f"- {s}" + ("" if s.endswith(".md") else "/"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
