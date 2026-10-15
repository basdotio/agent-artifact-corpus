#!/usr/bin/env python3
"""
mcp_server.py
Nextcloud WebDAV 連携 FastMCP (SSE) サーバー
LibreChat 等の MCP クライアントから講義ノートを安全に参照・検索するエンドポイントを提供
"""

import os
from mcp.server.fastmcp import FastMCP
from nc_client import NextcloudWebDAV

# === Nextcloud設定 (環境変数またはプレースホルダー) ===
NCP_HOST = os.getenv("NCP_HOST", "https://nextcloud.example.ts.net")
NCP_USER = os.getenv("NCP_USER", "your_username")
NCP_PASS = os.getenv("NCP_PASS", "your_app_password_here")
TARGET_BASE = os.getenv("TARGET_BASE", "/大学/2026_秋")

# FastMCPサーバー初期化 (ポート8000 / 0.0.0.0 で外部連携)
mcp = FastMCP("Nextcloud-Academic-Notes", host="0.0.0.0", port=8000)
nc = NextcloudWebDAV(NCP_HOST, NCP_USER, NCP_PASS)


@mcp.tool()
def list_course_notes(subpath: str = "") -> list[str]:
    """Nextcloud上の講義フォルダやファイルの一覧を取得します。
    引数 subpath: '科目名' や '科目名/第01回' などの相対パス。空なら科目一覧を返します。
    """
    clean_sub = subpath.strip("/")
    target = f"{TARGET_BASE}/{clean_sub}" if clean_sub else TARGET_BASE

    files = nc.list_dir(target)
    return files


@mcp.tool()
def read_course_note(relative_file_path: str) -> str:
    """指定された講義ノートや要約ファイルの中身を読み出します。
    引数 relative_file_path 例: '科目名/第01回/講義ノート_要約.md'
    """
    clean_path = relative_file_path.strip("/")
    target = f"{TARGET_BASE}/{clean_path}"

    # パストラバーサル防止ガード
    if not clean_path or ".." in clean_path:
        return "エラー: 不正なパス指定です。"

    try:
        content = nc.read_text(target)
        return content
    except Exception as e:
        return f"ファイル読み出し失敗: {e}"


if __name__ == "__main__":
    # 外部(LibreChat)から叩けるように SSE トランスポートで待受起動
    mcp.run(transport="sse")