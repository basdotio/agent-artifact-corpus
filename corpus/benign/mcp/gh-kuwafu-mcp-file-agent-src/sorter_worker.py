#!/usr/bin/env python3
"""
sorter_worker.py
Nextcloud 受動的ファイル自動仕分けワーカー
_Inbox を監視し、ローカル LLM (llama.cpp / llama-proxy) を用いて科目・講義回を判定して自動移動
"""

import os
import json
import requests
from nc_client import NextcloudWebDAV

# === 設定 (環境変数またはプレースホルダー) ===
NCP_HOST = os.getenv("NCP_HOST", "https://nextcloud.example.ts.net")
NCP_USER = os.getenv("NCP_USER", "your_username")
NCP_PASS = os.getenv("NCP_PASS", "your_app_password_here")

# ArcLightの動的プロキシ（ポート8000）を指定
LLM_HOST = os.getenv("LLM_HOST", "http://192.168.0.159:8000")
LLM_API_URL = f"{LLM_HOST}/v1/chat/completions"
LLM_MODEL = os.getenv("LLM_MODEL", "Qwen_Qwen3.5-122B-A10B-Q4_K_M-00001-of-00002.gguf")

INBOX_DIR = "/_Inbox"
TARGET_ROOT = os.getenv("TARGET_ROOT", "/大学/2026_秋")

# 登録科目リストのサンプル（運用環境に合わせてカスタマイズ）
SUBJECTS = [
    "分子生物学",
    "生化学Ⅰ",
    "有機化学Ⅱ",
    "物理化学実験",
    "情報科学基礎",
    "その他"
]


def classify_file(filename: str) -> dict:
    """llama.cpp (llama-proxy) にファイル名を渡して分類判定（JSON）"""
    system_prompt = f"""あなたは大学の講義資料を分類する整理エンジンです。
入力されたファイル名から該当する「科目名」と「講義の第何回か」を推測し、必ず以下のJSON形式のみで回答してください。前置きや解説、思考プロセスは一切出力しないでください。

【候補科目】
{", ".join(SUBJECTS)}

【JSONフォーマット】
{{"subject": "科目名", "week": 整数（不明な場合は0）}}"""

    payload = {
        "model": LLM_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"ファイル名: {filename}"}
        ],
        "temperature": 0.1,
        "response_format": {"type": "json_object"},
        "chat_template_kwargs": {"enable_thinking": False}
    }

    # チャット推論等のキュー待ちに耐えるようタイムアウト300秒
    res = requests.post(LLM_API_URL, json=payload, timeout=300)
    res.raise_for_status()

    content = res.json()["choices"][0]["message"]["content"]

    # 万が一 <think> タグが含まれていた場合の防護処理
    if "</think>" in content:
        content = content.split("</think>")[-1].strip()

    return json.loads(content)


def process_inbox(nc: NextcloudWebDAV):
    """_Inbox 内のファイルを巡回して仕分け"""
    files = nc.list_dir(INBOX_DIR)
    if not files:
        print("[INFO] _Inbox は空です。")
        return

    print(f"[INFO] 処理対象ファイル: {files}")

    for filename in files:
        print(f"\n--- 処理開始: {filename} ---")
        try:
            # 1. LLMによる推論
            result = classify_file(filename)
            subject = result.get("subject", "その他")
            week = int(result.get("week", 0))
            print(f"[判定結果] 科目: {subject} / 回数: 第{week}回")

            # 2. 移動先ディレクトリの決定
            if week > 0:
                dest_dir = f"{TARGET_ROOT}/{subject}/第{week:02d}回"
            else:
                dest_dir = f"{TARGET_ROOT}/{subject}"

            # 3. ディレクトリ作成 & ファイル移動
            nc.mkdir_p(dest_dir)
            src_path = f"{INBOX_DIR}/{filename}"
            dest_path = f"{dest_dir}/{filename}"

            if nc.move(src_path, dest_path):
                print(f"[完了] 移動成功: {dest_path}")
            else:
                print(f"[警告] 移動に失敗しました: {filename}")

        except Exception as e:
            # 個別例外が発生してもワーカー全体は落とさず継続
            print(f"[エラー発生] {filename} の処理をスキップ: {e}")


if __name__ == "__main__":
    nc = NextcloudWebDAV(NCP_HOST, NCP_USER, NCP_PASS)
    process_inbox(nc)